const { WholesalerAdapter } = require('./base');
const { findByKeyword, BASE_PRICES, priceFor } = require('./catalog');

const ID = 'public-supply-co';
const STOCK = ['BOLT-SS-100', 'GLOVE-WK-L', 'LED-SHOP-4FT', 'GOG-SAFETY-10', 'MICROFIBER-50', 'TAPE-DUCT-12', 'WIRE-GALV-100'];

module.exports = new WholesalerAdapter({
  id: ID,
  name: 'Public Supply Co.',
  tagline: 'Open catalog, no account needed',
  authType: 'none',
  credentialFields: [],
  async searchProducts({ query }) {
    return findByKeyword(query)
      .filter(p => STOCK.includes(p.sku))
      .map(p => ({
        sku: p.sku,
        name: p.name,
        unit: p.unit,
        price: priceFor(ID, p.sku, BASE_PRICES[p.sku], 0.12),
        currency: 'USD',
        stock: 100 + (p.sku.length * 13) % 400,
        minOrderQty: 1,
        shipsIn: '3-5 business days',
        productUrl: `https://example.com/public-supply/${p.sku.toLowerCase()}`,
      }));
  },
});
