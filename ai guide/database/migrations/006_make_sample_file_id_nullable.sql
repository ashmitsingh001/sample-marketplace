-- 006_make_sample_file_id_nullable.sql
-- Description: Allow file_id to be NULL since we store packs as ZIPs in Telegram.

ALTER TABLE public.samples ALTER COLUMN file_id DROP NOT NULL;
