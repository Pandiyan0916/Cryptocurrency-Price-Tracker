# CoinMarketCap DOM Notes

**Inspected:** 2026-10-02  
**Real Fixture Captured:** 2026-10-02 12:28 UTC (via `tools/capture_fixture.py`, 12 real <tr> rows)  
**URL:** https://coinmarketcap.com/  
**Method:** Static HTML fetch + knowledge of Next.js/React rendering

---

## Page Architecture

CoinMarketCap is a **Next.js** application. The primary table is **JavaScript-rendered** — a plain HTTP `GET` returns a skeleton with minimal coin data. Selenium with ChromeDriver is required to get the live-rendered table.

---

## Cookie / Consent Banner

- ID: `#onetrust-banner-sdk`  
- Dismiss button: `button#onetrust-accept-btn-handler`  
- The banner is hidden in the raw server response via a CSS rule  
  (`bottom: -1000px !important`) injected by a `<script>` tag.  
  After JS runs, it may appear in the viewport.  
- Additional selectors observed: `button[id*='accept']`, `button[class*='accept']`

---

## Table Structure

```
<table>
  <thead>
    <tr>
      <th>...</th>   ← columns described below
    </tr>
  </thead>
  <tbody>
    <tr>              ← one row per coin
      <td>...</td>
      ...
    </tr>
  </tbody>
</table>
```

**CSS selector to reach rows:**  
```css
table tbody tr
```
This is a stable semantic selector; CoinMarketCap's generated class names are hashed and change between deployments.

---

## Column Positions (0-indexed, per `<td>`)

| Index | Content | Notes |
|-------|---------|-------|
| 0 | **Rank** | Plain integer text |
| 1 | Watchlist / star | Icon only; ignored |
| 2 | **Name + Symbol** | `<a href="/currencies/slug/">Name<span>SYMBOL</span></a>` |
| 3 | **Price (USD)** | `$67,500.12` or `$0.00002543` for tiny coins |
| 4 | **1h change %** | `+0.12%` or `-0.05%`; skipped |
| 5 | **24h change %** | `+3.42%` or `-1.20%` — *this is the column we use* |
| 6 | **7d change %** | Similar format; skipped |
| 7 | **Market Cap** | `$1,330,000,000,000` or `$1.33T` abbreviated |
| 8 | Volume (24h) | Skipped |
| 9 | Circulating Supply | Skipped |

---

## Cell Structure Detail

### Rank (col 0)
```html
<td>1</td>
```
Plain text node; `get_text(strip=True)` returns `"1"`.

### Name + Symbol (col 2)
```html
<td>
  <a href="/currencies/bitcoin/">
    Bitcoin
    <span>BTC</span>
  </a>
</td>
```
`stripped_strings` on the anchor yields `['Bitcoin', 'BTC']`.

### Price (col 3)
```html
<td>$67,500.12</td>
```
Very small coins may render with subscript zero notation:  
`$0.0₅1234` = `0.000001234` (5 zeros after decimal before significant digits).

### 24h Change (col 5)
```html
<td><span style="color: var(--c-color-positive)">+3.42%</span></td>
<!-- OR -->
<td><span style="color: var(--c-color-negative)">-1.20%</span></td>
```
Sign is indicated both by the `+`/`-` prefix in the text **and** by the CSS custom property:
- Positive: `--c-color-positive` (#16C784 green)
- Negative: `--c-color-negative` (#EA3943 red)

The scraper checks the text sign first; the CSS class is used as a fallback for cases where only the absolute value appears.

### Market Cap (col 7)
```html
<td>$1,330,000,000,000</td>
<!-- Or abbreviated -->
<td>$1.33T</td>
```

---

## Lazy-loading Behaviour

The initial page render loads the first ~100 rows. Additional rows beyond ~100 require scrolling. For the default limit of 10 (or any limit ≤ 100), no scrolling is necessary, but the scraper scrolls gently as a safety measure.

---

## Automation Detection

CoinMarketCap uses AWS WAF with a challenge script. The scraper uses:
- `--disable-blink-features=AutomationControlled`
- `navigator.webdriver` set to `undefined`
- Polite delays (`SCRAPE_DELAY = 2.0s`)

If automation is blocked, the scraper reports a clear error and exits without saving fabricated data.

---

## Sample First Row HTML (representative structure)

```html
<tr>
  <td>1</td>
  <td><!-- star icon --></td>
  <td>
    <a href="/currencies/bitcoin/">
      Bitcoin
      <span>BTC</span>
    </a>
  </td>
  <td>$67,500.12</td>
  <td><span style="color:var(--c-color-positive)">+0.12%</span></td>
  <td><span style="color:var(--c-color-positive)">+3.42%</span></td>
  <td><span style="color:var(--c-color-positive)">+5.10%</span></td>
  <td>$1,330,000,000,000</td>
  <td>$25,000,000,000</td>
  <td>19,700,000 BTC</td>
</tr>
```

The complete 12-row fixture is in `tests/fixtures/sample_table.html`.
