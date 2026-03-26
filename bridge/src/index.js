/**
 * Samply Download Bridge — Cloudflare Worker
 * Version: 1.0.0
 *
 * Routes:
 *   GET /download/pack/:pack_id  → Streams the full ZIP from Telegram
 *
 * Environment Variables (set via wrangler secret put):
 *   TELEGRAM_BOT_TOKEN
 *   SUPABASE_SERVICE_ROLE_KEY
 *   SUPABASE_URL
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
      return handlePackDownload(packId, env);
    }

    return new Response(JSON.stringify({ error: 'Not Found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
    });
  },
};

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
        'Cache-Control': 'no-store',
        ...CORS_HEADERS,
      },
    });
  } catch (err) {
    console.error('Bridge error:', err);
    return jsonError(500, 'Internal server error.');
  }
}

/**
 * Fetches a pack's metadata from Supabase using service role key.
 * Returns the pack object or null if not found / inactive.
 */
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

  if (!resp.ok) {
    console.error('Supabase error:', await resp.text());
    return null;
  }

  const data = await resp.json();
  return Array.isArray(data) && data.length > 0 ? data[0] : null;
}

/**
 * Resolves a Telegram file_id to a direct download URL.
 * Uses the /getFile Bot API endpoint.
 */
async function getTelegramDownloadUrl(fileId, env) {
  const resp = await fetch(
    `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getFile?file_id=${fileId}`
  );

  if (!resp.ok) {
    console.error('Telegram getFile failed:', await resp.text());
    return null;
  }

  const data = await resp.json();
  if (!data.ok || !data.result?.file_path) {
    console.error('Telegram getFile bad response:', data);
    return null;
  }

  return `https://api.telegram.org/file/bot${env.TELEGRAM_BOT_TOKEN}/${data.result.file_path}`;
}

/**
 * Helper: Returns a JSON error response.
 */
function jsonError(status, message) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { 'Content-Type': 'application/json', ...CORS_HEADERS },
  });
}
