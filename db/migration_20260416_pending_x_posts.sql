-- Migration: pending_x_posts — holds the current draft awaiting approval.
-- Replaces the old /tmp/pending_x_post.json file-based approach so drafts
-- survive Mac Mini restarts and live in Supabase like the rest of the state.
--
-- One row per pending draft (key is fixed to 'pending_x_post' — at most one
-- draft outstanding). After /approve or /discard, the row is deleted.

CREATE TABLE IF NOT EXISTS pending_x_posts (
    key TEXT PRIMARY KEY,
    session INTEGER,
    title TEXT,
    summary TEXT,
    draft TEXT NOT NULL,
    signature TEXT NOT NULL DEFAULT '🤖 AI · bagholderai.lol',
    generated_at TIMESTAMPTZ DEFAULT now()
);
