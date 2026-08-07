"""
T.3 (S119b) → riscritto in S125: get_grid_state deve misurare KRAKEN, e l'ERA
intera del denaro reale — non piu' venue=binance, non piu' un ciclo solo.

STORIA, perche' questo file ha cambiato bandiera e la cosa e' voluta.

Nato il 2026-07-18 per bloccare il contrario: allora `get_grid_state` sommava
`capital_allocation` su TUTTE le righe grid, e la riga di collaudo Kraken
($25, is_active=false) faceva leggere "Started with $525". Il fix fu
`.eq("venue", "binance")`, e questo test lo inchiodava.

Il 2026-08-07 il cutover ha invertito i ruoli: le 4 righe binance sono
is_active=false e Kraken E' la flotta. Quel pin, lasciato in piedi, ha fatto
misurare al report serale il portafoglio testnet MORTO ($500 iniziali,
$539,54) e archiviarlo come snapshot del giorno. Il commento nel codice
prevedeva persino questo momento ("revisit at the full-Kraken cutover") e ci
siamo passati accanto lo stesso.

Quindi il test non viene cancellato: viene ribaltato. Le assert coprono ora
tre invarianti, e la terza e' quella che e' costata di piu':

  1. il budget e' la somma delle righe grid ATTIVE su venue=kraken
  2. le righe binance spente non compaiono come posizioni fantasma
  3. il filtro sui trade e' l'ERA (cycle LIKE 'kraken%'), non il ciclo
     singolo: il primo giro completo a denaro reale vive sotto
     'kraken_test' (l'ordine di prova del 17-lug) e un filtro `=kraken_2b`
     lo amputa. E' cosi' che report e dashboard finivano per dire due
     numeri diversi sullo stesso portafoglio.

Il finto client applica davvero `.eq()` e `.like()`, quindi i filtri sono
esercitati sul serio: toglierli fa fallire le assert, non passare in silenzio.

Run:
    python tests/test_grid_state_venue_filter_t3.py
    # oppure: pytest tests/test_grid_state_venue_filter_t3.py
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import commentary


# ----------------------------------------------------------------------
# Finto client Supabase che onora .eq() E .like() — cosi' sia il filtro
# venue sia quello sull'era sono esercitati davvero.
# ----------------------------------------------------------------------

class FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._eq = {}
        self._like = {}

    def select(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def like(self, col, pattern):
        self._like[col] = pattern
        return self

    def execute(self):
        def ok(r):
            if not all(r.get(k) == v for k, v in self._eq.items()):
                return False
            for col, pat in self._like.items():
                val = str(r.get(col) or "")
                if pat.endswith("%"):
                    if not val.startswith(pat[:-1]):
                        return False
                elif val != pat:
                    return False
            return True
        return SimpleNamespace(data=[r for r in self._rows if ok(r)])


class FakeSupabase:
    def __init__(self, tables):
        self._tables = tables  # name -> list[dict]

    def table(self, name):
        return FakeQuery(list(self._tables.get(name, [])))


# Righe bot_config come dopo il cutover del 2026-08-07: le 4 binance spente
# (allocazioni ancora scritte: la config sopravvive allo spegnimento) + le 2
# Kraken vive. capital_allocation come stringa, come la restituisce PostgREST.
BOT_CONFIG_ROWS = [
    {"symbol": "BTC/USDT",  "managed_by": "grid", "is_active": False, "venue": "binance", "cycle": "testnet_2", "capital_allocation": "200"},
    {"symbol": "SOL/USDT",  "managed_by": "grid", "is_active": False, "venue": "binance", "cycle": "testnet_2", "capital_allocation": "150"},
    {"symbol": "BONK/USDT", "managed_by": "grid", "is_active": False, "venue": "binance", "cycle": "testnet_2", "capital_allocation": "150"},
    {"symbol": "BTC/USD",   "managed_by": "grid", "is_active": True,  "venue": "kraken",  "cycle": "kraken_2b", "capital_allocation": "250"},
    {"symbol": "SOL/USD",   "managed_by": "grid", "is_active": True,  "venue": "kraken",  "cycle": "kraken_2b", "capital_allocation": "150"},
]


def _run(trades=None, reserve=None, prices=None):
    fake = FakeSupabase({
        "bot_config": BOT_CONFIG_ROWS,
        "trades": trades or [],
        "reserve_ledger": reserve or [],
    })
    orig_cycle = commentary.get_current_cycle
    orig_prices = commentary.fetch_live_prices
    commentary.get_current_cycle = lambda _c: "kraken_2b"
    commentary.fetch_live_prices = lambda _syms: (prices or {})
    try:
        return commentary.get_grid_state(fake)
    finally:
        commentary.get_current_cycle = orig_cycle
        commentary.fetch_live_prices = orig_prices


def test_grid_budget_is_kraken_only():
    state = _run()
    # 250 + 150 = 400. Le tre righe binance spente ($500) NON contano.
    assert state["initial_capital"] == 400.0, (
        f"il budget deve essere 400 (solo venue=kraken), letto {state['initial_capital']}. "
        "Se legge 900 il filtro venue e' sparito; se legge 500 e' tornato su binance "
        "— ed e' esattamente il bug che il 07-ago ha fatto misurare il testnet morto."
    )


def test_no_phantom_binance_position():
    state = _run()
    syms = [p["symbol"] for p in state["positions"]]
    assert not any(s.endswith("/USDT") for s in syms), (
        f"nessuna coppia /USDT deve comparire fra le posizioni Grid, lette {syms}"
    )
    assert set(syms) == {"BTC/USD", "SOL/USD"}, syms


# ----------------------------------------------------------------------
# L'invariante che e' costato di piu': l'ERA, non il ciclo.
# ----------------------------------------------------------------------

ERA_TRADES = [
    # kraken_test — il giro completo del 17-21 lug, chiuso in utile.
    {"symbol": "BTC/USD", "side": "buy",  "amount": 1.0, "price": 100.0, "cost": 100.0,
     "fee": 0.80, "fee_asset": "USD", "realized_pnl": 0.0, "created_at": "2026-07-17T00:00:00",
     "config_version": "v3", "cycle": "kraken_test", "managed_by": "grid"},
    {"symbol": "BTC/USD", "side": "sell", "amount": 1.0, "price": 110.0, "cost": 110.0,
     "fee": 0.88, "fee_asset": "USD", "realized_pnl": 8.32, "created_at": "2026-07-21T00:00:00",
     "config_version": "v3", "cycle": "kraken_test", "managed_by": "grid"},
    # kraken_2b — posizione ancora aperta.
    {"symbol": "SOL/USD", "side": "buy",  "amount": 1.0, "price": 50.0, "cost": 50.0,
     "fee": 0.40, "fee_asset": "USD", "realized_pnl": 0.0, "created_at": "2026-08-07T00:00:00",
     "config_version": "v3", "cycle": "kraken_2b", "managed_by": "grid"},
]


def test_era_includes_both_kraken_cycles():
    """Un filtro `cycle == 'kraken_2b'` amputerebbe il giro di kraken_test."""
    state = _run(trades=ERA_TRADES, prices={"SOL/USD": 50.0})
    # net_invested = 100 − 110 + 50 = 40 · holdings = 1 × 50 = 50 · fee = 2.08
    # total_value = 400 − 40 + 50 − 2.08 = 407.92
    assert abs(state["total_value"] - 407.92) < 0.01, (
        f"total_value {state['total_value']}: se legge ~397,92 il filtro e' tornato "
        "al ciclo singolo e ha buttato via il round-trip di kraken_test (+$10 lordi)."
    )
    # NB: qui `realized_total` e' la somma della colonna realized_pnl SALVATA
    # (8.32 = 10 lordi − 1.68 di fee del giro), non il replay avg-cost che usa
    # il sito dal Fix A (2026-06-29), che darebbe 10.00 lordi. Le due
    # convenzioni convivono: la cifra di TESTA (total_value / total_pnl)
    # coincide comunque, perche' la formula canonica sottrae le fee a parte.
    # Documentato qui perche' e' una trappola da "correggere" per sbaglio.
    assert abs(state["realized_total"] - 8.32) < 0.01, state["realized_total"]


# ----------------------------------------------------------------------
# T.3 (meta' fee) — la cifra di testa deve essere NETTA di commissioni,
# identica all'hero del sito (pnl-canonical.ts). Le fee sono soldi gia'
# usciti, non trattenuti.
# ----------------------------------------------------------------------

NET_OF_FEE_TRADES = [
    {"symbol": "BTC/USD", "side": "buy",  "amount": 1.0, "price": 100.0, "cost": 100.0,
     "fee": 0.10, "fee_asset": "USD", "realized_pnl": 0.0,  "created_at": "2026-08-01T00:00:00",
     "config_version": "v3", "cycle": "kraken_2b", "managed_by": "grid"},
    {"symbol": "BTC/USD", "side": "sell", "amount": 0.5, "price": 120.0, "cost": 60.0,
     "fee": 0.06, "fee_asset": "USD", "realized_pnl": 9.94, "created_at": "2026-08-02T00:00:00",
     "config_version": "v3", "cycle": "kraken_2b", "managed_by": "grid"},
]


def test_total_value_is_net_of_fees():
    state = _run(
        trades=NET_OF_FEE_TRADES,
        reserve=[{"symbol": "BTC/USD", "amount": "2.0", "config_version": "v3", "cycle": "kraken_2b"}],
        prices={"BTC/USD": 110.0},
    )
    # net_invested = 100 − 60 = 40 · holdings = 0.5 × 110 = 55 · fee = 0.16 · skim = 2
    # total_value = 400 − 40 + 55 − 0.16 = 414.84  (NETTO di fee)
    # cash        = 400 − 40 − 2      = 358.00
    assert abs(state["total_value"] - 414.84) < 0.01, state["total_value"]
    assert abs(state["cash"] - 358.00) < 0.01, state["cash"]
    assert abs(state["total_pnl"] - 14.84) < 0.01, state["total_pnl"]
    # La vecchia formula lorda (budget + realized-da-DB + unrealized) leggerebbe
    # 400 + 9.94 + 5 = 414.94, piu' alta esattamente della fee di buy. Guardia
    # contro il ritorno al lordo.
    assert state["total_value"] < 414.94, (
        f"total_value {state['total_value']} sembra lordo di fee (>= 414.94)"
    )


if __name__ == "__main__":
    test_grid_budget_is_kraken_only()
    test_no_phantom_binance_position()
    test_era_includes_both_kraken_cycles()
    test_total_value_is_net_of_fees()
    print("PASS — T.3/S125: get_grid_state misura Kraken, l'era intera, netto di fee.")
