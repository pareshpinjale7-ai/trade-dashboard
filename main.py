import time
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from dhanhq import dhanhq
from fo_stocks import FO_STOCKS

# =====================
# BASIC SETUP
# =====================

app = FastAPI()

CLIENT_ID = os.getenv("CLIENT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)

CACHE = {"data": None, "time": 0}

# =====================
# INDEX DATA
# =====================

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

# =====================
# DATA FUNCTIONS
# =====================

def get_quote(sid):
    q = dhan.quote_data(securities={"NSE_EQ": [sid]})
    return q.get("data", {}).get("data", {}).get("NSE_EQ", {}).get(str(sid))


def market_pulse_data():
    data = []

    for symbol, sid in FO_STOCKS.items():
        try:
            d = get_quote(sid)
            if not d:
                continue

            last = d["last_price"]
            vol = d["volume"]
            openp = d["ohlc"]["open"]

            status = "ACTIVE" if last > openp else "WATCH"

            data.append({
                "symbol": symbol,
                "last_price": last,
                "volume": vol,
                "status": status
            })

        except:
            pass

    return data[:15]   # LIMIT for UI


def index_mover_data():
    movers = []

    for symbol, sid in INDEX_STOCKS.items():
        try:
            d = get_quote(sid)
            if not d:
                continue

            o = d["ohlc"]["open"]
            l = d["last_price"]

            if o == 0:
                continue

            chg = ((l - o) / o) * 100
            impact = chg * NIFTY_WEIGHTS[symbol]

            movers.append({
                "symbol": symbol,
                "change_%": round(chg, 2),
                "impact_score": round(impact, 2)
            })

        except:
            pass

    return movers


def fo_scanner_data():
    results = []

    for symbol, sid in FO_STOCKS.items():
        try:
            d = get_quote(sid)
            if not d:
                continue

            ohlc = d["ohlc"]
            score = sum([
                d["last_price"] > ohlc["open"],
                d["last_price"] > ohlc["high"] * 0.8,
                d["volume"] > d["average_price"] * 500
            ])

            results.append({
                "symbol": symbol,
                "last_price": d["last_price"],
                "volume": d["volume"],
                "score": score
            })

        except:
            pass

    results.sort(key=lambda x: x["volume"], reverse=True)
    return results[:10]

# =====================
# SNAPSHOT API
# =====================

@app.get("/snapshot")
def snapshot():
    now = time.time()

    if CACHE["data"] and now - CACHE["time"] < 10:
        return CACHE["data"]

    data = {
        "market_pulse": market_pulse_data(),
        "index_mover": index_mover_data(),
        "fo_scanner": fo_scanner_data()
    }

    CACHE["data"] = data
    CACHE["time"] = now

    return data

# =====================
# DASHBOARD UI
# =====================

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Trade Dashboard</title>
<meta http-equiv="refresh" content="10">
<style>
body{background:#0b1220;color:white;font-family:Arial}
.container{width:92%;margin:auto}
.card{background:#111827;padding:16px;border-radius:14px;margin-bottom:20px}
table{width:100%;border-collapse:collapse}
th,td{padding:10px;border-bottom:1px solid #1f2937;text-align:center}
th{background:#0f172a}
.badge{padding:4px 10px;border-radius:999px}
.green{background:#064e3b;color:#34d399}
.red{background:#3f1d1d;color:#f87171}
</style>
</head>
<body>
<div class="container">
<h1>🔥 Trade Dashboard</h1>

<div class="card">
<h3>Market Pulse</h3>
<div id="mp"></div>
</div>

<div class="card">
<h3>Index Mover</h3>
<div id="im"></div>
</div>

<div class="card">
<h3>F&O Scanner (Top 10)</h3>
<div id="fo"></div>
</div>
</div>

<script>
async function load(){
 const r=await fetch('/snapshot'); const d=await r.json();

 let mp='<table><tr><th>Symbol</th><th>Price</th><th>Volume</th><th>Status</th></tr>';
 d.market_pulse.forEach(x=>{
   mp+=`<tr><td>${x.symbol}</td><td>${x.last_price}</td><td>${x.volume}</td>
   <td><span class="badge ${x.status=='ACTIVE'?'green':'red'}">${x.status}</span></td></tr>`;
 });
 mp+='</table>'; document.getElementById('mp').innerHTML=mp;

 let im='<table><tr><th>Symbol</th><th>%</th><th>Impact</th></tr>';
 d.index_mover.forEach(x=>{
   im+=`<tr><td>${x.symbol}</td><td>${x["change_%"]}</td>
   <td>${x.impact_score}</td></tr>`;
 });
 im+='</table>'; document.getElementById('im').innerHTML=im;

 let fo='<table><tr><th>Symbol</th><th>Price</th><th>Volume</th><th>Strength</th></tr>';
 d.fo_scanner.forEach(x=>{
   fo+=`<tr><td>${x.symbol}</td><td>${x.last_price}</td><td>${x.volume}</td>
   <td>${x.score>=2?'STRONG':'MEDIUM'}</td></tr>`;
 });
 fo+='</table>'; document.getElementById('fo').innerHTML=fo;
}
load();
</script>
</body>
</html>
"""
