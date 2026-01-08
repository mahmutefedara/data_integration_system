-- db/schema.sql

-- 1) jobs
DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('PENDING','RUNNING','DONE','FAILED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  root_domain TEXT NOT NULL,
  start_url TEXT NOT NULL,
  config JSONB NOT NULL,
  status job_status NOT NULL DEFAULT 'PENDING',
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);

-- 2) url frontier (pages + files)
DO $$ BEGIN
  CREATE TYPE frontier_state AS ENUM ('queued','processing','done','failed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS url_frontier (
  id BIGSERIAL PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  kind TEXT NOT NULL, -- 'page' | 'file'
  url TEXT NOT NULL,
  domain TEXT NOT NULL,
  depth INT NOT NULL DEFAULT 0,
  state frontier_state NOT NULL DEFAULT 'queued',
  retry_count INT NOT NULL DEFAULT 0,
  last_error TEXT,
  locked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(job_id, url, kind)
);

CREATE INDEX IF NOT EXISTS idx_frontier_job_kind_state ON url_frontier(job_id, kind, state);

-- 3) documents (no embeddings here)
DO $$ BEGIN
  CREATE TYPE document_status AS ENUM ('EXTRACTED','EMBED_PENDING','DONE','FAILED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS documents (
  id BIGSERIAL PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,
  source_type TEXT NOT NULL, -- 'page' | 'file'
  url TEXT NOT NULL,
  domain TEXT NOT NULL,
  depth INT NOT NULL DEFAULT 0,
  content_type TEXT,
  extracted_text TEXT,
  discovered_links JSONB,
  discovered_files JSONB,
  file_meta JSONB,
  status document_status NOT NULL DEFAULT 'EXTRACTED',
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(job_id, url, source_type)
);

CREATE INDEX IF NOT EXISTS idx_docs_job_status ON documents(job_id, status);
