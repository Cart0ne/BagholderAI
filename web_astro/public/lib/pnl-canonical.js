/* Canonical P&L formulas — SHARED across home, dashboard, grid.html, tf.html.
   Brief 72a refactor (S72 2026-05-11): single source of truth, plain JS,
   loadable by static HTML pages via <script src="/lib/pnl-canonical.js">.
   Mirrors src/lib/pnl-canonical.ts (which TS-imports in dashboard-live.ts
   + live-stats.ts during Astro build).

   Exposes window.PnL.computeCanonicalState(trades, skim, livePrices, budget)
   and window.PnL.fetchLivePrices(symbols).

   Two metrics, both NET of fees, applied identically everywhere:

   - Total P&L (hero):
       netWorth   = cash + holdings_mtm + skim − fees
                  = budget + realized + unrealized − fees  (algebraic identity)
       totalPnL   = netWorth − budget
     where:
       cash       = budget − netInvested − skim
       netInvested= Σ buy.cost − Σ sell.cost
       holdings_mtm= Σ open_amount × live_price
       skim       = Σ reserve_ledger.amount
       fees       = Σ trades.fee  (USDT-equivalent)

   - Net Realized Profit (post-fees):
       netRealized = Σ realized_pnl − fees

   Brief 72a P2 (S72): when fee_asset == base_coin (live BUY), Binance
   scales fee from base balance — qty_acquired = filled − fee_native,
   avg = total_cost_usdt / qty_acquired_net. Paper trades default to
   fee_asset='USDT' → fee_native=0 → legacy behaviour. */

(function (global) {
  function replayAvgCost(trades) {
    var out = {};
    var sorted = trades.slice().sort(function (a, b) {
      var aT = a.created_at || "";
      var bT = b.created_at || "";
      return aT.localeCompare(bT);
    });
    for (var i = 0; i < sorted.length; i++) {
      var t = sorted[i];
      var sym = t.symbol;
      var base = (sym.split("/")[0] || "").toUpperCase();
      if (!out[sym]) {
        out[sym] = {
          holdings: 0, avgBuyPrice: 0,
          totalInvested: 0, totalReceived: 0,
          realized: 0, fees: 0
        };
      }
      var s = out[sym];
      var amt = Number(t.amount || 0);
      var cost = Number(t.cost || 0);
      var fee = Number(t.fee || 0);
      var feeAsset = ((t.fee_asset || "USDT") + "").toUpperCase();
      s.fees += fee;
      if (t.side === "buy") {
        var price = amt > 0 ? cost / amt : 0;
        var feeNativeEst = (feeAsset === base && price > 0) ? fee / price : 0;
        var qtyAcquired = amt - feeNativeEst;
        var newH = s.holdings + qtyAcquired;
        if (newH > 0) {
          s.avgBuyPrice = (s.avgBuyPrice * s.holdings + cost) / newH;
        }
        s.holdings = newH;
        s.totalInvested += cost;
      } else {
        s.holdings -= amt;
        s.totalReceived += cost;
        var dbPnl = Number(t.realized_pnl);
        if (isFinite(dbPnl)) s.realized += dbPnl;
        if (s.holdings <= 1e-9) {
          s.holdings = 0;
          s.avgBuyPrice = 0;
        }
      }
    }
    return out;
  }

  function computeCanonicalState(trades, skim, livePrices, budget) {
    var bySym = replayAvgCost(trades || []);
    var netInvested = 0;
    var holdingsMtm = 0;
    var fees = 0;
    var realized = 0;
    var unrealized = 0;
    var perCoin = [];
    var symbols = Object.keys(bySym);
    for (var i = 0; i < symbols.length; i++) {
      var sym = symbols[i];
      var s = bySym[sym];
      netInvested += (s.totalInvested - s.totalReceived);
      fees += s.fees;
      realized += s.realized;
      var px = (livePrices && livePrices[sym]) || 0;
      var mtm = (s.holdings > 0 && px > 0) ? s.holdings * px : 0;
      var openCost = s.avgBuyPrice * s.holdings;
      var unr = mtm > 0 ? mtm - openCost : 0;
      holdingsMtm += mtm;
      unrealized += unr;
      perCoin.push({
        symbol: sym,
        holdings: s.holdings,
        avgBuyPrice: s.avgBuyPrice,
        livePrice: px,
        mtm: mtm,
        openCost: openCost,
        unrealized: unr,
        unrealizedPct: openCost > 0 ? (unr / openCost) * 100 : 0,
        realized: s.realized,
        fees: s.fees,
        totalInvested: s.totalInvested,
        totalReceived: s.totalReceived
      });
    }
    var cash = budget - netInvested - skim;
    var netWorth = cash + holdingsMtm + skim - fees;
    var totalPnL = netWorth - budget;
    /* Known bias S72: 18 testnet sells have realized = (price-avg)×qty − fee_sell
       (post-backfill); paper trades remain gross. `realized - fees` subtracts
       fee_sell twice for testnet. Bias ≈ −$0.22 documented, deferred fix. */
    var netRealized = realized - fees;
    return {
      cash: cash,
      holdingsMtm: holdingsMtm,
      skim: skim,
      fees: fees,
      realized: realized,
      unrealized: unrealized,
      netInvested: netInvested,
      netWorth: netWorth,
      totalPnL: totalPnL,
      netRealized: netRealized,
      perCoin: perCoin
    };
  }

  function fetchLivePrices(symbols) {
    if (!symbols || !symbols.length) return Promise.resolve({});
    var binSyms = symbols.map(function (s) { return s.replace("/", ""); });
    var url = "https://api.binance.com/api/v3/ticker/price?symbols=" +
      encodeURIComponent(JSON.stringify(binSyms));
    return fetch(url).then(function (r) {
      if (!r.ok) return {};
      return r.json().then(function (arr) {
        var out = {};
        for (var i = 0; i < arr.length; i++) {
          var s = arr[i].symbol.replace(/USDT$/, "/USDT");
          out[s] = Number(arr[i].price);
        }
        return out;
      });
    }).catch(function () { return {}; });
  }

  global.PnL = {
    computeCanonicalState: computeCanonicalState,
    fetchLivePrices: fetchLivePrices,
    _replayAvgCost: replayAvgCost
  };
})(typeof window !== "undefined" ? window : this);
