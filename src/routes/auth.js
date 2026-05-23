const express = require('express');
const { COOKIE_NAME, loginOrRegister, userFromRequest, logout } = require('../auth');

const router = express.Router();

router.post('/login', (req, res) => {
  try {
    const { user, token } = loginOrRegister(req.body && req.body.email);
    res.cookie(COOKIE_NAME, token, {
      httpOnly: true,
      sameSite: 'lax',
      maxAge: 1000 * 60 * 60 * 24 * 30,
    });
    res.json({ user: { id: user.id, email: user.email } });
  } catch (e) {
    res.status(400).json({ error: e.message });
  }
});

router.post('/logout', (req, res) => {
  logout(req);
  res.clearCookie(COOKIE_NAME);
  res.json({ ok: true });
});

router.get('/me', (req, res) => {
  const user = userFromRequest(req);
  res.json({ user: user ? { id: user.id, email: user.email } : null });
});

module.exports = router;
