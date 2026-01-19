import time
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dhanhq import dhanhq

# ===============================
# CONFIG / CACHE
# ===============================

CACHE = {
    "snapshot": {
        "data": None,
        "time": 0
    }
}

# ===============================
# STOCK LISTS
# ===============================

from fo_stocks import FO_STOCKS   # FULL F&O LIST

STOCKS = FO_STOCKS               # Market Pulse = All F&O stocks

INDEX_STOCKS = {
    "RELIANCE": 2885,
    "HDFCBANK": 1333,
    "ICICIBANK": 4963,
    "TCS": 11536,
    "INFY": 1594
}

NIFTY_WEIGHTS = {
    "RELIANCE": 10.8,
    "HDFCBANK": 8.9,
    "ICICIBANK": 7.6,
    "TCS": 3.9,
    "INFY": 3.7
}

# ===============================
# APP + DHAN SETUP
# ===============================

app = FastAPI()

CLIENT_ID = os.getenv("CLIENT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

# ===============================
# ROOT DASHBOARD (UI)
# ===============================

@app.get("/", response_class=HTMLResponse)
def dashboard():
    html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>Trade Dashboard</title>
<meta http-equiv="refresh" content="10">
<style>
body { background:#0b1220; color:#e5e7eb; font-family:Arial }
.container { width:92%; margin:auto; }
h1 { text-align:center; margin:20px 0; }
.grid { display:grid; grid-template-columns: 1fr 1fr; gap:20px; }
.card { background:#111827; border-radius:14px; padding:16px; }
table { width:100%; border-collapse:collapse }
th, td { padding:10px; border-bottom:1px solid #1f2937; text-align:center }
th { background:#0f172a }
.badge { padding:4px 10px; border-radius:999px; font-weight:600 }
.green { background:#064e3b; color:#34d399 }
.red { background:#3f1d1d; color:#f87171 }
</style>
</head>

<body>
<div class="container">
<h1>🔥 Trade Dashboard</h1>

<div class="grid">
  <div class="card">
    <h3>Market Pulse</h3>
    <div id="mp"></div>
  </div>
  <div class="card">
    <h3>Index Mover</h3>
    <div id="im"></div>
  </div>
</div>

<div class="card" style="margin-top:20px;">
  <h3>F&O Scanner (Top 10)</h3>
  <div id="fo"></div>
</div>
</div>

<script>
async function load(){
  const r = await fetch('/snapshot');
  const d = await r.json();

  let mp = `<table><tr><th>Symbol</th><th>Price</th><th>Volume</th><th>Status</th></tr>`;
  d.market_pulse.forEach(x=>{
    mp += `<tr><td>${x.symbol}</td><td>${x.last_price}</td><td>${x.volume}</td>
           <td><span class="badge green">ACTIVE</span></td></tr>`;
  });
  mp += `</table>`;
  document.getElementById('mp').innerHTML = mp;

  let im = `<table><tr><th>Symbol</th><th>Change %</th><th>Impact</th></tr>`;
  d.index_mover.forEach(x=>{
    const cls = x.impact_score >= 0 ? 'green':'red';
    im += `<tr><td>${x.symbol}</td><td>${x["change_%"]}</td>
           <td><span class="badge ${cls}">${x.impact_score}</span></td></tr>`;
  });
  im += `</table>`;
  document.getElementById('im').innerHTML = im;

  let fo = `<table><tr><th>Symbol</th><th>Price</th><th>Volume</th><th>Strength</th></tr>`;
  d.fo_scanner.forEach(x=>{
    let label = x.score == 3
      ? '<span class="badge green">STRONG</span>'
      : '<span class="badge">MEDIUM</span>';

    fo += `<tr><td>${x.symbol}</td><td>${x.last_price}</td><td>${x.volume}</td><td>${label}</td></tr>`;
  });
  fo += `</table>`;
  document.getElementById('fo').innerHTML = fo;
}
load();
</script>
</body>
</html>
"""
    return HTMLResponse(content=html)

# ===============================
# LOGIC FUNCTIONS
# ===============================

def scan_market_pulse():
    results = []

    for symbol, sid in STOCKS.items():
        try:
            quote = dhan.quote_data(securities={"NSE_EQ": [sid]})
            data = quote.get("data", {}).get("data", {}).get("NSE_EQ", {}).get(str(sid))
            if not data:
                continue

            ohlc = data.get("ohlc", {})
            last_price = data.get("last_price", 0)
            open_price = ohlc.get("open", 0)
            high_price = ohlc.get("high", 0)
            volume = data.get("volume", 0)
            avg_price = data.get("average_price", 1)

            price_strength = last_price > open_price
            breakout_zone = last_price > (high_price * 0.8)
            volume_spike = volume > (avg_price * 1000)

            score = sum([price_strength, breakout_zone, volume_spike])

            if score >= 2:
                results.append({
                    "symbol": symbol,
                    "last_price": last_price,
                    "volume": volume
                })

        except Exception:
            pass

    return results

def scan_fo_market_pulse():
    results = []

    for symbol, sid in FO_STOCKS.items():
        try:
            quote = dhan.quote_data(securities={"NSE_EQ": [sid]})
            data = quote.get("data", {}).get("data", {}).get("NSE_EQ", {}).get(str(sid))
            if not data:
                continue

            ohlc = data.get("ohlc", {})
            last_price = data.get("last_price", 0)
            open_price = ohlc.get("open", 0)
            high_price = ohlc.get("high", 0)
            volume = data.get("volume", 0)
            avg_price = data.get("average_price", 1)

            score = sum([
                last_price > open_price,
                last_price > (high_price * 0.8),
                volume > (avg_price * 1000)
            ])

            if score >= 2:
                results.append({
                    "symbol": symbol,
                    "last_price": last_price,
                    "volume": volume,
                    "score": score
                })

        except Exception:
            pass

    return sorted(results, key=lambda x: x["volume"], reverse=True)[:10]

def index_mover():
    movers = []

    for symbol, sid in INDEX_STOCKS.items():
        try:
            quote = dhan.quote_data(securities={"NSE_EQ": [sid]})
            data = quote.get("data", {}).get("data", {}).get("NSE_EQ", {}).get(str(sid))
            if not data:
                continue

            ohlc = data.get("ohlc", {})
            open_price = ohlc.get("open", 0)
            last_price = data.get("last_price", 0)
            if open_price == 0:
                continue

            pct = ((last_price - open_price) / open_price) * 100
            impact = pct * NIFTY_WEIGHTS.get(symbol, 0)

            movers.append({
                "symbol": symbol,
                "change_%": round(pct, 2),
                "impact_score": round(impact, 2)
            })

        except Exception:
            pass

    return sorted(movers, key=lambda x: abs(x["impact_score"]), reverse=True)

# ===============================
# SNAPSHOT API (UI USES THIS)
# ===============================

@app.get("/snapshot")
def snapshot():
    now = time.time()

    if CACHE["snapshot"]["data"] and now - CACHE["snapshot"]["time"] < 10:
        return CACHE["snapshot"]["data"]

    data = {
        "market_pulse": scan_market_pulse(),
        "index_mover": index_mover(),
        "fo_scanner": scan_fo_market_pulse()
    }

    CACHE["snapshot"]["data"] = data
    CACHE["snapshot"]["time"] = now

    return data
