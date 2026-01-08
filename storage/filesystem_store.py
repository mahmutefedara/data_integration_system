import os
import json
import aiofiles
from typing import List
from urllib.parse import urlparse

from models import CrawlJob, PageRecord, FileRecord
from utils import hash_url, get_domain, hash_text


def _safe_site_key(domain: str) -> str:
    return domain.replace(".", "_").replace(":", "_").replace("/", "_")


def _start_path(url: str) -> str:
    p = urlparse(url).path or "/"
    return p.rstrip("/") or "/"


class FilesystemStore:
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        self._pages: List[PageRecord] = []
        self._files: List[FileRecord] = []

    def job_dir(self, job: CrawlJob) -> str:
        """
        incremental=True  -> site bazlı global storage (aynı site aynı klasör)
        incremental=False -> job_id bazlı storage (her run ayrı klasör)
        """
        if job.incremental:
            domain = job.root_domain or (get_domain(job.start_urls[0]) if job.start_urls else job.job_id)
            key = _safe_site_key(domain)

            if job.path_mode and job.start_urls:
                p = _start_path(job.start_urls[0])
                key = f"{key}__path_{hash_url(p)[:8]}"

            return os.path.join(self.base_dir, key)

        return os.path.join(self.base_dir, job.job_id)

    def ensure_dirs(self, job: CrawlJob):
        base = self.job_dir(job)
        for sub in ["pages/text", "files_text"]:
            os.makedirs(os.path.join(base, sub), exist_ok=True)

    async def load_indexes_if_any(self, job: CrawlJob):
        base = self.job_dir(job)
        pages_index = os.path.join(base, "pages_index.json")
        files_index = os.path.join(base, "files_index.json")

        self._pages = []
        self._files = []

        if os.path.exists(pages_index):
            try:
                async with aiofiles.open(pages_index, "r", encoding="utf-8") as f:
                    raw = json.loads(await f.read() or "[]")
                self._pages = [PageRecord(**x) for x in raw]
            except Exception:
                # index bozuksa incremental yine çalışsın diye sessiz geçiyoruz
                self._pages = []

        if os.path.exists(files_index):
            try:
                async with aiofiles.open(files_index, "r", encoding="utf-8") as f:
                    raw = json.loads(await f.read() or "[]")
                self._files = [FileRecord(**x) for x in raw]
            except Exception:
                self._files = []

    async def save_page(
        self,
        job: CrawlJob,
        url: str,
        depth: int,
        text: str,
        content_type: str,
        links: list[str],
        discovered_files: list[str],
    ) -> PageRecord:
        self.ensure_dirs(job)
        base = self.job_dir(job)

        pid = hash_url(url)
        txt_path = os.path.join(base, "pages", "text", f"{pid}.txt")

        new_hash = hash_text(text)
        new_len = len(text or "")

        existing = next((p for p in self._pages if p.page_id == pid), None)

        if existing:
            old_hash = (getattr(existing, "content_hash", "") or "").strip()

            # ✅ 1) ESKİ INDEX MIGRATION: content_hash yoksa BACKFILL (UPDATED basma)
            if not old_hash:
                existing.content_hash = new_hash
                existing.text_len = new_len
                existing.depth = depth
                existing.content_type = content_type
                existing.discovered_links = links
                existing.discovered_files = discovered_files
                print(f"[DOC][PAGE][BACKFILL_HASH] depth={depth} url={url}")
                return existing

            # ✅ 2) Hash aynıysa SKIP (rewrite yok)
            if old_hash == new_hash:
                print(f"[DOC][PAGE][SKIP_SAME] depth={depth} url={url}")
                return existing

            # ✅ 3) Hash farklıysa gerçekten UPDATE (rewrite var)
            async with aiofiles.open(txt_path, "w", encoding="utf-8") as f:
                await f.write(text or "")

            existing.content_hash = new_hash
            existing.text_len = new_len
            existing.depth = depth
            existing.content_type = content_type
            existing.discovered_links = links
            existing.discovered_files = discovered_files

            print(f"[DOC][PAGE][UPDATED] depth={depth} chars={new_len} url={url}")
            return existing

        # 🆕 İlk kez görülen sayfa
        async with aiofiles.open(txt_path, "w", encoding="utf-8") as f:
            await f.write(text or "")

        rec = PageRecord(
            page_id=pid,
            job_id=job.job_id,
            url=url,
            domain=get_domain(url),
            depth=depth,
            text_path=txt_path,
            content_type=content_type,
            discovered_links=links,
            discovered_files=discovered_files,
            content_hash=new_hash,
            text_len=new_len,
        )

        self._pages.append(rec)
        print(f"[DOC][PAGE] depth={depth} chars={new_len} url={url}")
        return rec

    def _file_txt_path(self, job: CrawlJob, url: str) -> str:
        base = self.job_dir(job)
        fid = hash_url(url)
        return os.path.join(base, "files_text", f"{fid}.txt")

    async def save_file_text(
        self,
        job: CrawlJob,
        url: str,
        depth: int,
        text: str,
        content_type: str,
        size_bytes: int,
    ) -> FileRecord:
        self.ensure_dirs(job)

        fid = hash_url(url)
        txt_path = self._file_txt_path(job, url)

        if job.incremental and os.path.exists(txt_path):
            if not any(x.file_id == fid for x in self._files):
                self._files.append(
                    FileRecord(
                        file_id=fid,
                        job_id=job.job_id,
                        url=url,
                        domain=get_domain(url),
                        depth=depth,
                        file_path=txt_path,
                        content_type=content_type,
                        size_bytes=size_bytes,
                    )
                )
            return next(x for x in self._files if x.file_id == fid)

        async with aiofiles.open(txt_path, "w", encoding="utf-8") as f:
            await f.write(text or "")

        rec = FileRecord(
            file_id=fid,
            job_id=job.job_id,
            url=url,
            domain=get_domain(url),
            depth=depth,
            file_path=txt_path,
            content_type=content_type,
            size_bytes=len((text or "").encode("utf-8", errors="ignore")),
        )

        if not any(x.file_id == fid for x in self._files):
            self._files.append(rec)

        return rec

    async def write_indexes(self, job: CrawlJob):
        base = self.job_dir(job)
        os.makedirs(base, exist_ok=True)

        async with aiofiles.open(os.path.join(base, "pages_index.json"), "w", encoding="utf-8") as f:
            await f.write(json.dumps([p.__dict__ for p in self._pages], ensure_ascii=False, indent=2))

        async with aiofiles.open(os.path.join(base, "files_index.json"), "w", encoding="utf-8") as f:
            await f.write(json.dumps([x.__dict__ for x in self._files], ensure_ascii=False, indent=2))

        print(f"[STORE] {len(self._pages)} page, {len(self._files)} file index yazıldı → {base}")
