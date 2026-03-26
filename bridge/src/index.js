/**
 * Samply Download Bridge — Cloudflare Worker
 * Version: 1.2.0 (Individual Sample Downloads)
 *
 * Routes:
 *   GET /download/pack/:pack_id?token=...    → Streams full ZIP from Telegram
 *   GET /download/sample/:sample_id?token=... → Streams individual WAV from Telegram
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
      if (!token) return jsonError(403, 'Access denied: missing download token.');
      const tokenValid = await verifyToken(token, packId, env.DOWNLOAD_SECRET);
      if (!tokenValid) return jsonError(403, 'Access denied: invalid or expired token.');
      return handlePackDownload(packId, env);
    }

    // Route: GET /download/sample/:sample_id
    const sampleMatch = path.match(/^\/download\/sample\/([a-f0-9\-]{36})$/i);
    if (sampleMatch) {
      const sampleId = sampleMatch[1];
      const token = url.searchParams.get('token');
      if (!token) return jsonError(403, 'Access denied: missing download token.');
      const tokenValid = await verifyToken(token, sampleId, env.DOWNLOAD_SECRET);
      if (!tokenValid) return jsonError(403, 'Access denied: invalid or expired token.');
      return handleSampleDownload(sampleId, env);
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

// ─── DOWNLOAD HANDLERS ───────────────────────────────────────────────────────

/**
 * Handles full-pack ZIP download.
 */
async function handlePackDownload(packId, env) {
  try {
    const pack = await fetchFromSupabase('packs', packId, 'id,slug,pack_file_id', env);
    if (!pack) return jsonError(404, 'Pack not found or inactive.');
    if (!pack.pack_file_id) return jsonError(503, 'Pack is not ready for download yet.');
    const telegramUrl = await getTelegramDownloadUrl(pack.pack_file_id, env);
    if (!telegramUrl) return jsonError(502, 'Failed to resolve download URL from Telegram.');
    const filename = `${pack.slug || packId}.zip`;
    const upstream = await fetch(telegramUrl);
    if (!upstream.ok) return jsonError(502, 'Failed to stream file from Telegram.');
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
    console.error('Bridge error (pack):', err);
    return jsonError(500, 'Internal server error.');
  }
}

/**
 * Handles individual WAV sample download.
 * Supports both "Pure Streaming" (Supabase Range) and "Legacy" (Telegram) modes.
 */
async function handleSampleDownload(sampleId, env) {
  try {
    const fields = 'id,filename,data_start,data_end,zip_path,is_indexed,sample_file_id,pack_id';
    const sample = await fetchFromSupabase('samples', sampleId, fields, env);
    if (!sample) return jsonError(404, 'Sample not found.');

    const pack = await fetchFromSupabase('packs', sample.pack_id, 'id,storage_provider', env);
    if (!pack) return jsonError(404, 'Associated pack not found.');

    const filename = sample.filename || `${sampleId}.wav`;

    // --- MODE 1: PURE STREAMING (Hybrid Source: R2 or Supabase) ---
    if (sample.is_indexed && sample.zip_path && sample.data_start !== null && sample.data_end !== null) {
      // 1. Validate Bounds
      if (sample.data_start < 0 || sample.data_end <= sample.data_start) {
        console.error(`Invalid range offsets for sample ${sampleId}: ${sample.data_start}-${sample.data_end}`);
        return jsonError(416, 'Requested range not satisfiable: Invalid offsets in database.');
      }

      const filename = sample.filename || `${sampleId}.wav`;
      const key = sample.zip_path; // Object key in R2 or path in Supabase
      const range = { offset: sample.data_start, length: sample.data_end - sample.data_start + 1 };

      // CASE A: Cloudflare R2
      if (pack.storage_provider === 'r2') {
        console.log(`Streaming sample ${sampleId} from Cloudflare R2: ${key} (Range: ${sample.data_start}-${sample.data_end})`);
        
        if (!env.BUCKET) return jsonError(500, 'R2 Bucket binding is missing.');
        
        const object = await env.BUCKET.get(key, { range });
        
        if (!object || !object.body) {
          return jsonError(404, 'Sample object not found in R2 storage.');
        }

        const headers = {
          'Content-Type': 'audio/wav',
          'Content-Disposition': `attachment; filename="${filename}"`,
          'Content-Length': object.size.toString(),
          'Cache-Control': 'no-store',
          ...CORS_HEADERS,
        };

        return new Response(object.body, { status: 206, headers });
      }

      // CASE B: Supabase Storage (Legacy/Fallback)
      const supabaseUrl = `${env.SUPABASE_URL}/storage/v1/object/packs/${key}`;
      const rangeHeader = `bytes=${sample.data_start}-${sample.data_end}`;

      console.log(`Streaming sample ${sampleId} from Supabase: ${key} (Range: ${rangeHeader})`);

      const upstream = await fetch(supabaseUrl, {
        headers: {
          'Authorization': `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
          'Range': rangeHeader
        }
      });

      if (upstream.status === 206 || upstream.status === 200) {
        const headers = {
          'Content-Type': 'audio/wav',
          'Content-Disposition': `attachment; filename="${filename}"`,
          'Content-Length': upstream.headers.get('Content-Length') || '',
          'Cache-Control': 'no-store',
          ...CORS_HEADERS,
        };

        const contentRange = upstream.headers.get('Content-Range');
        if (contentRange) headers['Content-Range'] = contentRange;

        return new Response(upstream.body, { status: upstream.status, headers });
      }

      console.error(`Supabase Range Fetch failed (${upstream.status}):`, await upstream.text());
      return jsonError(502, 'Failed to extract sample from ZIP hub.');
    }

    // --- MODE 2: LEGACY FALLBACK (Telegram) ---
    if (sample.sample_file_id) {
      console.log(`Falling back to Telegram for sample ${sampleId}`);
      const telegramUrl = await getTelegramDownloadUrl(sample.sample_file_id, env);
      if (!telegramUrl) return jsonError(502, 'Failed to resolve download URL from Telegram.');

      const upstream = await fetch(telegramUrl);
      if (!upstream.ok) return jsonError(502, 'Failed to stream sample from Telegram.');

      return new Response(upstream.body, {
        status: 200,
        headers: {
          'Content-Type': 'audio/wav',
          'Content-Disposition': `attachment; filename="${filename}"`,
          'Content-Length': upstream.headers.get('Content-Length') || '',
          'Cache-Control': 'no-store',
          ...CORS_HEADERS,
        },
      });
    }

    return jsonError(503, 'Sample file not available for download (unindexed and no Telegram fallback).');
  } catch (err) {
    console.error('Bridge error (sample):', err);
    return jsonError(500, 'Internal server error.');
  }
}

// ─── SUPABASE + TELEGRAM HELPERS ─────────────────────────────────────────────

/**
 * Generic Supabase record fetcher.
 * Supports both packs and samples tables.
 */
async function fetchFromSupabase(table, id, fields, env) {
  const filters = table === 'packs'
    ? `id=eq.${id}&is_active=eq.true&is_deleted=eq.false`
    : `id=eq.${id}`;
  const resp = await fetch(
    `${env.SUPABASE_URL}/rest/v1/${table}?${filters}&select=${fields}`,
    {
      headers: {
        apikey: env.SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
        'Content-Type': 'application/json',
      },
    }
  );
  if (!resp.ok) { console.error(`Supabase error (${table}):`, await resp.text()); return null; }
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
