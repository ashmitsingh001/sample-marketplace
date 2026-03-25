-- 001_create_packs_table.sql
-- Description: Create the central 'packs' table for sample pack metadata.

CREATE TABLE IF NOT EXISTS public.packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE NOT NULL, -- Google Sheets row identifier
    source TEXT DEFAULT 'sheets',
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    type TEXT,
    price NUMERIC(10, 2) DEFAULT 0.00,
    cover_url TEXT,
    is_free BOOLEAN DEFAULT FALSE, -- Added for visibility logic
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    last_synced_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexing for fast lookups
CREATE INDEX IF NOT EXISTS packs_slug_idx ON public.packs (slug);
CREATE INDEX IF NOT EXISTS packs_external_id_idx ON public.packs (external_id);
CREATE INDEX IF NOT EXISTS packs_active_idx ON public.packs (is_active, is_deleted);

-- Enable RLS
ALTER TABLE public.packs ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Public packs are viewable if active and not deleted
CREATE POLICY "Packs are viewable by everyone" ON public.packs
FOR SELECT USING (
    is_active = TRUE 
    AND is_deleted = FALSE
);

-- Note: Complex "is_free OR purchased" visibility can be handled at the application layer 
-- or via a more complex RLS join, but for zero-budget performance, 
-- we allow metadata visibility for all active packs.
