-- 004_setup_security_views.sql
-- Description: Create convenience views that strictly exclude internal fields.

-- A clean view for the frontend to consume
CREATE OR REPLACE VIEW public.active_samples_catalog AS
SELECT 
    id, 
    pack_id, 
    filename, 
    bpm, 
    musical_key, 
    category, 
    preview_url, 
    extra_metadata,
    created_at
FROM public.samples
WHERE is_active = TRUE AND is_deleted = FALSE;

-- Ensure the view respects RLS of the underlying table
ALTER VIEW public.active_samples_catalog SET (security_invoker = on);

-- Grant access to the view
GRANT SELECT ON public.active_samples_catalog TO public, anon, authenticated;
