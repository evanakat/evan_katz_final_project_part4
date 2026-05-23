const publicSupplyCo = require('./publicSupplyCo');
const budgetWholesale = require('./budgetWholesale');
const premiumDistributors = require('./premiumDistributors');
const tradeOnlySupply = require('./tradeOnlySupply');

const ADAPTERS = [publicSupplyCo, budgetWholesale, premiumDistributors, tradeOnlySupply];

const byId = new Map(ADAPTERS.map(a => [a.id, a]));

function listAdapters() {
  return ADAPTERS.map(a => ({
    id: a.id,
    name: a.name,
    tagline: a.tagline,
    authType: a.authType,
    credentialFields: a.credentialFields,
  }));
}

function getAdapter(id) {
  return byId.get(id);
}

module.exports = { ADAPTERS, listAdapters, getAdapter };
