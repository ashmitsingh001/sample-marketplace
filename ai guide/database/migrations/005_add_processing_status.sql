-- 005_add_processing_status.sql
-- Description: Add processing status and pack_file_id for ingestion tracking.

ALTER TABLE public.samples 
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending';

ALTER TABLE public.packs
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS pack_file_id TEXT; -- For the ZIP file in Telegram

-- Optional: Index for filtering pending samples in ingestion script
CREATE INDEX IF NOT EXISTS samples_processing_status_idx ON public.samples (processing_status) 
WHERE processing_status != 'completed';

CREATE INDEX IF NOT EXISTS packs_processing_status_idx ON public.packs (processing_status) 
WHERE processing_status != 'completed';
