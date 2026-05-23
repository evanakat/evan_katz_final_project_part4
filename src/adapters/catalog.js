/**
 * Shared mock catalog: each wholesaler stocks a subset of these products
 * at different price points / stock levels. In a real integration these
 * would come from the wholesaler's API.
 */
const PRODUCTS = [
  { sku: 'BOLT-SS-100', name: 'Stainless Steel Bolts (Box of 100)', unit: 'box', keywords: ['bolt', 'fastener', 'hardware', 'stainless'] },
  { sku: 'GLOVE-WK-L', name: 'Industrial Work Gloves — Size L', unit: 'pair', keywords: ['glove', 'safety', 'ppe'] },
  { sku: 'LED-SHOP-4FT', name: 'LED Shop Light 4ft 5000K', unit: 'each', keywords: ['led', 'light', 'shop', 'lighting'] },
  { sku: 'IMPACT-12-PNEU', name: 'Pneumatic Impact Wrench 1/2"', unit: 'each', keywords: ['wrench', 'impact', 'pneumatic', 'tool'] },
  { sku: 'GOG-SAFETY-10', name: 'Safety Goggles (Pack of 10)', unit: 'pack', keywords: ['goggles', 'safety', 'ppe'] },
  { sku: 'DRILL-20V-KIT', name: 'Cordless Drill 20V Kit', unit: 'kit', keywords: ['drill', 'cordless', 'tool', 'kit'] },
  { sku: 'MICROFIBER-50', name: 'Microfiber Cleaning Cloths (Pack of 50)', unit: 'pack', keywords: ['microfiber', 'cleaning', 'cloth'] },
  { sku: 'WIRE-GALV-100', name: 'Galvanized Steel Wire 100ft', unit: 'roll', keywords: ['wire', 'steel', 'galvanized'] },
  { sku: 'TAPE-DUCT-12', name: 'Heavy Duty Duct Tape (Case of 12)', unit: 'case', keywords: ['tape', 'duct', 'adhesive'] },
  { sku: 'PAINT-WHT-5G', name: 'Interior Latex Paint White (5 Gal)', unit: 'pail', keywords: ['paint', 'latex', 'interior'] },
];

function findByKeyword(query) {
  if (!query) return PRODUCTS;
  const q = query.toLowerCase();
  return PRODUCTS.filter(p =>
    p.name.toLowerCase().includes(q) ||
    p.sku.toLowerCase().includes(q) ||
    p.keywords.some(k => k.includes(q))
  );
}

/** Deterministic per-wholesaler pricing so users see consistent numbers. */
function priceFor(wholesalerId, sku, basePrice, variancePct = 0.18) {
  let hash = 0;
  const s = `${wholesalerId}::${sku}`;
  for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  const rand = (hash % 1000) / 1000;
  const factor = 1 - variancePct + rand * (variancePct * 2);
  return Math.round(basePrice * factor * 100) / 100;
}

const BASE_PRICES = {
  'BOLT-SS-100': 24.50,
  'GLOVE-WK-L': 8.75,
  'LED-SHOP-4FT': 32.00,
  'IMPACT-12-PNEU': 165.00,
  'GOG-SAFETY-10': 21.40,
  'DRILL-20V-KIT': 119.00,
  'MICROFIBER-50': 18.20,
  'WIRE-GALV-100': 27.30,
  'TAPE-DUCT-12': 44.90,
  'PAINT-WHT-5G': 89.00,
};

module.exports = { PRODUCTS, BASE_PRICES, findByKeyword, priceFor };
