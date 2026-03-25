### 🧾 Project: Sample Marketplace (Zero Budget Architecture)

### 📦 Modules:

* [x] Module 1: Database Schema (Completed)
* [/] Module 2: Ingestion Pipeline (Current)
* [ ] Module 3: Download Bridge
* [ ] Module 4: Security Layer

### 📊 Current Module Progress (Module 2):

* [x] Brainstorming
* [x] Architecture Planning
* [x] Implementation Planning
* [x] Implementation
* [x] Deployment Setup
* [/] Project Review (Current)

### 📁 Files Planned:

* `.github/workflows/ingestion.yml`
* `scripts/process_samples.py` (or .js)
* `scripts/utils/telegram_upload.py`

### 🧠 Decisions Made:

* **Trigger**: GitHub Action on `/incoming/**` push (path-filtered).
* **Processing Limit**: 300–500 files per run, max 60 min runtime.
* **Storage Order**: DB Registration → Telegram ZIP Upload → Sample Processing.
* **Idempotency**: `status='completed' AND previews exist`.
* **State Tracking**: `pending → processing → completed/failed`.
* **Sanitization**: Filenames to `lowercase_snake_case`, case-insensitive regex.
* **Collision Handling**: Short hash/index appending.
* **Concurrency**: `ingest-{pack_slug}` group.
* **Timeout**: Graceful stop at 85% elapsed time.
* **Resume**: Skip `completed` samples.
* **Failure Threshold**: Stop if >30% failures; mark pack `needs_review`.
* **Pack-Level Status**: Added to `packs` table (pending, processing, completed, partial, failed).
* **Logging Persistence**: Artifacts + committed logs for `errors.json`.
* **Metadata Strategy**: Hybrid (Regex + Fallback).
* **Coordination**: Catalog First (lookup via `external_id`).
* **Storage Strategy**: Using Telegram `file_id` based system for zero-budget storage.
* **Backend**: Supabase (PostgreSQL) for structured data and RLS.
* **Authentication**: Exclusively Supabase Auth (no Telegram UID mapping required).
* **Sync Source**: One-Way Sync (Google Sheets as Source of Truth → Supabase).
* **Metadata Strategy**: Standard Columns in `samples` table with controlled normalization.
* **Validation Layer**: Controlled TEXT (flexible) with validation at the ingestion level (Module 2).
* **Table Design**: Expanded with `is_deleted` for both packs and samples.
* **Security Layer**: `file_id` isolated via Column-Level Security (Selective GRANT) + refined RLS (active/deleted filters).

### ⏳ Pending Tasks:

* Complete indexing strategy.
* Design RLS policies.
* Final architecture validation.

### ✅ Completed Tasks:

* System context review.
* Task initialization.
