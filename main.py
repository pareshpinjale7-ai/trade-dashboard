@app.get("/scan-market-pulse")
def scan_market_pulse():

    results = []

    for name, sid in STOCKS.items():
        try:
            quote = dhan.quote_data(
                securities={
                    "NSE_EQ": [sid]
                }
            )

            # SAFE extraction
            nse_data = quote.get("data", {}).get("data", {}).get("NSE_EQ", {})
            if str(sid) not in nse_data:
                continue

            data = nse_data[str(sid)]

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
                    "symbol": name,
                    "security_id": sid,
                    "last_price": last_price,
                    "volume": volume,
                    "market_pulse": True
                })

        except Exception as e:
            # NEVER crash server
            print(f"Error in {name} ({sid}): {e}")

    return results
