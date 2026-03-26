/**
 * Samply Download Bridge — Cloudflare Worker
 * Version: 1.1.0 (Signed Token Auth)
 *
 * Routes:
 *   GET /download/pack/:pack_id?token=...  → Streams the full ZIP from Telegram
 *
 * Token Format (base64url-encoded JSON):
 *   { pack_id, expiry (unix seconds), sig (HMAC-SHA256 hex) }
 *
 * Environment Variables (set via wrangler secret put):
 *   TELEGRAM_BOT_TOKEN
 *   SUPABASE_SERVICE_ROLE_KEY
 *   SUPABASE_URL
 *   DOWNLOAD_SECRET
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    // Route: GET /download/pack/:pack_id
    const packMatch = path.match(/^\/download\/pack\/([a-f0-9\-]{36})$/i);
    if (packMatch) {
      const packId = packMatch[1];
      const token = url.searchParams.get('token');

      // --- TOKEN VALIDATION ---
      if (!token) {
        return jsonError(403, 'Access denied: missing download token.');
      }
      const tokenValid = await verifyToken(token, packId, env.DOWNLOAD_SECRET);
      if (!tokenValid) {
        return jsonError(403, 'Access denied: invalid or expired token.');
      }
      // --- END TOKEN VALIDATION ---

      return handlePackDownload(packId, env);
    }

    return new Response(JSON.stringify({ error: 'Not Found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  },
};

// ─── TOKEN VERIFICATION ────────────────────────────────────────────────────────

/**
 * Verifies a signed download token.
 * Returns true if valid, false otherwise.
 */
async function verifyToken(token, packId, secret) {
  try {
    // 1. Decode base64url JSON payload
    const payload = JSON.parse(atob(token.replace(/-/g, '+').replace(/_/g, '/')));
    const { pack_id, expiry, sig } = payload;

    // 2. Validate fields exist
    if (!pack_id || !expiry || !sig) return false;

    // 3. Check pack_id matches URL (prevents token reuse across packs)
    if (pack_id !== packId) return false;

    // 4. Check expiry (unix seconds)
    if (Date.now() / 1000 > expiry) return false;

    // 5. Verify HMAC-SHA256 signature
    const expectedSig = await computeHmac(secret, pack_id + expiry);
    return expectedSig === sig;
  } catch {
    return false;
  }
}

/**
 * Computes HMAC-SHA256 using the Web Crypto API (available in Cloudflare Workers).
 * Returns a lowercase hex string.
 */
async function computeHmac(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    enc.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signature = await crypto.subtle.sign('HMAC', key, enc.encode(message));
  return Array.from(new Uint8Array(signature))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

// ─── DOWNLOAD HANDLER ─────────────────────────────────────────────────────────

/**
 * Handles full-pack ZIP download.
 * 1. Fetches pack_file_id from Supabase using the pack UUID.
 * 2. Resolves Telegram download URL from file_id.
 * 3. Streams the ZIP bytes directly to the client.
 */
async function handlePackDownload(packId, env) {
  try {
    // Step 1: Fetch pack record from Supabase
    const pack = await fetchPackFromSupabase(packId, env);
    if (!pack) {
      return jsonError(404, 'Pack not found or inactive.');
    }
    if (!pack.pack_file_id) {
      return jsonError(503, 'Pack is not ready for download yet.');
    }

    // Step 2: Resolve Telegram download URL
    const telegramUrl = await getTelegramDownloadUrl(pack.pack_file_id, env);
    if (!telegramUrl) {
      return jsonError(502, 'Failed to resolve download URL from Telegram.');
    }

    // Step 3: Stream to client
    const filename = `${pack.slug || packId}.zip`;
    const upstream = await fetch(telegramUrl);
    if (!upstream.ok) {
      return jsonError(502, 'Failed to stream file from Telegram.');
    }

    return new Response(upstream.body, {
      status: 200,
      headers: {
        'Content-Type': 'application/zip',
        'Content-Disposition': `attachment; filename="${filename}"`,
        'Content-Length': upstream.headers.get('Content-Length') || '',
        'Cache-Control': 'no-store',
        ...CORS_HEADERS,
      },
    });
  } catch (err) {
    console.error('Bridge error:', err);
    return jsonError(500, 'Internal server error.');
  }
}

// ─── SUPABASE + TELEGRAM HELPERS ─────────────────────────────────────────────

async function fetchPackFromSupabase(packId, env) {
  const resp = await fetch(
    `${env.SUPABASE_URL}/rest/v1/packs?id=eq.${packId}&is_active=eq.true&is_deleted=eq.false&select=id,slug,pack_file_id`,
    {
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        'Content-Type': 'application/json',
      },
    }
  );
  if (!resp.ok) { console.error('Supabase error:', await resp.text()); return null; }
  const data = await resp.json();
  return Array.isArray(data) && data.length > 0 ? data[0] : null;
}

async function getTelegramDownloadUrl(fileId, env) {
  const resp = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getFile?file_id=${fileId}`
  );
  if (!resp.ok) { console.error('Telegram getFile failed:', await resp.text()); return null; }
  const data = await resp.json();
  if (!data.ok || !data.result?.file_path) { console.error('Telegram bad response:', data); return null; }
  return `https://api.telegram.org/file/bot${env.TELEGRAM_BOT_TOKEN}/${data.result.file_path}`;
}

function jsonError(status, message) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
