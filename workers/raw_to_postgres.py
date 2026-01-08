import json
import aiofiles
from db.postgres_store import PostgresStore

async def ingest_site(site_dir: str):
    pg = PostgresStore()
    await pg.connect()

    index_path = f"{site_dir}/pages_index.json"
    async with aiofiles.open(index_path, "r", encoding="utf-8") as f:
        pages = json.loads(await f.read())

    for p in pages:
        async with aiofiles.open(p["text_path"], "r", encoding="utf-8") as tf:
            text = await tf.read()

        await pg.insert_raw_document(
            source_type="page",
            url=p["url"],
            domain=p["domain"],
            content=text,
            content_hash=p["content_hash"],
            content_length=p["text_len"],
            job_id=p["job_id"],
            site_key=p["domain"],
            agent_id = p["agent_id"],
            project_id = p["project_id"]
        )

    await pg.close()
