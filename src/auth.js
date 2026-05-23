const crypto = require('crypto');
const db = require('./db');

const COOKIE_NAME = 'wpc_session';

function newToken() {
  return crypto.randomBytes(32).toString('hex');
}

function loginOrRegister(email) {
  const normalized = String(email || '').trim().toLowerCase();
  if (!normalized || !normalized.includes('@')) {
    throw new Error('A valid email is required.');
  }
  let user = db.prepare('SELECT * FROM users WHERE email = ?').get(normalized);
  if (!user) {
    const info = db.prepare('INSERT INTO users (email) VALUES (?)').run(normalized);
    user = { id: info.lastInsertRowid, email: normalized };
  }
  const token = newToken();
  db.prepare('INSERT INTO sessions (token, user_id) VALUES (?, ?)').run(token, user.id);
  return { user, token };
}

function userFromRequest(req) {
  const token = req.cookies && req.cookies[COOKIE_NAME];
  if (!token) return null;
  const row = db.prepare(`
    SELECT u.id, u.email
    FROM sessions s JOIN users u ON u.id = s.user_id
    WHERE s.token = ?
  `).get(token);
  return row || null;
}

function requireUser(req, res, next) {
  const user = userFromRequest(req);
  if (!user) return res.status(401).json({ error: 'Sign in required.' });
  req.user = user;
  next();
}

function logout(req) {
  const token = req.cookies && req.cookies[COOKIE_NAME];
  if (token) db.prepare('DELETE FROM sessions WHERE token = ?').run(token);
}

module.exports = { COOKIE_NAME, loginOrRegister, userFromRequest, requireUser, logout };
