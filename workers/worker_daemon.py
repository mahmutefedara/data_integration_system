import asyncio
import json
from dataclasses import fields

from db.postgres_store import PostgresStore
from crawler.crawler_core import Crawler
from models import CrawlJob


def _filter_cfg_for_crawljob(cfg: dict) -> dict:
    allowed = {f.name for f in fields(CrawlJob)}
    return {k: v for k, v in (cfg or {}).items() if k in allowed}


async def daemon_loop():
    store = PostgresStore()
    await store.connect()
    await store.mark_stale_jobs_as_failed(timeout_minutes=10)


    print("[WORKER] daemon started")

    try:
        while True:
            row = await store.pick_job()
            if not row:
                await asyncio.sleep(2)
                continue

            job_id = row["job_id"]
            start_url = row["start_url"]
            root_domain = row["root_domain"]
            cfg_raw = row["config"]

            if isinstance(cfg_raw, str):
                cfg = json.loads(cfg_raw or "{}")
            else:
                cfg = dict(cfg_raw or {})

            cfg = _filter_cfg_for_crawljob(cfg)

            job = CrawlJob(
                job_id=job_id,
                start_urls=[start_url],
                root_domain=root_domain,
                **cfg,
            )

            print(f"[WORKER] picked job {job.job_id}")

            try:
                crawler = Crawler(job)
                await crawler.run()
                await store.set_job_status(job.job_id, "DONE")
                print(f"[WORKER] job {job.job_id} DONE")
            except Exception as e:
                await store.set_job_status(job.job_id, "FAILED", error=str(e))
                print(f"[WORKER] job {job.job_id} FAILED: {e}")

    finally:
        try:
            await store.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(daemon_loop())
