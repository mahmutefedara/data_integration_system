from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CrawlJob:
    job_id: str
    start_urls: List[str]
    root_domain: str = ""

    single_page: bool = False
    path_mode: bool = False
    exclusive_depth: Optional[int] = None

    download_files: bool = True
    download_only_same_domain: bool = True
    incremental: bool = True

    agent_id: str = "default_agent_id"
    project_id: int = 1
    max_depth_root: int = 10
    max_pages_total: int = 20000
    concurrency: int = 8

    allowed_file_extensions: List[str] = field(
        default_factory=lambda: [
            ".pdf", ".doc", ".docx",
            ".xls", ".xlsx",
            ".txt",
        ]
    )

    max_file_bytes: int = 25_000_000


@dataclass
class UrlContext:
    url: str
    depth: int


@dataclass
class PageRecord:
    page_id: str
    job_id: str
    url: str
    domain: str
    depth: int
    text_path: str
    content_type: str
    discovered_links: List[str]
    discovered_files: List[str]

    content_hash: str = ""
    text_len: int = 0


@dataclass
class FileRecord:
    file_id: str
    job_id: str
    url: str
    domain: str
    depth: int
    file_path: str
    content_type: str
    size_bytes: int
