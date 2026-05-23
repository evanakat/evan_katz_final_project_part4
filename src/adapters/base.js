/**
 * Wholesaler adapter contract.
 *
 * Implementations expose:
 *   - id, name, authType ('none' | 'basic' | 'apiKey' | 'oauth')
 *   - credentialFields: [{ name, label, type }] (only when authType !== 'none')
 *   - verifyCredentials(creds): Promise<{ ok: boolean, message?: string }>
 *   - searchProducts({ query, creds }): Promise<Product[]>
 *
 * Product shape:
 *   { sku, name, unit, price, currency, stock, minOrderQty, shipsIn, productUrl }
 */
class WholesalerAdapter {
  constructor(meta) {
    Object.assign(this, meta);
  }
  async verifyCredentials() { return { ok: true }; }
  async searchProducts() { return []; }
}

module.exports = { WholesalerAdapter };
