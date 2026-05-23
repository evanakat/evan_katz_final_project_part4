const express = require('express');
const db = require('../db');
const { requireUser } = require('../auth');
const { listAdapters, getAdapter } = require('../adapters');
const { encrypt, decrypt } = require('../crypto');

const router = express.Router();

function connectionsFor(userId) {
  return db.prepare(`
    SELECT wholesaler_id, status, last_verified_at, created_at
    FROM wholesaler_connections WHERE user_id = ?
  `).all(userId);
}

router.get('/', requireUser, (req, res) => {
  const connections = new Map(connectionsFor(req.user.id).map(c => [c.wholesaler_id, c]));
  res.json({
    wholesalers: listAdapters().map(a => ({
      ...a,
      connection: connections.get(a.id) || null,
    })),
  });
});

router.post('/:id/connect', requireUser, async (req, res) => {
  const adapter = getAdapter(req.params.id);
  if (!adapter) return res.status(404).json({ error: 'Unknown wholesaler.' });
  if (adapter.authType === 'none') {
    return res.status(400).json({ error: 'This wholesaler does not require credentials.' });
  }
  const creds = (req.body && req.body.credentials) || {};

  // Confirm the credentials work before persisting them.
  try {
    const verified = await adapter.verifyCredentials(creds);
    if (!verified.ok) return res.status(401).json({ error: verified.message || 'Invalid credentials.' });

    const encrypted = encrypt(JSON.stringify(creds));
    db.prepare(`
      INSERT INTO wholesaler_connections
        (user_id, wholesaler_id, encrypted_credentials, status, last_verified_at)
      VALUES (?, ?, ?, 'connected', datetime('now'))
      ON CONFLICT(user_id, wholesaler_id) DO UPDATE SET
        encrypted_credentials = excluded.encrypted_credentials,
        status = 'connected',
        last_verified_at = datetime('now')
    `).run(req.user.id, adapter.id, encrypted);

    res.json({ ok: true, message: verified.message || 'Connected.' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

router.delete('/:id/connect', requireUser, (req, res) => {
  db.prepare('DELETE FROM wholesaler_connections WHERE user_id = ? AND wholesaler_id = ?')
    .run(req.user.id, req.params.id);
  res.json({ ok: true });
});

/** Return stored credentials for a user+wholesaler, decrypted (server-side use only). */
function loadCredentials(userId, wholesalerId) {
  const row = db.prepare(`
    SELECT encrypted_credentials FROM wholesaler_connections
    WHERE user_id = ? AND wholesaler_id = ?
  `).get(userId, wholesalerId);
  if (!row) return null;
  try {
    return JSON.parse(decrypt(row.encrypted_credentials));
  } catch {
    return null;
  }
}

router.loadCredentials = loadCredentials;

module.exports = router;
