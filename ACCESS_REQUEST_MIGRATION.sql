-- Table for Access Requests
CREATE TABLE IF NOT EXISTS public.access_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    club_name TEXT NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS but allow anyone to insert
ALTER TABLE public.access_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public can submit access requests" ON public.access_requests;
DROP POLICY IF EXISTS "Enable insert for all users" ON public.access_requests;

CREATE POLICY "Enable insert for all users" 
ON public.access_requests 
FOR INSERT 
WITH CHECK (true);

-- Explicitly grant permissions to the API roles
GRANT INSERT ON public.access_requests TO anon;
GRANT INSERT ON public.access_requests TO authenticated;

-- Only super-admins should be able to view/update. 
-- For now, we'll allow admins to see it if we want, but ideally it's more restricted.
DROP POLICY IF EXISTS "Admins can view access requests" ON public.access_requests;
CREATE POLICY "Admins can view access requests" ON public.access_requests FOR SELECT USING (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role = 'admin'));
