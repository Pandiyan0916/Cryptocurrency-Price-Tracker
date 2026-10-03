/**
 * search.js - Global Search Modal & Dropdown with Keyboard Navigation.
 */

import { searchCoins } from './api.js';

export function initGlobalSearch() {
  const searchInput = document.getElementById('global-search-input');
  const searchResults = document.getElementById('global-search-results');
  if (!searchInput || !searchResults) return;

  let debounceTimer = null;
  let activeIndex = -1;

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    clearTimeout(debounceTimer);
    if (!query) {
      searchResults.style.display = 'none';
      searchResults.innerHTML = '';
      activeIndex = -1;
      return;
    }

    debounceTimer = setTimeout(() => {
      performSearch(query);
    }, 250);
  });

  searchInput.addEventListener('keydown', (e) => {
    const items = searchResults.querySelectorAll('.search-item');
    if (!items.length || searchResults.style.display === 'none') return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIndex >= 0 && items[activeIndex]) {
        items[activeIndex].click();
      } else if (items[0]) {
        items[0].click();
      }
    } else if (e.key === 'Escape') {
      searchResults.style.display = 'none';
      activeIndex = -1;
    }
  });

  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
      searchResults.style.display = 'none';
      activeIndex = -1;
    }
  });

  async function performSearch(query) {
    try {
      searchResults.style.display = 'block';
      searchResults.innerHTML = `<div class="search-loading"><i class="fas fa-spinner fa-spin"></i> Searching market...</div>`;

      const data = await searchCoins(query);
      const coins = data.coins || [];
      const exchanges = data.exchanges || [];
      const categories = data.categories || [];

      if (!coins.length && !exchanges.length && !categories.length) {
        searchResults.innerHTML = `<div class="search-empty">No assets, exchanges, or categories found for "${escapeHtml(query)}"</div>`;
        return;
      }

      let html = '';

      if (coins.length) {
        html += `<div class="search-section-title">Cryptocurrencies</div>`;
        coins.forEach(c => {
          const thumb = c.thumb ? `<img src="${c.thumb}" alt="${c.name}" class="search-thumb">` : '';
          const rank = c.market_cap_rank ? `<span class="badge badge-rank">#${c.market_cap_rank}</span>` : '';
          html += `
            <a href="coin.html?id=${c.id}" class="search-item">
              ${thumb}
              <span class="search-item-name">${escapeHtml(c.name)}</span>
              <span class="search-item-symbol">${escapeHtml(c.symbol.toUpperCase())}</span>
              ${rank}
            </a>
          `;
        });
      }

      if (exchanges.length) {
        html += `<div class="search-section-title">Exchanges</div>`;
        exchanges.forEach(ex => {
          const thumb = ex.thumb ? `<img src="${ex.thumb}" alt="${ex.name}" class="search-thumb">` : '';
          html += `
            <a href="exchange.html?id=${ex.id}" class="search-item">
              ${thumb}
              <span class="search-item-name">${escapeHtml(ex.name)}</span>
              <span class="badge badge-tag">Exchange</span>
            </a>
          `;
        });
      }

      if (categories.length) {
        html += `<div class="search-section-title">Categories</div>`;
        categories.forEach(cat => {
          html += `
            <a href="categories.html?id=${cat.id}" class="search-item">
              <i class="fas fa-folder search-thumb-icon"></i>
              <span class="search-item-name">${escapeHtml(cat.name)}</span>
              <span class="badge badge-tag">Category</span>
            </a>
          `;
        });
      }

      searchResults.innerHTML = html;
      activeIndex = -1;
    } catch (err) {
      searchResults.innerHTML = `<div class="search-error">Failed to complete search. ${escapeHtml(err.message)}</div>`;
    }
  }

  function updateActiveItem(items) {
    items.forEach((item, idx) => {
      if (idx === activeIndex) {
        item.classList.add('active');
        item.scrollIntoView({ block: 'nearest' });
      } else {
        item.classList.remove('active');
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
