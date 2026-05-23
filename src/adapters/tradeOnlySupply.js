const { WholesalerAdapter } = require('./base');
const { findByKeyword, BASE_PRICES, priceFor } = require('./catalog');

const ID = 'trade-only-supply';
const STOCK = ['IMPACT-12-PNEU', 'DRILL-20V-KIT', 'PAINT-WHT-5G', 'TAPE-DUCT-12', 'WIRE-GALV-100', 'LED-SHOP-4FT', 'BOLT-SS-100'];

/**
 * Login-gated wholesaler using API key auth (common for B2B portals).
 * Mock key accepted: any non-empty string starting with "tk_".
 */
module.exports = new WholesalerAdapter({
  id: ID,
  name: 'Trade-Only Supply',
  tagline: 'API key required — net 30 trade accounts',
  authType: 'apiKey',
  credentialFields: [
    { name: 'apiKey', label: 'API Key (starts with tk_)', type: 'password' },
  ],
  async verifyCredentials(creds) {
    if (!creds || !creds.apiKey) {
      return { ok: false, message: 'API key is required.' };
    }
    if (!creds.apiKey.startsWith('tk_') || creds.apiKey.length < 8) {
      return { ok: false, message: 'API key must start with "tk_" and be at least 8 characters. (Demo: tk_demo123)' };
    }
    return { ok: true, message: 'API key verified.' };
  },
  async searchProducts({ query, creds }) {
    const verified = await this.verifyCredentials(creds);
    if (!verified.ok) {
      const err = new Error(verified.message);
      err.code = 'AUTH_FAILED';
      throw err;
    }
    return findByKeyword(query)
      .filter(p => STOCK.includes(p.sku))
      .map(p => ({
        sku: p.sku,
        name: p.name,
        unit: p.unit,
        price: priceFor(ID, p.sku, BASE_PRICES[p.sku] * 0.92, 0.14),
        currency: 'USD',
        stock: 75 + (p.sku.length * 9) % 350,
        minOrderQty: 1,
        shipsIn: '2-4 business days',
        productUrl: `https://example.com/trade-only/${p.sku.toLowerCase()}`,
      }));
  },
});
