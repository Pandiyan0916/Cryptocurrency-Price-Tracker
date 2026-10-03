/**
 * api.js - Robust client API fetch wrapper with timeout, status validation, and error handling.
 */

const DEFAULT_TIMEOUT_MS = 6000;

export async function apiFetch(endpoint, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const config = {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        ...(options.headers || {}),
      },
    };

    const res = await fetch(endpoint, config);
    clearTimeout(timer);

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) detail = errJson.detail;
      } catch (e) {
        // use status text if JSON parse fails
      }
      throw new Error(`API error (${res.status}): ${detail}`);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') {
      throw new Error(`Request to ${endpoint} timed out after ${timeoutMs / 1000}s`);
    }
    throw err;
  }
}

export async function fetchHealth() {
  return await apiFetch('/api/health');
}

export async function fetchGlobalStats() {
  return await apiFetch('/api/global');
}

export async function fetchMarkets(page = 1, perPage = 50, order = 'market_cap_desc', query = '', ids = '', refresh = false) {
  let url = `/api/markets?page=${page}&per_page=${perPage}&order=${order}`;
  if (query) url += `&q=${encodeURIComponent(query)}`;
  if (ids) url += `&ids=${encodeURIComponent(ids)}`;
  if (refresh) url += `&refresh=true`;
  return await apiFetch(url);
}

export async function fetchCoinDetail(coinId) {
  return await apiFetch(`/api/coin/${encodeURIComponent(coinId)}`);
}

export async function fetchCoinChart(coinId, days = 7) {
  return await apiFetch(`/api/coin/${encodeURIComponent(coinId)}/chart?days=${days}`);
}

export async function fetchTrending() {
  return await apiFetch('/api/trending');
}

export async function searchCoins(query) {
  return await apiFetch(`/api/search?q=${encodeURIComponent(query)}`);
}

export async function fetchExchanges(page = 1, perPage = 50) {
  return await apiFetch(`/api/exchanges?page=${page}&per_page=${perPage}`);
}

export async function fetchExchangeDetail(exchangeId) {
  return await apiFetch(`/api/exchange/${encodeURIComponent(exchangeId)}`);
}

export async function fetchCategories() {
  return await apiFetch('/api/categories');
}
