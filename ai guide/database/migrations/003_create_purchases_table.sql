-- 003_create_purchases_table.sql
-- Description: Access control table linking users to packs.

CREATE TABLE IF NOT EXISTS public.purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    pack_id UUID NOT NULL REFERENCES public.packs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    
    CONSTRAINT unique_user_pack_purchase UNIQUE (user_id, pack_id)
);

-- Indexing for access checks
CREATE INDEX IF NOT EXISTS purchases_user_id_idx ON public.purchases (user_id);
CREATE INDEX IF NOT EXISTS purchases_pack_id_idx ON public.purchases (pack_id);

-- Enable RLS
ALTER TABLE public.purchases ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their own purchases
CREATE POLICY "Users can view own purchases" ON public.purchases
FOR SELECT TO authenticated USING (auth.uid() = user_id);

-- RLS Policy: Users can insert their own purchase records (for testing/direct buy)
-- In production, this might be restricted to a service role
CREATE POLICY "Users can insert own purchases" ON public.purchases
FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
