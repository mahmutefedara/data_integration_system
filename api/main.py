from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse
import uuid
import json

from db.postgres_store import PostgresStore

app = FastAPI(title="Crawler API")
store = PostgresStore()


class CreateJobRequest(BaseModel):
    url: HttpUrl

    single_page: bool = False
    path_mode: bool = False
    agent_id: str
    project_id: int

    exclusive_depth: int | None = None
    max_depth_root: int = 10
    max_pages_total: int = 20000
    concurrency: int = 8

    download_files: bool = True
    download_only_same_domain: bool = True
    incremental: bool = True

    allowed_file_extensions: list[str] | None = None
    max_file_bytes: int | None = None


class CreateJobResponse(BaseModel):
    job_id: str
    status: str


def extract_root_domain(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


@app.post("/jobs", response_model=CreateJobResponse)
async def create_job(req: CreateJobRequest):
    await store.connect()

    job_id = str(uuid.uuid4())
    start_url = str(req.url)
    root_domain = extract_root_domain(start_url)

    config = {
        "single_page": req.single_page,
        "path_mode": req.path_mode,
        "exclusive_depth": req.exclusive_depth,
        "max_depth_root": req.max_depth_root,
        "max_pages_total": req.max_pages_total,
        "concurrency": req.concurrency,
        "download_files": req.download_files,
        "download_only_same_domain": req.download_only_same_domain,
        "incremental": req.incremental,
        "allowed_file_extensions": req.allowed_file_extensions,
        "max_file_bytes": req.max_file_bytes,
        "agent_id": req.agent_id,
        "project_id": req.project_id
    }

    config = {k: v for k, v in config.items() if v is not None}

    q = """
        INSERT INTO jobs (job_id, start_url, root_domain, config, status, agent_id, project_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7) \
        """
    async with store.pool.acquire() as con:
        await con.execute(q, job_id, start_url, root_domain, json.dumps(config),'PENDING',req.agent_id, req.project_id)

    return {"job_id": job_id, "status": "PENDING"}
