/**
 * Samply Token Generator Utility
 * 
 * Use this on your frontend/backend to generate signed download URLs.
 * The DOWNLOAD_SECRET must match the one set in your Cloudflare Worker.
 *
 * Usage:
 *   const token = await generateDownloadToken(packId, DOWNLOAD_SECRET, 3600);
 *   const url = `https://samply-download-bridge.workers.dev/download/pack/${packId}?token=${token}`;
 */

/**
 * Generates a signed download token.
 * @param {string} packId       - The Supabase UUID of the pack.
 * @param {string} secret       - The shared DOWNLOAD_SECRET.
 * @param {number} ttlSeconds   - Token lifetime in seconds (default: 1 hour).
 * @returns {Promise<string>}   - base64url-encoded signed token.
 */
export async function generateDownloadToken(packId, secret, ttlSeconds = 3600) {
  const expiry = Math.floor(Date.now() / 1000) + ttlSeconds;
  const sig = await computeHmac(secret, packId + expiry);

  const payload = JSON.stringify({ pack_id: packId, expiry, sig });

  // Encode as base64url (URL-safe, no padding issues)
  return btoa(payload)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Computes HMAC-SHA256 using the Web Crypto API.
 * Works in both Cloudflare Workers and modern browsers.
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

// ─── QUICK TEST (Node.js / Browser Console) ──────────────────────────────────
// Replace with real values:
// const token = await generateDownloadToken('your-pack-uuid', 'your-secret', 3600);
// console.log('Token:', token);
