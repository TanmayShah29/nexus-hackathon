-- =============================================================================
-- NEXUS AlloyDB AI — Schema Initialisation Script
-- Run once against your AlloyDB primary instance.
-- AlloyDB ships with pgvector pre-installed; no CREATE EXTENSION needed on
-- instances created after AlloyDB GA (May 2023). If you're on an older
-- instance uncomment the line below.
-- =============================================================================

-- CREATE EXTENSION IF NOT EXISTS vector;  -- only needed on older instances

-- ---------------------------------------------------------------------------
-- 1. threads  (Layer 2 — session index)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS threads (
    id          TEXT        PRIMARY KEY,
    title       TEXT        NOT NULL DEFAULT '',
    metadata    JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Keep updated_at in sync automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_threads_updated_at ON threads;
CREATE TRIGGER trg_threads_updated_at
    BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ---------------------------------------------------------------------------
-- 2. agent_traces  (Layer 2 — observability feed)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_traces (
    id          BIGSERIAL   PRIMARY KEY,
    thread_id   TEXT        NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    agent_id    TEXT        NOT NULL,
    status      TEXT        NOT NULL CHECK (status IN ('running','done','error','skipped')),
    message     TEXT        NOT NULL DEFAULT '',
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_traces_thread
    ON agent_traces (thread_id, timestamp DESC);

-- ---------------------------------------------------------------------------
-- 3. context_items  (Layer 3 — blackboard / context KV store)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS context_items (
    key         TEXT        PRIMARY KEY,
    value       JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_context_items_updated_at ON context_items;
CREATE TRIGGER trg_context_items_updated_at
    BEFORE UPDATE ON context_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ---------------------------------------------------------------------------
-- 4. memories  (Layer 4 — pgvector semantic vault)
--
-- embedding dimension = 768  (Vertex AI textembedding-gecko@003 /
--                              Gemini text-embedding-004 both use 768)
-- If you switch to a 1536-dim model, change the number below and
-- re-create the index.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memories (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id   TEXT        NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    agent_id    TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    embedding   VECTOR(768) NOT NULL,
    metadata    JSONB       NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- IVFFlat index — good balance of speed vs recall for up to ~1 M rows.
-- Lists ≈ sqrt(rows). Start at 100; tune up when the table grows.
-- For AlloyDB Omni you can also use HNSW which gives better recall:
--   CREATE INDEX … USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_memories_embedding
    ON memories
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_memories_thread
    ON memories (thread_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- 5. match_memories()  — RPC called by the Python memory client
--    Returns rows ordered by cosine similarity (highest first).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION match_memories(
    query_embedding   VECTOR(768),
    match_threshold   FLOAT     DEFAULT 0.5,
    match_count       INT       DEFAULT 5
)
RETURNS TABLE (
    id          UUID,
    thread_id   TEXT,
    agent_id    TEXT,
    content     TEXT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ,
    similarity  FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        id,
        thread_id,
        agent_id,
        content,
        metadata,
        created_at,
        1 - (embedding <=> query_embedding) AS similarity
    FROM memories
    WHERE 1 - (embedding <=> query_embedding) >= match_threshold
    ORDER BY embedding <=> query_embedding   -- ascending distance = descending similarity
    LIMIT match_count;
$$;

-- ---------------------------------------------------------------------------
-- 6. Helpful views (optional — useful for the memory dashboard)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_recent_traces AS
    SELECT
        t.id          AS thread_id,
        t.title       AS thread_title,
        at.agent_id,
        at.status,
        at.message,
        at.timestamp
    FROM agent_traces at
    JOIN threads      t  ON at.thread_id = t.id
    ORDER BY at.timestamp DESC;
