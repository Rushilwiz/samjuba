import { createClient } from '@supabase/supabase-js';
import {
	PUBLIC_SUPABASE_URL,
	PUBLIC_SUPABASE_ANON_KEY,
	PUBLIC_SUPABASE_BUCKET,
	PUBLIC_UPLOADS_TABLE
} from '$env/static/public';

export const supabaseUrl = PUBLIC_SUPABASE_URL;
export const supabaseAnonKey = PUBLIC_SUPABASE_ANON_KEY;
export const bucket = PUBLIC_SUPABASE_BUCKET || 'samjuba-uploads';
export const uploadsTable = PUBLIC_UPLOADS_TABLE || 'uploads';

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
	auth: { persistSession: false, autoRefreshToken: false }
});
