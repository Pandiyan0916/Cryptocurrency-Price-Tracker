/**
 * currency.js - Currency Converter & Exchange Rate Manager for CoinPulse
 */

const CURRENCY_KEY = 'coinpulse_currency';

export const CURRENCIES = {
  usd: { code: 'usd', symbol: '$', rate: 1.0, label: 'USD ($)', decimals: 2 },
  eur: { code: 'eur', symbol: '€', rate: 0.92, label: 'EUR (€)', decimals: 2 },
  gbp: { code: 'gbp', symbol: '£', rate: 0.78, label: 'GBP (£)', decimals: 2 },
  inr: { code: 'inr', symbol: '₹', rate: 83.5, label: 'INR (₹)', decimals: 2 },
  btc: { code: 'btc', symbol: '₿', rate: 0.0000118, label: 'BTC (₿)', decimals: 6 },
};

export function getSelectedCurrency() {
  const saved = localStorage.getItem(CURRENCY_KEY);
  if (saved && CURRENCIES[saved.toLowerCase()]) {
    return saved.toLowerCase();
  }
  return 'usd';
}

export function setSelectedCurrency(currencyCode) {
  const code = currencyCode.toLowerCase();
  if (CURRENCIES[code]) {
    localStorage.setItem(CURRENCY_KEY, code);
    document.querySelectorAll('#global-currency-select, .currency-select').forEach(sel => {
      sel.value = code;
    });
    // Dispatch custom event to notify all components to re-render prices
    window.dispatchEvent(new CustomEvent('currencyChanged', { detail: { currency: code } }));
  }
}

export function formatPriceInCurrency(usdPrice, currencyCode = null) {
  if (usdPrice === null || usdPrice === undefined || isNaN(usdPrice)) return '-';
  const code = currencyCode ? currencyCode.toLowerCase() : getSelectedCurrency();
  const info = CURRENCIES[code] || CURRENCIES.usd;
  const converted = usdPrice * info.rate;

  if (code === 'btc') {
    return `${info.symbol}${converted.toFixed(6)}`;
  }

  if (converted >= 1) {
    return `${info.symbol}${converted.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  } else if (converted >= 0.0001) {
    return `${info.symbol}${converted.toFixed(4)}`;
  } else {
    return `${info.symbol}${converted.toFixed(6)}`;
  }
}

export function formatVolumeInCurrency(usdAmount, currencyCode = null) {
  if (usdAmount === null || usdAmount === undefined || isNaN(usdAmount)) return '-';
  const code = currencyCode ? currencyCode.toLowerCase() : getSelectedCurrency();
  const info = CURRENCIES[code] || CURRENCIES.usd;
  const converted = usdAmount * info.rate;

  if (converted >= 1e12) return `${info.symbol}${(converted / 1e12).toFixed(2)}T`;
  if (converted >= 1e9) return `${info.symbol}${(converted / 1e9).toFixed(2)}B`;
  if (converted >= 1e6) return `${info.symbol}${(converted / 1e6).toFixed(2)}M`;
  if (converted >= 1e3) return `${info.symbol}${(converted / 1e3).toFixed(2)}K`;
  return `${info.symbol}${converted.toFixed(2)}`;
}

let liveClockInterval = null;

export function initLiveClock() {
  const wrappers = document.querySelectorAll('.currency-selector-wrapper');
  wrappers.forEach(wrapper => {
    if (!wrapper.querySelector('.live-clock-badge')) {
      const clockHtml = `
        <div class="live-clock-badge" id="global-live-clock" title="Real-Time UTC Timestamp">
          <i class="fas fa-clock text-primary"></i>
          <span class="live-clock-text" id="live-clock-text">--:--:-- UTC</span>
        </div>
      `;
      wrapper.insertAdjacentHTML('afterbegin', clockHtml);
    }
  });

  function updateClock() {
    const now = new Date();
    const hrs = now.getUTCHours().toString().padStart(2, '0');
    const mins = now.getUTCMinutes().toString().padStart(2, '0');
    const secs = now.getUTCSeconds().toString().padStart(2, '0');
    const utcTimeStr = `${hrs}:${mins}:${secs} UTC`;
    const localTime = now.toLocaleTimeString();

    document.querySelectorAll('.live-clock-text, #live-clock-text').forEach(el => {
      el.textContent = utcTimeStr;
    });

    document.querySelectorAll('.live-clock-badge, #global-live-clock').forEach(el => {
      el.title = `UTC Time: ${utcTimeStr} | Local Time: ${localTime}`;
    });
  }

  updateClock();
  if (!liveClockInterval) {
    liveClockInterval = setInterval(updateClock, 1000);
  }
}

export function initCurrencySelector() {
  initLiveClock();
  const selects = document.querySelectorAll('#global-currency-select, .currency-select');
  const current = getSelectedCurrency();

  selects.forEach(select => {
    select.value = current;
    if (!select.dataset.currencyBound) {
      select.dataset.currencyBound = 'true';
      select.addEventListener('change', (e) => {
        setSelectedCurrency(e.target.value);
      });
    }
  });
}

// Auto init on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initCurrencySelector();
    initLiveClock();
  });
} else {
  initCurrencySelector();
  initLiveClock();
}
