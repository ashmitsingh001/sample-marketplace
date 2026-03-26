🚀 CONTEXT CONTINUATION — DO NOT RESET

You are working on an Advanced Audio Streaming System for a Sample Marketplace.

This is NOT a simple project.
This is a production-grade system involving:

- Telegram (ZIP storage)
- Supabase (metadata + indexing)
- Cloudflare Workers (streaming + extraction)
- GitHub (code + automation)

---

🎯 FINAL OBJECTIVE

Build a system where:

- User can preview samples instantly (already done ✅)
- User can download individual WAVs WITHOUT storing them separately
- WAV is extracted on-demand from ZIP stored in Telegram
- System works efficiently even for large packs (1GB–10GB)

---

🧠 CORE TECH (MANDATORY)

We will implement:

🔥 ZIP INDEXING SYSTEM + HTTP RANGE STREAMING

Meaning:

- During ingestion → extract file offsets from ZIP
- Store offsets in DB
- During download → fetch only required bytes
- Decompress + stream to user

---

⚠️ STRICT DEVELOPMENT RULES

1. ❌ DO NOT write code immediately
2. ✅ ALWAYS start with Brainstorming
3. ✅ Break tasks into SMALL modules
4. ✅ Maintain FULL CONTEXT HISTORY (logbook style)
5. ✅ After every step:
   - What done
   - What pending
6. ✅ Ask questions when needed
7. ❌ DO NOT assume anything
8. ❌ DO NOT skip validation
9. ❌ DO NOT jump modules
10. ✅ WAIT for approval before coding

---

🧾 LOGBOOK SYSTEM (MANDATORY)

Maintain a persistent log:

📊 Modules Progress

- [x] Module 1: Database Schema
- [x] Module 2: Ingestion Pipeline
- [x] Module 3: Basic Download Bridge
- [ ] Module 2.5: ZIP Indexing Upgrade
- [ ] Module 3.5: Streaming Extraction Worker

---

📌 For EACH task track:

- Status: Pending / In Progress / Done
- Files affected
- Decisions made
- Issues found

---

🧩 MODULE BREAKDOWN

---

🔹 MODULE 2.5 — ZIP INDEXING (CRITICAL)

Goal:

Upgrade ingestion pipeline to:

- Parse ZIP structure
- Extract:
  - filename
  - offset
  - compressed_size
  - uncompressed_size
  - compression_type

Store in DB:

samples table must include:

- zip_offset
- compressed_size
- uncompressed_size
- compression_method

---

🔹 MODULE 3.5 — RANGE STREAMING WORKER

Goal:

Upgrade Cloudflare Worker:

Route:

/download/sample/{sample_id}

Worker must:

1. Fetch sample metadata from Supabase
2. Fetch ZIP from Telegram using HTTP Range
3. Extract ONLY required bytes
4. Decompress if needed
5. Stream to user

---

🧠 CRITICAL DESIGN DECISIONS

You MUST validate:

1. ZIP compression type:
   - Should we enforce STORE (no compression)?
2. Telegram CDN:
   - Confirm Range request support
3. Worker limits:
   - Memory safe streaming design

---

🧠 BRAINSTORMING PHASE (MANDATORY FIRST STEP)

You MUST:

- Explain ZIP structure deeply
- Identify challenges
- Identify edge cases
- Propose 2–3 approaches
- Recommend BEST approach

---

🏗️ ARCHITECTURE PHASE

Design:

- Data flow
- DB schema changes
- Pipeline changes
- Worker flow
- Failure handling

---

📊 FLOWCHART (MANDATORY)

Provide:

1. Ingestion Flow (ZIP → DB index)
2. Download Flow (User → Worker → Telegram → Stream)

Use clear structured diagrams (text-based)

---

⚙️ IMPLEMENTATION PLAN

Break into:

- Step-by-step tasks
- Each task small & testable

Example:

Step 1: Add DB columns
Step 2: Build ZIP parser
Step 3: Store offsets
Step 4: Validate offsets
Step 5: Worker range fetch
Step 6: Streaming

---

❓ INTERACTIVE MODE

At each phase:

👉 Ask questions like:

- Do we enforce no compression ZIP?
- Expected max file size?
- Testing strategy?

---

🧪 TESTING STRATEGY

Design:

- Small ZIP test
- Large ZIP simulation
- Invalid offset handling
- Streaming validation

---

📁 CODE ORGANIZATION

When approved:

Structure like:

/scripts
zip_parser.py
index_builder.py
/workers
sample_stream.js
/database
migrations/

---

⚠️ OUTPUT FORMAT

Phase 1:

- Brainstorming
- Architecture
- Flowcharts

⛔ STOP → WAIT FOR APPROVAL

---

Phase 2:

- Implementation Plan

⛔ STOP → WAIT FOR APPROVAL

---

Phase 3:

- Code

---

🧠 FINAL EXPECTATION

You are NOT writing code.

You are designing a:

🔥 HIGH-PERFORMANCE STREAMING SYSTEM

---

Proceed with:

👉 Phase 1: Brainstorming ONLY

Do not continue without confirmation.


⚠️ CRITICAL INSTRUCTION — SYSTEM UPGRADE MODE

This is NOT a new system.

This is an UPGRADE to an existing production-ready system.

---

RULES:

1. DO NOT modify or break existing modules:
   
   - Module 1 (DB)
   - Module 2 (Ingestion)
   - Module 3 (Download Bridge)

2. ONLY extend functionality via:
   
   - Module 2.5 (ZIP Indexing)
   - Module 3.5 (Streaming Extraction)

3. Maintain FULL backward compatibility

4. All new features must be OPTIONAL and SAFE

5. If any change risks breaking system → STOP and ask

---

GOAL:

Add advanced capability WITHOUT affecting current working system