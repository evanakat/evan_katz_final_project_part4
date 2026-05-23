const express = require('express');
const { userFromRequest } = require('../auth');
const { ADAPTERS } = require('../adapters');
const wholesalerRoutes = require('./wholesalers');

const router = express.Router();

/**
 * Search across every wholesaler in parallel.
 *
 * Public wholesalers always return results. Login-gated wholesalers return
 * results only when the signed-in user has connected credentials; otherwise
 * we return a structured "requiresConnection" entry so the UI can prompt.
 */
router.get('/', async (req, res) => {
  const user = userFromRequest(req);
  const query = String(req.query.q || '').trim();

  const tasks = ADAPTERS.map(async adapter => {
    if (adapter.authType === 'none') {
      try {
        const products = await adapter.searchProducts({ query });
        return { wholesaler: meta(adapter), products, status: 'ok' };
      } catch (e) {
        return { wholesaler: meta(adapter), products: [], status: 'error', message: e.message };
      }
    }

    if (!user) {
      return {
        wholesaler: meta(adapter),
        products: [],
        status: 'requires_signin',
        message: 'Sign in to connect this wholesaler and see pricing.',
      };
    }

    const creds = wholesalerRoutes.loadCredentials(user.id, adapter.id);
    if (!creds) {
      return {
        wholesaler: meta(adapter),
        products: [],
        status: 'requires_connection',
        message: 'Connect your account on the Wholesalers page to see pricing.',
      };
    }

    try {
      const products = await adapter.searchProducts({ query, creds });
      return { wholesaler: meta(adapter), products, status: 'ok' };
    } catch (e) {
      const code = e.code === 'AUTH_FAILED' ? 'auth_failed' : 'error';
      return { wholesaler: meta(adapter), products: [], status: code, message: e.message };
    }
  });

  const results = await Promise.all(tasks);
  res.json({ query, results, comparison: buildComparison(results) });
});

function meta(adapter) {
  return { id: adapter.id, name: adapter.name, authType: adapter.authType };
}

/**
 * Pivot results into a per-SKU comparison table.
 * For each SKU we get all offers ordered by price ascending plus the cheapest.
 */
function buildComparison(results) {
  const bySku = new Map();
  for (const r of results) {
    if (r.status !== 'ok') continue;
    for (const p of r.products) {
      if (!bySku.has(p.sku)) bySku.set(p.sku, { sku: p.sku, name: p.name, unit: p.unit, offers: [] });
      bySku.get(p.sku).offers.push({
        wholesalerId: r.wholesaler.id,
        wholesalerName: r.wholesaler.name,
        price: p.price,
        currency: p.currency,
        stock: p.stock,
        minOrderQty: p.minOrderQty,
        shipsIn: p.shipsIn,
        productUrl: p.productUrl,
      });
    }
  }
  return Array.from(bySku.values())
    .map(row => {
      row.offers.sort((a, b) => a.price - b.price);
      row.cheapest = row.offers[0] || null;
      row.highest = row.offers[row.offers.length - 1] || null;
      row.spread = row.offers.length > 1 ? Math.round((row.highest.price - row.cheapest.price) * 100) / 100 : 0;
      row.spreadPct = row.cheapest && row.cheapest.price > 0
        ? Math.round((row.spread / row.cheapest.price) * 1000) / 10
        : 0;
      return row;
    })
    .sort((a, b) => a.name.localeCompare(b.name));
}

module.exports = router;
