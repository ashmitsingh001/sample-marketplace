# Module 2 Architecture Plan: Ingestion Pipeline

## 🔄 High-Level Workflow Stages

### 1. Trigger & Pre-flight
*   **Trigger:** `push` event filtered to `incoming/**`.
*   **Pre-flight:** Check GitHub secrets (Supabase Key, TG Bot Token). Clean workspace.

### 2. Pack Discovery & Initialization
*   **Step:** Identify ZIP packs in `/incoming`.
*   **Logic:** For each pack:
    1.  **Register/Lookup in DB:** Check Supabase for a record matching the ZIP filename (`external_id`). Create if missing with `needs_review = TRUE`.
    2.  **Telegram Upload (ZIP):** Upload the full ZIP once and store the `pack_file_id` in the `packs` table.
    3.  **Context:** Use this `pack_id` for all child samples.

### 3. Sample Processing Loop (Recursive)
*   **Limit:** 300–500 files per run.
*   **Logic:** For each `.wav`/`.mp3`:
    1.  **Sanitize Filename:** Convert to `lowercase_snake_case`. Handle collisions by appending a short hash if same filename exists in `pack_id`.
    2.  **Idempotency Check:** Skip ONLY if `processing_status = 'completed'` AND `preview_url` IS NOT NULL AND `waveform_json_url` IS NOT NULL.
    3.  **State Update:** Set `processing_status = 'processing'`. (Status allows retry if in `failed` state).
    4.  **Metadata Extraction:** Pattern match filename (Case-insensitive, normalized keys: e.g., "Fm", "F#").
    5.  **Preview/Waveform Gen:** 128kbps MP3 + JSON Peaks.
    6.  **Storage:** Upload to Supabase Storage: `{pack_slug}/{sanitized_filename}.mp3`.
    7.  **Finalize:** Update record and set `processing_status = 'completed'`.
    8.  **Error Handling:** Set `processing_status = 'failed'`, log to `errors.json`, and continue.

### 4. Error Logging & Reporting
*   **Step:** Capture failed extractions or uploads.
*   **Output:** Generate `ingestion_report.json` and commit to a `/logs` folder or post as a GitHub Action notice.
*   **Flagging:** Update `needs_review = TRUE` in DB for any samples with fallback metadata.

---

## 🛠️ Modular Script Components

| Module | Responsibility |
| :--- | :--- |
| `ingestion.yml` | GA Orchestration, environment setup, python installation. |
| `main.py` | Command-line entry point, unzipping, looping, and error collection. |
| `metadata_extractor.py` | Regex logic and validation rules for filename parsing. |
| `storage_manager.py` | Abstraction for Telegram (Telethon/Requests) and Supabase (HTTP API). |
| `audio_processor.py` | Wrapper for `ffmpeg` and `audiowaveform` commands. |

---

## ⚡ Index & Performance Dependencies
*   Relies on `samples_pack_id_filename_idx` (Unique constraint) to prevent duplicates during concurrent runs or partial restarts.

## 🔍 Metadata Extraction Patterns (Regex Logic)

The `metadata_extractor` will prioritize extracting Key and BPM from filenames using the following patterns:

*   **BPM Pattern:** `(\d{2,3})(?=\s?bpm|BPM|_bpm|_)`
    *   *Matches:* `124bpm`, `124 BPM`, `_124_`, `Kick 128.wav`.
*   **Musical Key Pattern:** `\b([A-G][#b]?m?)\b` (Refined to avoid false positives)
    *   *Matches:* `Am`, `C#`, `Fm`, `G`.
*   **Fallback:** If no match, set `bpm = 0`, `musical_key = 'Unknown'`, and `validation_flag = 'needs_review'`.

## 📤 Telegram Primary Upload Logic

*   **Client:** Using `Requests` with the Telegram Bot API (for ZIPs up to 50MB) OR `Telethon` (if packs > 50MB, but requires User Session).
*   **Constraint:** Since we target zero-budget and GitHub Actions (headless), we will prioritize the **Bot API** for the ZIP upload if possible, or use a "Split ZIP" strategy if files exceed 50MB of Bot limit (up to 2GB via Bot API is possible now with some tricks).
*   **Storage ID:** The returned `file_id` is stored in `packs.pack_file_id`.

---

## 📊 Error Reporting System

*   **`errors.json`**: List of specific files that failed processing with the stack trace.
*   **`processing_report.json`**: Summary statistics (Processed: X, Skipped: Y, Failed: Z).
