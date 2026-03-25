# Module 1: Database Schema Architecture Plan

## 📁 Tables Overview (REFINED)

### 1. `packs` (The Collections)
*   **Purpose:** Stores metadata for sample packs (ZIPs).
*   **Key Fields:**
    *   `id` (uuid): Primary key.
    *   `external_id` (text): Google Sheets row identifier for idempotent sync.
    *   `source` (text): Default "sheets".
    *   `title` (text): UI display name.
    *   `slug` (text): URL-friendly unique identifier.
    *   `description` (text): Markdown/HTML description.
    *   `type` (text): Pack category.
    *   `price` (numeric): Selling price.
    *   `cover_url` (text): CDN link to artwork.
    *   `is_active` (boolean): Visibility toggle.
    *   `is_deleted` (boolean): Soft delete flag.
    *   `last_synced_at` (timestamptz): Sync tracking.

### 2. `samples` (The Individual Sounds)
*   **Purpose:** High-volume metadata for individual samples.
*   **Key Fields:**
    *   `id` (uuid): Primary key.
    *   `pack_id` (uuid): FK to `packs`.
    *   `filename` (text): Original file name.
    *   `file_id` (text): **INTERNAL ONLY**. Not exposed in default SELECTs.
    *   `bpm` (integer): Filterable BPM.
    *   `musical_key` (text): Filterable key.
    *   `category` (text): Filterable category.
    *   `preview_url` (text): CDN audio link.
    *   `extra_metadata` (jsonb): Non-filterable data (duration, sample_rate, etc.).
    *   `is_active` (boolean): Sample-level toggle.
    *   `created_at` (timestamptz): Creation timestamp.

### 3. `purchases` (Access Control)
*   **Purpose:** Tracks user ownership.
*   **Key Fields:**
    *   `id` (uuid): Primary key.
    *   `user_id` (uuid): FK to `auth.users`.
    *   `pack_id` (uuid): FK to `packs`.
    *   `created_at` (timestamptz): Purchase timestamp.
*   **Constraint:** Unique `(user_id, pack_id)`.

---

## 🔗 Relationships
*   **Packs (1) ↔ Samples (N):** One pack contains many samples.
*   **Users (1) ↔ Purchases (N):** Access control mapping.

---

## ⚡ Index Strategy (PHASE 2)
*   **`samples_bpm_idx`**: B-Tree on `bpm` for range/exact filtering.
*   **`samples_key_category_idx`**: Partial or Compound B-Tree on `(musical_key, category)` to speed up multi-filter search.
*   **`packs_slug_idx`**: Unique B-Tree for fast URL routing.
*   **`packs_external_id_idx`**: Unique B-Tree for fast idempotent sync lookups.

---

## 🛡️ RLS & Security Logic (PHASE 2)
*   **Requirement:** `file_id` is hidden from standard API.
*   **Policy `public_visibility`**: Allows `SELECT` on `packs` and `samples` if `is_active = true` AND `is_deleted = false`. 
*   **Policy `purchase_access`**: Only allows a specialized Edge function or internal service to resolve `file_id` by checking `purchases` table for `auth.uid()`.

---

## 🔮 Future-Proofing
*   **`extra_metadata`**: JSONB for non-filterable attributes keeps schema clean.
*   **Soft Delete**: `is_deleted` ensures data safety for sync rollbacks.
