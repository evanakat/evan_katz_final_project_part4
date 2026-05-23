const { WholesalerAdapter } = require('./base');
const { findByKeyword, BASE_PRICES, priceFor } = require('./catalog');

const ID = 'premium-distributors';
const STOCK = ['IMPACT-12-PNEU', 'DRILL-20V-KIT', 'LED-SHOP-4FT', 'BOLT-SS-100', 'WIRE-GALV-100', 'PAINT-WHT-5G'];

/**
 * Login-gated wholesaler. Trade accounts only — pricing is account-specific
 * (negotiated tier), so credentials must be on file before we can quote.
 *
 * In a real integration, verifyCredentials would call the wholesaler's auth
 * endpoint and persist a session token; searchProducts would call their
 * pricing API with that token. The mock accepts any username with the
 * password "demo-pass" to demonstrate both the success and failure paths.
 */
module.exports = new WholesalerAdapter({
  id: ID,
  name: 'Premium Distributors',
  tagline: 'Trade accounts only — login required for pricing',
  authType: 'basic',
  credentialFields: [
    { name: 'accountNumber', label: 'Account Number', type: 'text' },
    { name: 'password', label: 'Portal Password', type: 'password' },
  ],
  async verifyCredentials(creds) {
    if (!creds || !creds.accountNumber || !creds.password) {
      return { ok: false, message: 'Account number and password are required.' };
    }
    if (creds.password !== 'demo-pass') {
      return { ok: false, message: 'Invalid credentials. (Hint: demo password is "demo-pass".)' };
    }
    return { ok: true, message: `Verified account ${creds.accountNumber}.` };
  },
  async searchProducts({ query, creds }) {
    const verified = await this.verifyCredentials(creds);
    if (!verified.ok) {
      const err = new Error(verified.message);
      err.code = 'AUTH_FAILED';
      throw err;
    }
    // Trade-account pricing: meaningfully better than public wholesalers.
    return findByKeyword(query)
      .filter(p => STOCK.includes(p.sku))
      .map(p => ({
        sku: p.sku,
        name: p.name,
        unit: p.unit,
        price: priceFor(ID, p.sku, BASE_PRICES[p.sku] * 0.85, 0.10),
        currency: 'USD',
        stock: 200 + (p.sku.length * 11) % 600,
        minOrderQty: 10,
        shipsIn: '1-2 business days',
        productUrl: `https://example.com/premium/${p.sku.toLowerCase()}`,
      }));
  },
});
