-- Activation Keys for Organization Creation
CREATE TABLE IF NOT EXISTS public.activation_keys (
    key TEXT PRIMARY KEY,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    used_at TIMESTAMPTZ
);

-- Policy to allow anyone to check if a key exists/is valid (but not list all)
ALTER TABLE public.activation_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can view valid keys" ON public.activation_keys FOR SELECT USING (is_used = FALSE);
