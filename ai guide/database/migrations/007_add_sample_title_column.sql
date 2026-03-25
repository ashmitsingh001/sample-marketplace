-- 007_add_sample_title_column.sql
-- Description: Add a 'title' column to samples for cleaner UI display.

ALTER TABLE public.samples ADD COLUMN IF NOT EXISTS title TEXT;

-- Seed titles from filenames for existing rows
UPDATE public.samples SET title = split_part(filename, '.', 1) WHERE title IS NULL;

-- Ensure the selective GRANT strategy from 002 is maintained
GRANT SELECT (title) ON TABLE public.samples TO anon, authenticated;
