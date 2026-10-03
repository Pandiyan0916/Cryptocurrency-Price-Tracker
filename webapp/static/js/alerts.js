/**
 * alerts.js - Custom Price Target Alerts & Browser Notification Manager for CoinPulse
 */

const ALERTS_KEY = 'coinpulse_price_alerts';

export function getPriceAlerts() {
  try {
    return JSON.parse(localStorage.getItem(ALERTS_KEY) || '[]');
  } catch (e) {
    return [];
  }
}

export function savePriceAlerts(alerts) {
  try {
    localStorage.setItem(ALERTS_KEY, JSON.stringify(alerts));
  } catch (e) {
    console.error('Error saving alerts:', e);
  }
}

export function addPriceAlert(coinId, coinSymbol, coinName, targetPrice, condition = 'above') {
  const alerts = getPriceAlerts();
  const newAlert = {
    id: 'alert_' + Date.now(),
    coinId: coinId.toLowerCase(),
    symbol: coinSymbol.toUpperCase(),
    name: coinName,
    targetPrice: parseFloat(targetPrice),
    condition: condition, // 'above' or 'below'
    createdAt: new Date().toISOString(),
    active: true
  };
  alerts.push(newAlert);
  savePriceAlerts(alerts);
  requestNotificationPermission();
  showToastNotification(`Price alert set for ${coinName} at $${targetPrice} (${condition})`, 'success');
  return newAlert;
}

export function removePriceAlert(alertId) {
  let alerts = getPriceAlerts();
  alerts = alerts.filter(a => a.id !== alertId);
  savePriceAlerts(alerts);
  showToastNotification('Alert removed', 'info');
}

export function checkPriceAlerts(marketCoins) {
  const alerts = getPriceAlerts();
  if (!alerts.length || !marketCoins || !marketCoins.length) return;

  const coinMap = {};
  marketCoins.forEach(c => {
    coinMap[c.id.toLowerCase()] = c;
    coinMap[c.symbol.toLowerCase()] = c;
  });

  let alertsTriggered = 0;
  const updatedAlerts = alerts.map(alert => {
    if (!alert.active) return alert;
    const coin = coinMap[alert.coinId];
    if (!coin || !coin.current_price) return alert;

    const currentPrice = coin.current_price;
    let triggered = false;

    if (alert.condition === 'above' && currentPrice >= alert.targetPrice) {
      triggered = true;
    } else if (alert.condition === 'below' && currentPrice <= alert.targetPrice) {
      triggered = true;
    }

    if (triggered) {
      alertsTriggered++;
      triggerAlertNotification(alert, currentPrice);
      return { ...alert, active: false, triggeredAt: new Date().toISOString() };
    }

    return alert;
  });

  if (alertsTriggered > 0) {
    savePriceAlerts(updatedAlerts);
  }
}

function triggerAlertNotification(alert, currentPrice) {
  const title = `🚨 Price Alert: ${alert.name} (${alert.symbol})`;
  const msg = `${alert.name} has reached $${currentPrice.toLocaleString()} (Target: $${alert.targetPrice})`;

  showToastNotification(msg, 'warning');

  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, {
      body: msg,
      icon: 'https://assets.coingecko.com/coins/images/1/large/bitcoin.png'
    });
  }
}

export function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}

export function injectAlertModal() {
  if (document.getElementById('price-alert-modal')) return;

  const modalHTML = `
    <div class="modal-backdrop hidden" id="price-alert-modal" aria-hidden="true">
      <div class="modal-box alert-modal-box">
        <div class="modal-header">
          <h3 class="modal-title"><i class="fas fa-bell text-warning"></i> Set Price Alert</h3>
          <button class="modal-close" id="close-alert-modal">&times;</button>
        </div>
        <form id="price-alert-form" class="margin-top-md">
          <input type="hidden" id="alert-coin-id">
          <input type="hidden" id="alert-coin-symbol">
          
          <div class="form-group">
            <label class="form-label">Coin Name</label>
            <input type="text" id="alert-coin-name" class="form-input" readonly>
          </div>

          <div class="form-group">
            <label class="form-label">Target Price (USD)</label>
            <div class="input-icon-group">
              <i class="fas fa-dollar-sign input-icon"></i>
              <input type="number" step="any" id="alert-target-price" class="form-input" placeholder="e.g. 95000" required>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Alert Trigger Condition</label>
            <select id="alert-condition" class="form-select">
              <option value="above">Price Rises Above Target (>=)</option>
              <option value="below">Price Drops Below Target (<=)</option>
            </select>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-outline" id="btn-cancel-alert">Cancel</button>
            <button type="submit" class="btn btn-primary"><i class="fas fa-check"></i> Set Alert</button>
          </div>
        </form>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modalHTML);

  const modal = document.getElementById('price-alert-modal');
  const closeBtn = document.getElementById('close-alert-modal');
  const cancelBtn = document.getElementById('btn-cancel-alert');
  const form = document.getElementById('price-alert-form');

  if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
  if (cancelBtn) cancelBtn.addEventListener('click', () => modal.classList.add('hidden'));
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.add('hidden');
    });
  }

  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const id = document.getElementById('alert-coin-id').value;
      const symbol = document.getElementById('alert-coin-symbol').value;
      const name = document.getElementById('alert-coin-name').value;
      const price = document.getElementById('alert-target-price').value;
      const condition = document.getElementById('alert-condition').value;

      addPriceAlert(id, symbol, name, price, condition);
      modal.classList.add('hidden');
    });
  }
}

export function openAlertModal(coinId, coinSymbol, coinName, currentPrice = '') {
  injectAlertModal();
  const modal = document.getElementById('price-alert-modal');
  document.getElementById('alert-coin-id').value = coinId;
  document.getElementById('alert-coin-symbol').value = coinSymbol;
  document.getElementById('alert-coin-name').value = coinName;
  document.getElementById('alert-target-price').value = currentPrice ? (parseFloat(currentPrice) * 1.05).toFixed(2) : '';
  modal.classList.remove('hidden');
}

function showToastNotification(msg, type = 'info') {
  let toast = document.getElementById('toast-notification');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-notification';
    toast.className = 'toast-notification';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `toast-notification toast-${type} show`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3500);
}

// Auto inject alert modal on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectAlertModal);
} else {
  injectAlertModal();
}
