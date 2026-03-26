# Samply Download Bridge

Cloudflare Worker that acts as a secure proxy between the Samply marketplace and Telegram file storage.

## Routes

| Route | Description |
| :--- | :--- |
| `GET /download/pack/:pack_id` | Stream full ZIP pack from Telegram |

## Setup

### 1. Install Wrangler
```bash
cd bridge
npm install
```

### 2. Set Secrets (one-time)
```bash
wrangler secret put TELEGRAM_BOT_TOKEN
wrangler secret put SUPABASE_SERVICE_ROLE_KEY
```

### 3. Dev Mode
```bash
npm run dev
```

### 4. Deploy
```bash
npm run deploy
```

## How It Works

1. Frontend calls `/download/pack/{supabase_pack_uuid}`.
2. Worker looks up the `pack_file_id` from Supabase (using service role).
3. Worker calls Telegram `/getFile` to resolve the temporary download URL.
4. Worker **streams** the bytes directly to the user — no RAM buffering.

## Security

- `pack_file_id` is **never** exposed publicly.
- Inactive or deleted packs return `404`.
- Service Role Key is stored as a Cloudflare secret.
