import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


class PostgresStore:
    def __init__(self):
        self.dsn = os.environ["DATABASE_URL"]
        self.pool = None

    # -------------------- CONNECTION --------------------

    async def connect(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    # -------------------- JOB QUEUE --------------------

    async def pick_job(self):
        q = """
        UPDATE jobs
        SET status = 'RUNNING',
            updated_at = NOW()
        WHERE job_id = (
            SELECT job_id
            FROM jobs
            WHERE status = 'PENDING'
            ORDER BY created_at
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING *
        """
        async with self.pool.acquire() as con:
            return await con.fetchrow(q)

    async def set_job_status(self, job_id: str, status: str, error: str | None = None):
        q = """
        UPDATE jobs
        SET status = $2,
            error = $3,
            updated_at = NOW()
        WHERE job_id = $1
        """
        async with self.pool.acquire() as con:
            await con.execute(q, job_id, status, error)

    # -------------------- RAW DOCUMENTS --------------------

    async def mark_stale_jobs_as_failed(self, timeout_minutes: int):
        q = """
            UPDATE jobs
            SET status     = 'FAILED',
                error      = 'stale job timeout',
                updated_at = NOW()
            WHERE status = 'RUNNING'
              AND updated_at < NOW() - ($1 * INTERVAL '1 minute') \
            """
        async with self.pool.acquire() as con:
            await con.execute(q, timeout_minutes)

    async def insert_raw_document(
            self,
            *,
            source_type: str,  # "page" | "file"
            url: str,
            domain: str,
            content: str,
            content_hash: str,
            content_length: int,
            job_id: str | None,
            site_key: str,
    ):
        q = """
            INSERT INTO raw_documents (source_type, url, domain, \
                                       content, content_hash, content_length, \
                                       job_id, site_key)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT (content_hash) DO NOTHING \
            """
        async with self.pool.acquire() as con:
            await con.execute(
                q,
                source_type,
                url,
                domain,
                content,
                content_hash,
                content_length,
                job_id,
                site_key,
            )

    async def get_existing_hash(self, source_type: str, source_id: str):
        """
        Daha önce bu doküman DB'ye yazılmış mı?
        """
        q = """
        SELECT content_hash
        FROM raw_documents
        WHERE source_type = $1
          AND source_id = $2
        """
        async with self.pool.acquire() as con:
            return await con.fetchrow(q, source_type, source_id)

    async def has_same_content(self, source_id: str, content_hash: str) -> bool:
        q = """
            SELECT 1
            FROM raw_documents
            WHERE source_id = $1 \
              AND content_hash = $2 LIMIT 1 \
            """
        async with self.pool.acquire() as con:
            return await con.fetchval(q) is not None


    async def upsert_raw_document(
        self,
        *,
        source_type: str,   # "page" | "file"
        source_id: str,     # page_id / file_id
        site: str,
        url: str,
        raw_text: str,
        content_hash: str,
        content_type: str,
        text_len: int,
    ):
        """
        Hash-aware UPSERT:
        - content_hash aynıysa DB'ye dokunmaz
        - farklıysa UPDATE eder
        """

        # 1️⃣ Önce hash kontrolü
        old = await self.get_existing_hash(source_type, source_id)
        if old and old["content_hash"] == content_hash:
            return "SKIPPED"

        # 2️⃣ Farklıysa UPSERT
        q = """
        INSERT INTO raw_documents (
            source_type,
            source_id,
            site,
            url,
            raw_text,
            content_hash,
            content_type,
            text_len,
            created_at,
            updated_at
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,NOW(),NOW())
        ON CONFLICT (source_type, source_id)
        DO UPDATE SET
            raw_text     = EXCLUDED.raw_text,
            content_hash = EXCLUDED.content_hash,
            content_type = EXCLUDED.content_type,
            text_len     = EXCLUDED.text_len,
            updated_at   = NOW();
        """

        async with self.pool.acquire() as con:
            await con.execute(
                q,
                source_type,
                source_id,
                site,
                url,
                raw_text,
                content_hash,
                content_type,
                text_len,
            )

        return "UPSERTED"
