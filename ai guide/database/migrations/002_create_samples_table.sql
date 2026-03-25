-- 002_create_samples_table.sql
-- Description: Create the high-volume 'samples' table with hidden file_id.

CREATE TABLE IF NOT EXISTS public.samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pack_id UUID NOT NULL REFERENCES public.packs(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_id TEXT NOT NULL, -- Telegram Reference HIDDEN from default SELECT
    bpm INTEGER,
    musical_key TEXT,
    category TEXT,
    preview_url TEXT,
    extra_metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE, -- Added for consistency
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Performance Indexing
CREATE INDEX IF NOT EXISTS samples_pack_id_idx ON public.samples (pack_id);
CREATE INDEX IF NOT EXISTS samples_search_idx ON public.samples (category, musical_key, bpm);
CREATE INDEX IF NOT EXISTS samples_visibility_idx ON public.samples (is_active, is_deleted);

-- Enable RLS
ALTER TABLE public.samples ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Active/Non-deleted samples metadata is viewable by everyone
CREATE POLICY "Samples are viewable by everyone" ON public.samples
FOR SELECT USING (
    is_active = TRUE 
    AND is_deleted = FALSE
);

-- SECURE COLUMN STRATEGY: 
-- We GRANT SELECT only on "safe" columns to the public roles.
-- Since PostgREST (Supabase API) uses these roles, it will automatically exclude file_id from its schema.
REVOKE SELECT ON TABLE public.samples FROM anon, authenticated;
GRANT SELECT (id, pack_id, filename, bpm, musical_key, category, preview_url, extra_metadata, is_active, is_deleted, created_at) 
ON TABLE public.samples TO anon, authenticated;

-- Service role (used by Edge Functions) will retain full access to file_id
-- No change needed for 'service_role' as it has bypass RLS/all permissions by default.
