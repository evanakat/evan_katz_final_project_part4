const { WholesalerAdapter } = require('./base');
const { findByKeyword, BASE_PRICES, priceFor } = require('./catalog');

const ID = 'budget-wholesale';
const STOCK = ['BOLT-SS-100', 'GLOVE-WK-L', 'GOG-SAFETY-10', 'MICROFIBER-50', 'TAPE-DUCT-12', 'PAINT-WHT-5G', 'DRILL-20V-KIT'];

module.exports = new WholesalerAdapter({
  id: ID,
  name: 'Budget Wholesale',
  tagline: 'Lowest prices on bulk consumables',
  authType: 'none',
  credentialFields: [],
  async searchProducts({ query }) {
    return findByKeyword(query)
      .filter(p => STOCK.includes(p.sku))
      .map(p => ({
        sku: p.sku,
        name: p.name,
        unit: p.unit,
        price: priceFor(ID, p.sku, BASE_PRICES[p.sku], 0.22),
        currency: 'USD',
        stock: 50 + (p.sku.length * 7) % 250,
        minOrderQty: 5,
        shipsIn: '5-7 business days',
        productUrl: `https://example.com/budget/${p.sku.toLowerCase()}`,
      }));
  },
});
