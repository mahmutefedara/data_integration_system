--
-- PostgreSQL database dump
--

\restrict ohSfNPbW6hpzwj32RzESLKH5Bwgd2bbPCBXORv3aNK4enRuoBT1boKTHwfL9aJN

-- Dumped from database version 15.15 (Homebrew)
-- Dumped by pg_dump version 15.15 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: document_status; Type: TYPE; Schema: public; Owner: efe
--

CREATE TYPE public.document_status AS ENUM (
    'EXTRACTED',
    'EMBED_PENDING',
    'DONE',
    'FAILED'
);


ALTER TYPE public.document_status OWNER TO efe;

--
-- Name: frontier_state; Type: TYPE; Schema: public; Owner: efe
--

CREATE TYPE public.frontier_state AS ENUM (
    'queued',
    'processing',
    'done',
    'failed'
);


ALTER TYPE public.frontier_state OWNER TO efe;

--
-- Name: job_status; Type: TYPE; Schema: public; Owner: efe
--

CREATE TYPE public.job_status AS ENUM (
    'PENDING',
    'RUNNING',
    'DONE',
    'FAILED'
);


ALTER TYPE public.job_status OWNER TO efe;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: efe
--

CREATE TABLE public.jobs (
    job_id text NOT NULL,
    root_domain text NOT NULL,
    start_url text NOT NULL,
    config jsonb NOT NULL,
    status public.job_status DEFAULT 'PENDING'::public.job_status NOT NULL,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    single_page boolean DEFAULT false,
    path_mode boolean DEFAULT false,
    download_files boolean DEFAULT true,
    download_only_same_domain boolean DEFAULT true,
    incremental boolean DEFAULT true,
    agent_id text NOT NULL,
    project_id integer NOT NULL
);


ALTER TABLE public.jobs OWNER TO efe;

--
-- Name: raw_documents; Type: TABLE; Schema: public; Owner: efe
--

CREATE TABLE public.raw_documents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source_type text NOT NULL,
    source_id text NOT NULL,
    site text NOT NULL,
    url text NOT NULL,
    content_hash text NOT NULL,
    raw_text text NOT NULL,
    content_type text,
    text_len integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT raw_documents_source_type_check CHECK ((source_type = ANY (ARRAY['page'::text, 'file'::text])))
);


ALTER TABLE public.raw_documents OWNER TO efe;

--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: efe
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (job_id);


--
-- Name: raw_documents raw_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: efe
--

ALTER TABLE ONLY public.raw_documents
    ADD CONSTRAINT raw_documents_pkey PRIMARY KEY (id);


--
-- Name: raw_documents raw_documents_source_type_source_id_key; Type: CONSTRAINT; Schema: public; Owner: efe
--

ALTER TABLE ONLY public.raw_documents
    ADD CONSTRAINT raw_documents_source_type_source_id_key UNIQUE (source_type, source_id);


--
-- Name: idx_jobs_agent_project; Type: INDEX; Schema: public; Owner: efe
--

CREATE INDEX idx_jobs_agent_project ON public.jobs USING btree (agent_id, project_id);


--
-- Name: idx_jobs_status_created; Type: INDEX; Schema: public; Owner: efe
--

CREATE INDEX idx_jobs_status_created ON public.jobs USING btree (status, created_at);


--
-- PostgreSQL database dump complete
--

\unrestrict ohSfNPbW6hpzwj32RzESLKH5Bwgd2bbPCBXORv3aNK4enRuoBT1boKTHwfL9aJN

