import asyncio
import os
from typing import Set, List, Optional
from urllib.parse import urlparse, urljoin

from models import CrawlJob, UrlContext
from utils import get_domain, hash_url, hash_text
from .http_fetcher import HttpFetcher
from .link_extractor import LinkExtractor
from storage.filesystem_store import FilesystemStore
from .file_ingestion import download_extract_delete
from db.postgres_store import PostgresStore

# Statik dosya uzantıları (içerik aranmayacaklar)
STATIC_EXTENSIONS = (
    ".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".mp4", ".webm", ".avi", ".mov",
    ".mp3", ".wav", ".zip", ".rar", ".7z", ".gz", ".tar",
)


def has_blocked_ext(url: str) -> bool:
    path = url.split("?", 1)[0].lower()
    return any(path.endswith(ext) for ext in STATIC_EXTENSIONS)


def get_ext(url: str) -> str:
    path = url.split("?", 1)[0].lower()
    _, ext = os.path.splitext(path)
    return ext.lower()


def decode_html(data: bytes, content_type: Optional[str]) -> str:
    """HTML içeriğini doğru karakter setiyle decode eder."""
    if content_type and "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=")[-1].split(";")[0].strip()
        try:
            return data.decode(charset)
        except Exception:
            pass

    try:
        txt = data.decode("utf-8")
        if "ý" not in txt and "þ" not in txt:
            return txt
    except Exception:
        pass

    for enc in ("windows-1254", "iso-8859-9"):
        try:
            return data.decode(enc)
        except Exception:
            pass

    return data.decode("utf-8", errors="replace")


class Crawler:
    def __init__(self, job: CrawlJob):
        self.job = job
        self.fetcher = HttpFetcher()
        self.extractor = LinkExtractor()
        self.store = FilesystemStore()
        self.pg = PostgresStore()

        self.visited_pages: Set[str] = set()
        self.enqueued_pages: Set[str] = set()
        self.processed_files: Set[str] = set()

        if not self.job.root_domain and self.job.start_urls:
            self.job.root_domain = get_domain(self.job.start_urls[0])

        self.base_path: Optional[str] = None
        if self.job.path_mode and self.job.start_urls:
            p = urlparse(self.job.start_urls[0]).path
            if not p or p == "/":
                self.base_path = "/"
            else:
                self.base_path = p.rstrip("/") + "/"

    def _in_scope(self, url: str) -> bool:
        if get_domain(url) != self.job.root_domain:
            return False
        if self.job.path_mode and self.base_path:
            if not urlparse(url).path.startswith(self.base_path):
                return False
        return True

    def _depth_cap(self) -> int:
        return self.job.exclusive_depth if self.job.exclusive_depth is not None else self.job.max_depth_root

    def _can_go_deeper(self, depth: int) -> bool:
        return (depth + 1) <= self._depth_cap()

    async def _handle_file_url(self, url: str, depth: int):
        if not self.job.download_files:
            return
        if url in self.processed_files:
            return
        if depth > self._depth_cap():
            return

        ext = get_ext(url)
        if ext not in self.job.allowed_file_extensions:
            return

        if self.job.download_only_same_domain:
            if get_domain(url) != self.job.root_domain:
                return

        fid = hash_url(url)

        text, meta, ctype = await download_extract_delete(
            fetcher=self.fetcher,
            url=url,
            max_bytes=getattr(self.job, "max_file_bytes", None)
        )

        if not text or meta.get("skipped_too_large"):
            self.processed_files.add(url)
            return

        await self.store.save_file_text(
            job=self.job,
            url=url,
            depth=depth,
            text=text,
            content_type=ctype or "",
            size_bytes=len(text.encode("utf-8", errors="ignore")),
            agent_id=self.job.agent_id,
            project_id=self.job.project_id
        )

        await self.pg.upsert_raw_document(
            source_type="file",
            source_id=fid,
            site=get_domain(url),
            url=url,
            raw_text=text,
            content_hash=hash_text(text),
            content_type=ctype or "",
            text_len=len(text),
            agent_id=self.job.agent_id,
            project_id=self.job.project_id
        )

        self.processed_files.add(url)

    async def _worker(self, wid: int, queue: "asyncio.Queue[UrlContext]"):
        try:
            while True:
                ctx = await queue.get()
                url = ctx.url
                depth = ctx.depth

                # Kontrol: Kapsam dışı mı veya zaten ziyaret edildi mi?
                if url in self.visited_pages or not self._in_scope(url):
                    queue.task_done()
                    continue

                if depth > self._depth_cap():
                    queue.task_done()
                    continue

                if self.job.single_page and depth > 0:
                    queue.task_done()
                    continue

                self.visited_pages.add(url)
                print(f"[w{wid}] FETCH depth={depth} {url}")

                try:
                    data, ctype = await self.fetcher.fetch(url, domain=get_domain(url))
                    if not data:
                        queue.task_done()
                        continue

                    if "text/html" in (ctype or "").lower():
                        html = decode_html(data, ctype)
                        text, links = self.extractor.extract(url, html)

                        clean_links: List[str] = []
                        file_links: List[str] = []

                        for ln in links:
                            ln = urljoin(url, ln)
                            if has_blocked_ext(ln) or not self._in_scope(ln):
                                continue

                            if get_ext(ln) in self.job.allowed_file_extensions:
                                file_links.append(ln)
                            else:
                                clean_links.append(ln)

                        # Sayfayı diske kaydet

                        page = await self.store.save_page(
                            job=self.job,
                            url=url,
                            depth=depth,
                            text=text,
                            content_type=ctype or "",
                            links=clean_links,
                            discovered_files=file_links,
                            agent_id=self.job.agent_id,
                            project_id=self.job.project_id
                        )

                        if page:
                            discovered_links = page.discovered_links
                            discovered_files = page.discovered_files
                        else:
                            discovered_links = clean_links
                            discovered_files = file_links

                        # Sayfayı DB'ye kaydet
                        if not self.job.documents_only:
                            if page:
                                await self.pg.upsert_raw_document(
                                    source_type="page",
                                    source_id=page.page_id,
                                    site=page.domain,
                                    url=page.url,
                                    raw_text=text,
                                    content_hash=page.content_hash,
                                    content_type=page.content_type,
                                    text_len=page.text_len,
                                    agent_id=self.job.agent_id,
                                    project_id=self.job.project_id
                                )

                        # Bulunan dosyaları işle
                        for f in file_links:
                            await self._handle_file_url(f, depth + 1)

                        # Yeni linkleri kuyruğa ekle
                        if self._can_go_deeper(depth):
                            for ln in clean_links:
                                if ln not in self.enqueued_pages:
                                    self.enqueued_pages.add(ln)
                                    queue.put_nowait(UrlContext(ln, depth + 1))
                        else:
                            pass

                except Exception as e:
                    print(f"[ERROR][WORKER-{wid}] {url}: {e}")

                queue.task_done()

        except asyncio.CancelledError:
            return

    async def run(self):
        try:
            await self.pg.connect()
            self.store.ensure_dirs(self.job)

            if self.job.incremental:
                await self.store.load_indexes_if_any(self.job)

            await self.fetcher.open()

            queue: asyncio.Queue[UrlContext] = asyncio.Queue()
            for u in self.job.start_urls:
                if u not in self.enqueued_pages:
                    self.enqueued_pages.add(u)
                    queue.put_nowait(UrlContext(u, 0))

            workers = [asyncio.create_task(self._worker(i + 1, queue)) for i in range(self.job.concurrency)]

            await queue.join()

            # Eğer buraya kadar geldiyse iş başarıyla bitmiştir
            await self.pg.set_job_status(self.job.job_id, "DONE")

        except asyncio.CancelledError:
            # Control-C veya manuel iptal durumunda buraya düşer
            print(f"\n[CRITICAL] Job {self.job.job_id} was cancelled by user (Control-C).")
            await self.pg.set_job_status(self.job.job_id, "FAILED", error="Interrupted by user (SIGINT)")
            raise  # Worker_daemon'un da kapanması için hatayı yukarı fırlat

        except Exception as e:
            # Beklenmedik bir hata oluşursa
            print(f"[ERROR] Fatal job error: {e}")
            await self.pg.set_job_status(self.job.job_id, "FAILED", error=str(e))

        finally:
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

            await self.fetcher.close()
            await self.store.write_indexes(self.job)
            await self.pg.close()