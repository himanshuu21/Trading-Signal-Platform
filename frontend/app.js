// ── Config ────────────────────────────────────────────────
const API_BASE        = "http://localhost:8000";
const REFRESH_MS      = 5 * 60 * 1000;   // 5 minutes
let   refreshTimer    = null;

// ── Helpers ───────────────────────────────────────────────
const $  = id => document.getElementById(id);
const fmt=(n,d=2)=>{

    if(n===null || n===undefined || isNaN(n))
        return "--";

    return Number(n).toFixed(d);

}

function setDot(state) {
  const dot = $("status-dot");
  dot.className = "dot " + state;
}

function updateTimestamp() {
  const now = new Date();
  $("last-updated").textContent =
    "Updated: " + now.toLocaleTimeString("en-IN");
}

function getStock()   { return $("stock-select").value; }
function getCapital() { return parseInt($("capital-input").value) || 100000; }

// ── Signal Banner ─────────────────────────────────────────
function updateBanner(signal, price, ml) {
  const banner = $("signal-banner");
  let icon = "⚪";
  let cls  = "neutral";
  let mlText = "";

  if (signal === "BUY") {
    icon = "🟢"; cls = "buy";
    if (ml) {
      mlText = ` &nbsp;|&nbsp; 🤖 ML: ${ml.prediction} — ${ml.confidence}% confidence`;
    }
  } else if (signal === "SELL") {
    icon = "🔴"; cls = "sell";
  }

  banner.className  = "signal-banner " + cls;
  banner.innerHTML  = `${icon} ${signal} &nbsp;·&nbsp; ₹${fmt(price)} ${mlText}`;
}

// ── Metric Cards ──────────────────────────────────────────
function updateCards(data) {
  const ind = data.indicators;
  const sig = data.signal;
  const ml  = data.ml;

  $("card-price").textContent  = "₹" + fmt(data.price);
  $("card-rsi").textContent    = fmt(ind.rsi, 1);
  $("card-adx").textContent    = fmt(ind.adx, 1);
  $("card-vol").textContent    = fmt(ind.volume_ratio, 2) + "x";

  // Signal card with colour
  const sigEl = $("card-signal");
  sigEl.textContent = sig;
  sigEl.className   = "card-value " +
    (sig === "BUY" ? "green" : sig === "SELL" ? "red" : "");

  // ML card
  const mlEl = $("card-ml");
  if (ml) {
    mlEl.textContent  = ml.confidence + "%";
    mlEl.className    = "card-value " + (ml.take_trade ? "green" : "yellow");
  } else {
    mlEl.textContent  = "N/A";
    mlEl.className    = "card-value";
  }
}

// ── Indicator Values ───────────────────────────────────────
function updateIndicators(ind) {
  $("i-ema20").textContent       = "₹" + fmt(ind.ema_20);
  $("i-ema50").textContent       = "₹" + fmt(ind.ema_50);
  $("i-sma20").textContent       = "₹" + fmt(ind.sma_20);
  $("i-sma50").textContent       = "₹" + fmt(ind.sma_50);
  $("i-vwap").textContent        = "₹" + fmt(ind.vwap);
  $("i-rsi").textContent         = fmt(ind.rsi, 1);
  $("i-macd").textContent        = fmt(ind.macd, 4);
  $("i-macd-signal").textContent = fmt(ind.macd_signal, 4);
  $("i-macd-hist").textContent   = fmt(ind.macd_hist, 4);
  $("i-atr").textContent         = "₹" + fmt(ind.atr);
  $("i-adx").textContent         = fmt(ind.adx, 1);
  $("i-bb-upper").textContent    = "₹" + fmt(ind.bb_upper);
  $("i-bb-lower").textContent    = "₹" + fmt(ind.bb_lower);
  $("i-vol-ratio").textContent   = fmt(ind.volume_ratio, 2) + "x";
}

// ── Recent Signals Table ───────────────────────────────────
function updateSignalsTable(signals) {
  const tbody = $("signals-body");

  if (!signals || signals.length === 0) {
    tbody.innerHTML =
      `<tr><td colspan="7" class="loading">No signals found</td></tr>`;
    return;
  }

  tbody.innerHTML = signals.map(s => {
    const cls   = s.signal === "BUY" ? "row-buy" : "row-sell";
    const badge = s.signal === "BUY"
      ? `<span class="badge buy">BUY</span>`
      : `<span class="badge sell">SELL</span>`;

    // Format timestamp — show only time portion
    const time = new Date(s.time).toLocaleString("en-IN", {
      month:  "short", day: "numeric",
      hour:   "2-digit", minute: "2-digit"
    });

    return `
      <tr class="${cls}">
        <td>${time}</td>
        <td>₹${fmt(s.price)}</td>
        <td>${fmt(s.rsi, 1)}</td>
        <td>${fmt(s.macd, 4)}</td>
        <td>${fmt(s.adx, 1)}</td>
        <td>${fmt(s.volume_ratio, 2)}x</td>
        <td>${badge}</td>
      </tr>
    `;
  }).join("");
}

// ── Backtest Cards ─────────────────────────────────────────
function updateBacktest(data, capital) {
  $("backtest-subtitle").textContent =
    `(Last 30 Days · ₹${capital.toLocaleString("en-IN")} Capital)`;

  if (!data.metrics) {
    ["bt-trades","bt-winrate","bt-return","bt-pnl",
     "bt-drawdown","bt-sharpe"].forEach(id => $(id).textContent = "N/A");
    return;
  }

  const m = data.metrics;

  $("bt-trades").textContent   = m["Total Trades"];
  $("bt-winrate").textContent  = fmt(m["Win Rate (%)"], 1) + "%";

  const retEl = $("bt-return");
  retEl.textContent = fmt(m["Total Return (%)"], 2) + "%";
  retEl.className   = "card-value " +
    (m["Total Return (%)"] >= 0 ? "green" : "red");

  const pnlEl = $("bt-pnl");
  pnlEl.textContent = "₹" + Number(m["Total PnL (₹)"]).toLocaleString("en-IN");
  pnlEl.className   = "card-value " +
    (m["Total PnL (₹)"] >= 0 ? "green" : "red");

  const ddEl = $("bt-drawdown");
  ddEl.textContent = fmt(m["Max Drawdown (%)"], 2) + "%";
  ddEl.className   = "card-value red";

  $("bt-sharpe").textContent = fmt(m["Sharpe Ratio"], 2);

  // Trade Log
  const trades = data.trades || [];
  const tbody  = $("trades-body");

  if (trades.length === 0) {
    tbody.innerHTML =
      `<tr><td colspan="7" class="loading">No trades found</td></tr>`;
    return;
  }

  tbody.innerHTML = trades.map(t => {
    const cls   = t.result === "WIN" ? "row-win" : "row-loss";
    const badge = t.result === "WIN"
      ? `<span class="badge win">WIN</span>`
      : `<span class="badge loss">LOSS</span>`;

    const entryTime = new Date(t.entry_time).toLocaleString("en-IN", {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit"
    });
    const exitTime = new Date(t.exit_time).toLocaleString("en-IN", {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit"
    });

    return `
      <tr class="${cls}">
        <td>${entryTime}</td>
        <td>${exitTime}</td>
        <td>₹${fmt(t.entry_price)}</td>
        <td>₹${fmt(t.exit_price)}</td>
        <td class="${t.pnl >= 0 ? 'green' : 'red'}" style="color:inherit">
          ${t.pnl >= 0 ? '+' : ''}₹${fmt(t.pnl)}
        </td>
        <td class="${t.pnl_pct >= 0 ? 'green' : 'red'}" style="color:inherit">
          ${t.pnl_pct >= 0 ? '+' : ''}${fmt(t.pnl_pct)}%
        </td>
        <td>${badge}</td>
      </tr>
    `;
  }).join("");
}

// ── Main Load Function ─────────────────────────────────────
async function loadAll() {
  const stock   = getStock();
  const capital = getCapital();

  setDot("gray");
  $("refresh-btn").innerHTML = `<span class="spinner"></span> Loading`;
  $("refresh-btn").disabled  = true;

  try {
    // 1. Fetch current signal
    const sigRes  = await fetch(`${API_BASE}/api/signal/${stock}`);
    const sigData = await sigRes.json();

    updateBanner(sigData.signal, sigData.price, sigData.ml);
    updateCards(sigData);
    updateIndicators(sigData.indicators);

    // 2. Fetch recent signals table
    const tblRes  = await fetch(`${API_BASE}/api/signals/${stock}`);
    const tblData = await tblRes.json();
    updateSignalsTable(tblData.signals);

    // 3. Fetch backtest
    const btRes  = await fetch(
      `${API_BASE}/api/backtest/${stock}?capital=${capital}`
    );
    const btData = await btRes.json();
    updateBacktest(btData, capital);
    // 4. Fetch chart data
    const chartRes = await fetch(`${API_BASE}/api/candles/${stock}`);
    const chartData = await chartRes.json();

    const labels = chartData.candles.map(c =>
        new Date(c.time).toLocaleString("en-IN",{
            month:"short",
            day:"numeric",
            hour:"2-digit",
            minute:"2-digit"
        })
    );

    const prices = chartData.candles.map(c => c.close);

    renderChart(labels, prices);

    setDot("green");
    updateTimestamp();

  } catch (err) {
    console.error("Load failed:", err);
    setDot("red");
    $("signal-banner").className = "signal-banner neutral";
    $("signal-banner").textContent =
      "⚠️ Failed to connect to API. Is the server running?";
  }

  $("refresh-btn").innerHTML = "🔄 Refresh";
  $("refresh-btn").disabled  = false;
}

// ── Auto Refresh ───────────────────────────────────────────
function setupAutoRefresh() {
  clearInterval(refreshTimer);
  if ($("auto-refresh").checked) {
    refreshTimer = setInterval(loadAll, REFRESH_MS);
  }
}

let chart;

function renderChart(labels, prices){

    const ctx = document.getElementById("priceChart");

    if(chart){

        chart.destroy();

    }

    chart = new Chart(ctx,{

        type:"line",

        data:{

            labels:labels,

            datasets:[{

                label:"Closing Price",

                data:prices,

                borderColor:"#3B82F6",

                borderWidth:3,

                pointRadius:0,

                tension:.35,

                fill:false

            }]

        },

        options:{

            responsive:true,

            maintainAspectRatio:false,

            plugins:{
                legend:{
                    display:false
                }
            },

            scales:{

                x:{
                    ticks:{
                        color:"#94A3B8"
                    },
                    grid:{
                        color:"#222"
                    }
                },

                y:{
                    ticks:{
                        color:"#94A3B8"
                    },
                    grid:{
                        color:"#222"
                    }
                }

            }

        }

    });

}

$("auto-refresh").addEventListener("change", setupAutoRefresh);
$("stock-select").addEventListener("change", loadAll);

// ── Init ───────────────────────────────────────────────────
loadAll();
setupAutoRefresh();
