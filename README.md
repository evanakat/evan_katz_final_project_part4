# Wholesaler Pricing Comparison

Search a product across every connected wholesaler at once and see who has
the best price, stock, and lead time side-by-side. Wholesalers that gate
pricing behind a login can be connected once and are then included in every
search automatically — credentials are encrypted at rest with AES-256-GCM.

## Quick start

```bash
npm install
npm start
# open http://localhost:3000
```

By default the app runs against four mock wholesalers so you can see the
full flow without real B2B accounts:

| Wholesaler            | Auth        | Demo credentials                            |
|-----------------------|-------------|---------------------------------------------|
| Public Supply Co.     | none        | —                                           |
| Budget Wholesale      | none        | —                                           |
| Premium Distributors  | username/pw | any account number, password `demo-pass`    |
| Trade-Only Supply     | API key     | any key starting with `tk_` (e.g. `tk_demo123`) |

## How it works

- **Search** (`GET /api/search?q=...`) fans out to every adapter in parallel.
  Public catalogs always return offers; login-gated wholesalers return offers
  only when the signed-in user has saved credentials for them. The response
  also includes a pivoted `comparison` array with the best price per SKU.
- **Connections** (`POST /api/wholesalers/:id/connect`) calls the adapter's
  `verifyCredentials` first; only verified credentials are encrypted and
  stored. Disconnecting removes the row entirely.
- **Credentials** are encrypted with AES-256-GCM using a key derived from
  `CREDENTIAL_KEY` (set this in production — the default is a clearly-marked
  dev-only key). Decrypted credentials live only in memory during a search.

## Adding a real wholesaler

Implement the adapter contract in `src/adapters/base.js`:

```js
const { WholesalerAdapter } = require('./base');

module.exports = new WholesalerAdapter({
  id: 'my-wholesaler',
  name: 'My Wholesaler',
  tagline: 'B2B catalog',
  authType: 'basic',            // 'none' | 'basic' | 'apiKey' | 'oauth'
  credentialFields: [
    { name: 'username', label: 'Username', type: 'text' },
    { name: 'password', label: 'Password', type: 'password' },
  ],
  async verifyCredentials(creds) {
    // call wholesaler auth endpoint, return { ok, message? }
  },
  async searchProducts({ query, creds }) {
    // call wholesaler pricing API, return Product[]
  },
});
```

Then register it in `src/adapters/index.js`. The search and connection UI
pick it up automatically — no other changes needed.

## Layout

```
server.js                  Express entry
src/db.js                  SQLite schema (users, sessions, connections)
src/crypto.js              AES-256-GCM helpers for stored credentials
src/auth.js                Cookie-session auth
src/routes/
  auth.js                  /api/auth/{login,logout,me}
  wholesalers.js           /api/wholesalers, connect / disconnect
  search.js                /api/search — parallel fan-out + comparison pivot
src/adapters/
  base.js                  Adapter contract
  catalog.js               Shared mock product catalog & pricing helpers
  publicSupplyCo.js        Open catalog (no auth)
  budgetWholesale.js       Open catalog (no auth)
  premiumDistributors.js   Basic auth (username + password)
  tradeOnlySupply.js       API-key auth
  index.js                 Registry
public/                    Vanilla JS frontend (no build step)
```

## Configuration

| Env var          | Purpose                                                          |
|------------------|------------------------------------------------------------------|
| `PORT`           | HTTP port (default `3000`).                                      |
| `CREDENTIAL_KEY` | Encryption key for stored wholesaler credentials. **Set this** in any non-dev environment. |
