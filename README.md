# samjuba

> In memory of **સમજુબેન શામજીભાઈ વાઘાણી** (Samjuben Shamjibhai Vaghani)

A simple, mobile-first public website where family members can upload photos and
videos to a shared collection. 
Files upload directly from the browser to Supabase Storage (with resumable TUS
for large videos), and one row per file is written to a Postgres table for
later browsing/admin.

---

## Supabase setup

These steps need to be done once in the Supabase dashboard before the app can work.

### 1. Create the project, upgrade to Pro

- Create a Supabase project. Note the **Project URL** and **anon public API key**
  (Project Settings → API).
- **Upgrade to Pro ($25/mo).** The free tier caps individual files at 50 MB,
  which phone videos routinely exceed. Pro gives 100 GB storage and lets you
  raise the per-file limit.

### 2. Raise the file-size limit

Storage → Settings → set **"Upload file size limit"** high enough for big
videos. **5 GB** is a comfortable ceiling.

### 3. Create the bucket

Storage → New bucket:

- Name: `samjuba-uploads` (or whatever you set in `PUBLIC_SUPABASE_BUCKET`)
- Public: **off** (we don't need viewing for v1)

### 4. Create the `uploads` table

SQL editor → run:

```sql
create table public.uploads (
  id            uuid primary key default gen_random_uuid(),
  storage_path  text not null,
  original_name text not null,
  content_type  text,
  size_bytes    bigint,
  created_at    timestamptz not null default now()
);

alter table public.uploads enable row level security;

-- Anyone may insert a row (matches the "anyone can upload" model).
create policy "anon can insert uploads"
  on public.uploads for insert
  to anon
  with check (true);

-- No select/update/delete for anon — uploaders can add, not browse or modify.
```

### 5. Storage policies for the bucket

SQL editor → run (replace bucket name if you changed it):

```sql
-- Allow anonymous uploads into the samjuba-uploads bucket only.
create policy "anon can upload to samjuba-uploads"
  on storage.objects for insert
  to anon
  with check (bucket_id = 'samjuba-uploads');

-- No select/list/update/delete policies for anon — uploaders can put files
-- in, but they can't list or remove what anyone else uploaded.
```

### 6. Environment variables

Copy `.env.example` to `.env` and fill in:

```env
PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
PUBLIC_SUPABASE_ANON_KEY=...your anon public key...
PUBLIC_SUPABASE_BUCKET=samjuba-uploads
PUBLIC_UPLOADS_TABLE=uploads
```

The `anon` key is a public credential — safe to ship to the browser. Security
for open uploads comes from the RLS policies above (anon = INSERT only).

### 7. Adobe Fonts

In [`src/app.html`](src/app.html) replace `REPLACE_WITH_KIT_ID` in the
`<link rel="stylesheet" href="https://use.typekit.net/...css" />` tag with
your Adobe Fonts web project ID. The project must publish the
`skolar-gujarati`, `square-peg`, and `work-sans` families.

---

## Local development

```bash
pnpm install
pnpm dev
```

Open http://localhost:5173.

To validate against real Supabase, fill `.env` with real values first.

---

## Production build (without Docker)

```bash
pnpm build
node build/index.js   # listens on $PORT (default 3000)
```

The public env vars are baked into the client bundle at `pnpm build` time —
re-run the build whenever they change.

---

## Deploy with Docker

The `.env` file in the project root drives both the build args and the
runtime container.

```bash
# one-time
docker compose build

# run
docker compose up -d

# update after pulling new code
docker compose build --no-cache && docker compose up -d
```

The site is then on port 3000 — put nginx/Caddy/Cloudflare Tunnel in front
for TLS.

Sanity check from an actual phone on cellular before sharing the URL.
That's the real test of the large-file / resumable upload path; desktop wifi
will not catch the same issues.

---

## Backups — important

Supabase Pro keeps backups for only **7 days**. These photos are
irreplaceable. After the collection period is over (or periodically during),
pull the bucket down to local storage and a separate cloud (Backblaze B2,
S3, an external drive — anywhere that isn't Supabase). The simplest way:

```bash
# requires the Supabase CLI, logged in
supabase storage cp -r ss://samjuba-uploads ./backup
```

…or just use the dashboard to download each file. Either way: **do not skip
this step.**

---

## How uploads work (under the hood)

- The page exposes one button → native file picker (`accept="image/*,video/*"
  multiple`).
- Selected files go into a queue with **3 in flight at a time** —
  parallelized enough to feel fast, bounded enough not to overwhelm mobile
  connections.
- Each file shows its own progress; a failure on one file does not stall the
  others, and each failed file can be retried independently.
- Files **≥ 6 MiB** use the resumable [TUS](https://tus.io) protocol against
  Supabase's `/storage/v1/upload/resumable` endpoint, so a dropped connection
  mid-video doesn't restart from zero. Smaller files use a plain
  `POST /storage/v1/object/<bucket>/<path>` with XHR for progress.
- After a successful upload, one row is inserted into the `uploads` table
  with the storage path, original filename, content type, and size.

All of this happens **directly from the browser** — there is no server
proxying file bytes, so there's nothing to scale and there's no per-upload
cost beyond Supabase's normal storage pricing.

---

## Out of scope for v1 (planned next)

- Admin view to browse, download, and delete uploads
- Family-facing viewer / slideshow
- Bulk export / automated backup script
- Optional "your name" field on uploads
- Abuse mitigation (passphrase gate, unguessable URL) — v1 is intentionally
  open per the owner's decision

All file metadata lives in the `uploads` table, so adding any of the above
later is straightforward.
