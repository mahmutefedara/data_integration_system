--
-- PostgreSQL database dump
--

\restrict TkYg07FWTzPUdkhTGb0G7yiK4bOVjJx47KoDo5TkvJNCWpRVH9qkbzrI4rZeqqU

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
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: document_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.document_status AS ENUM (
    'EXTRACTED',
    'EMBED_PENDING',
    'DONE',
    'FAILED'
);


--
-- Name: frontier_state; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.frontier_state AS ENUM (
    'queued',
    'processing',
    'done',
    'failed'
);


--
-- Name: job_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.job_status AS ENUM (
    'PENDING',
    'RUNNING',
    'DONE',
    'FAILED'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: -
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
    project_id integer NOT NULL,
    documents_only boolean DEFAULT false
);


--
-- Name: raw_documents; Type: TABLE; Schema: public; Owner: -
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
    agent_id text NOT NULL,
    project_id integer NOT NULL,
    CONSTRAINT raw_documents_source_type_check CHECK ((source_type = ANY (ARRAY['page'::text, 'file'::text])))
);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (job_id);


--
-- Name: raw_documents raw_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_documents
    ADD CONSTRAINT raw_documents_pkey PRIMARY KEY (id);


--
-- Name: raw_documents raw_documents_unique_per_project; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_documents
    ADD CONSTRAINT raw_documents_unique_per_project UNIQUE (agent_id, project_id, source_type, source_id);


--
-- Name: raw_documents unique_source_id_type; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_documents
    ADD CONSTRAINT unique_source_id_type UNIQUE (source_type, source_id);


--
-- Name: idx_jobs_agent_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_agent_project ON public.jobs USING btree (agent_id, project_id);


--
-- Name: idx_jobs_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_jobs_status_created ON public.jobs USING btree (status, created_at);


--
-- Name: idx_raw_documents_agent_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_raw_documents_agent_project ON public.raw_documents USING btree (agent_id, project_id);


--
-- PostgreSQL database dump complete
--

\unrestrict TkYg07FWTzPUdkhTGb0G7yiK4bOVjJx47KoDo5TkvJNCWpRVH9qkbzrI4rZeqqU

