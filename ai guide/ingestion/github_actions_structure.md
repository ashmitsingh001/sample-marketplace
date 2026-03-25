# GitHub Actions Job Structure — Ingestion Workflow

## 🕒 Workflow Trigger
```yaml
on:
  push:
    paths:
      - 'incoming/**'
  workflow_dispatch: # Allows manual re-run for failed packs
```

## 🏗️ Job: `process-pack`
*   **Runner:** `ubuntu-latest`
*   **Strategy:** Run once per pack detected in the commit.

### Stages (Steps):

#### 1. Setup & Environment
*   `actions/checkout@v4` (Fetch repo).
*   `actions/setup-python@v5` (Install Python 3.11+).
*   `Install Dependencies` (ffmpeg, audiowaveform, python requirements).

#### 2. Pack Discovery
*   Identify targeted ZIPs in `incoming/`.
*   Verify GitHub Secrets are available.

#### 3. Core Processing (The Python Script)
*   **Command:** `python scripts/main.py --pack <path_to_zip>`
*   **Internal Flow:**
    *   **DB Registration:** Call Supabase to ensure `pack_id`.
    *   **Telegram Upload:** ZIP -> Bot API. Verify `file_id`. (CRITICAL: Stop if failure).
    *   **Extraction:** Unzip to temp folder.
    *   **Loop:**
        *   Check Idempotency (DB Check).
        *   Sanitize & Process (FFmpeg/Audiowaveform).
        *   Upload Previews (Supabase Storage).
        *   Update DB (Status = 'completed').
    *   **Reporting:** Generate `reports/processing_report.json`.

#### 4. Post-Processing & Logging
*   **Artifact Upload:** Upload `reports/` folder as a GA artifact.
*   **Notice:** Use `$GITHUB_STEP_SUMMARY` to show a quick table of processed/failed files.
*   **Cleanup:** Delete temp folder and processed ZIP from runner.

---

## 🛡️ Reliability Features
*   **Timeout Handling:** Script periodically checks remaining runner time; if < 10 mins, it gracefully stops the loop and saves current progress.
*   **Retries:** Since `failed` samples remain in the DB, a re-run of the same pack will automatically target only `pending` or `failed` samples.
*   **Concurrency:** `concurrency` group set to `ingestion-${{ pack_name }}` to prevent simultaneous runs of the same pack pack.
