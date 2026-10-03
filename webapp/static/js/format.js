/**
 * format.js - Unified number, currency, and logo formatting for CoinPulse.
 */

import { formatPriceInCurrency, formatVolumeInCurrency } from './currency.js';

export function formatPrice(price, currencyCode = null) {
  return formatPriceInCurrency(price, currencyCode);
}

export function formatChange(percent) {
  if (percent === null || percent === undefined || isNaN(percent)) {
    return '-';
  }
  const sign = percent >= 0 ? '+' : '';
  return `${sign}${percent.toFixed(2)}%`;
}

export function formatMarketCap(cap, currencyCode = null) {
  return formatVolumeInCurrency(cap, currencyCode);
}

export function formatNumber(num) {
  if (num === null || num === undefined || isNaN(num)) {
    return '-';
  }
  return num.toLocaleString('en-US');
}

export const GENERIC_TOKEN_ICON = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'><circle cx='16' cy='16' r='15' fill='%23262b3e' stroke='%233861fb' stroke-width='2'/><text x='16' y='21' font-size='14' font-weight='bold' text-anchor='middle' fill='%23f8fafc'>$</text></svg>";

export function getCoinLogoUrl(coin) {
  if (!coin) return GENERIC_TOKEN_ICON;
  if (typeof coin === 'string') return coin;
  if (coin.image) return coin.image;
  return GENERIC_TOKEN_ICON;
}

export function formatQuantity(num) {
  if (num === null || num === undefined || isNaN(num)) return '0';
  const val = Number(num);
  if (val === 0) return '0';
  if (Math.abs(val) < 0.0001) {
    return val.toFixed(8).replace(/\.?0+$/, '');
  }
  return val.toLocaleString('en-US', { maximumFractionDigits: 8 });
}

// Aliases for cross-module compatibility
export const formatCurrency = formatPrice;
export const formatCompactNumber = formatMarketCap;
export const formatPercentage = formatChange;
