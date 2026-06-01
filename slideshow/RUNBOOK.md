# Ba's Memorial Slideshow — Runbook

A local, offline slideshow. Random shuffle, loops forever, 30s per photo,
gentle crossfade, video plays full length with sound. No internet needed
once photos are downloaded.

## Files in this folder
- `download.mjs`     — pulls all photos from Supabase into ./photos  (you already have this working)
- `preprocess.py`    — converts HEIC/HEIF → JPG, auto-rotates, copies video, writes manifest.json
- `serve.mjs`        — tiny local web server (no dependencies)
- `photos_ready/`    — the finished assets + `index.html` slideshow + `manifest.json`

---

## DO THIS TONIGHT (don't wait until morning)

### 1. Download the photos (if not already done)
```
node download.mjs          # creates ./photos with ~300 files
```

### 2. Convert + build the manifest
```
pip install pillow pillow-heif      # one time only
python3 preprocess.py               # creates ./photos_ready + manifest.json
```
Watch the output. Every file should show ✓. If any HEIC shows ✗, tell me —
but pillow-heif handled them in testing, so they should convert fine.

### 3. Test the slideshow locally
```
node serve.mjs photos_ready 8080
```
Open **http://localhost:8080** in Chrome. Click to start (this triggers
fullscreen + enables video sound — required by the browser).

Let it run a few minutes. Check:
- [ ] Photos advance every ~30s with a smooth fade
- [ ] Portrait photos are upright (not sideways)
- [ ] The .mov plays WITH SOUND and the slideshow continues after it ends
- [ ] No photo gets "stuck" (a broken file auto-skips)

### 4. Set your laptop so it won't sleep
- Disable screen lock / sleep / screensaver in system settings.
- Plug in the charger.
- Set volume to a sensible level for the video.

---

## TOMORROW MORNING (at the venue)

1. Connect laptop to projector. Set display to **mirror** (or extend and drag
   the browser to the projector, then fullscreen there).
2. Open a terminal in this folder:
   ```
   node serve.mjs photos_ready 8080
   ```
3. Open **http://localhost:8080** in Chrome.
4. Press **F11** (or it auto-fullscreens on click). Click once to begin.
5. Walk away. It loops forever and reshuffles each pass.

### Controls
- `f` — re-enter fullscreen if needed
- Move mouse to a corner / `Esc` — exit fullscreen
- Refresh the page to restart with a fresh shuffle

---

## If something goes wrong
- **Black screen / "could not load manifest":** you must open via
  http://localhost:8080, NOT by double-clicking index.html (file:// blocks fetch).
- **Video has no sound:** make sure you *clicked* to start (autoplay-with-sound
  needs that gesture); check laptop volume + projector audio cable.
- **A photo is sideways:** re-run `preprocess.py`; it bakes in rotation.
- **HEIC didn't convert:** `pip install --upgrade pillow-heif` and re-run.
- **Port 8080 busy:** `node serve.mjs photos_ready 8090` and use that port.
