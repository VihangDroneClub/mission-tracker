-- Editor Role and Permissions Update (Recursion-Safe Version)

-- 1. Helper function to check role without triggering recursion
CREATE OR REPLACE FUNCTION public.get_my_role()
RETURNS TEXT AS $$
  SELECT role FROM public.profiles WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER;

-- 2. Update Policies

-- PROFILES
DROP POLICY IF EXISTS "Users can view their own profiles" ON public.profiles;
CREATE POLICY "Users can view their own profiles" ON public.profiles 
FOR SELECT USING (auth.uid() = id OR public.get_my_role() = 'editor');

DROP POLICY IF EXISTS "Users can update their own profiles" ON public.profiles;
CREATE POLICY "Users can update their own profiles" ON public.profiles 
FOR UPDATE USING (auth.uid() = id OR public.get_my_role() = 'editor');

DROP POLICY IF EXISTS "Users can insert their own profiles" ON public.profiles;
CREATE POLICY "Users can insert their own profiles" ON public.profiles 
FOR INSERT WITH CHECK (auth.uid() = id OR public.get_my_role() = 'editor');

-- MISSIONS
DROP POLICY IF EXISTS "Missions are visible by organization members" ON public.missions;
CREATE POLICY "Missions are visible by organization members" ON public.missions 
FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR public.get_my_role() = 'editor');

DROP POLICY IF EXISTS "Admins can create missions" ON public.missions;
CREATE POLICY "Admins can create missions" ON public.missions 
FOR INSERT WITH CHECK (EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND role IN ('admin')) OR public.get_my_role() = 'editor');

-- PROJECTS
DROP POLICY IF EXISTS "Projects are visible by organization members" ON public.projects;
CREATE POLICY "Projects are visible by organization members" ON public.projects 
FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR public.get_my_role() = 'editor');

-- TASKS
DROP POLICY IF EXISTS "Tasks are visible by organization members" ON public.tasks;
CREATE POLICY "Tasks are visible by organization members" ON public.tasks 
FOR SELECT USING (organization_id = (SELECT organization_id FROM profiles WHERE id = auth.uid()) OR public.get_my_role() = 'editor');

-- Helper to set a user as editor
-- UPDATE public.profiles SET role = 'editor' WHERE email = 'pkhadse253@gmail.com';
