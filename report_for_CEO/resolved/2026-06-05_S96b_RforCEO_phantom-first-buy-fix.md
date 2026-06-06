# RforCEO — phantom-first-buy-fix (S96b)

**Da:** CC (Claude Code) · **A:** CEO + Max (Board) · **Data:** 2026-06-05 · **Sessione:** S96b
**Origine:** osservazione di Max — *"abbiamo resettato tutto e il mercato è bearish, perché non compra?"*
**Commit:** `32bfef4` + restart grid · **Esito:** ✅ SHIPPED & verificato live

---

## Sintesi

Dopo il clean slate (S96a) i 3 grid bot erano **vivi ma fermi**: non compravano, nonostante cash pieno e mercato in ribasso. Causa: un bug esposto proprio dal reset. Trovato, corretto, deployato. Al primo ciclo post-fix tutti e 3 hanno fatto la prima entrata.

## Il sintomo

Cash pieno ($150/$200/$150), `stop_buy` **non** attivo (quindi non era il freno extreme_fear), mercato bearish → eppure zero acquisti. I log ripetevano ogni ciclo:

> `Pct mode: existing holdings found, skipping first buy. Ref price set to avg buy $0.00000000`

## La diagnosi

Il gate del primo acquisto (`grid_bot.py:910`) controllava `state.holdings` — gli holdings **totali del wallet**, che dopo un reset testnet includono il "regalo" di baseline:

| | Posizione gestita (managed) | Wallet totale (incl. regalo testnet) |
|---|---|---|
| BTC | 0 | 1.0 |
| SOL | 0 | 6.0 |
| BONK | 0 | 18.446 |

Il bot vedeva la colonna destra (>0), concludeva "ho già una posizione", **saltava la prima entrata** e ancorava la scala di acquisto ad avg = $0 → trigger di buy "sotto $0" → non comprava mai.

**Risvolto sistemico:** non era un caso una-tantum. Il regalo di baseline ricompare a **ogni reset mensile della testnet** → senza il fix, ogni reset avrebbe paralizzato i grid.

## Il fix (1 riga)

```python
- if self.state.holdings > 0:      # totale, include i phantom (regalo testnet)
+ if self.managed_holdings > 0:    # posizione vera, esclude il regalo
```

`managed_holdings` (= total − phantom, introdotto nel brief 73c) era **già** la fonte di verità per tutti gli altri calcoli economici (unrealized, open_value, cap sulle vendite). Il gate del primo acquisto era l'unico punto rimasto su `state.holdings`. Su **mainnet** non esistono phantom → `managed == total` → **zero cambio di comportamento**.

## Verifica live (post-restart)

| Grid | Prima entrata | Prezzo |
|---|---|---|
| BTC | 0.00079 BTC (~$49.60) | $62.780 |
| SOL | 0.303 SOL (~$19.96) | $65.86 |
| BONK | 5.446.623 BONK (~$25.16) | $0.00000462 |

Tutti: *"first buy at market (reference established)"*. Da qui scala normale (accumulo sui ribassi). Il clean slate è ora pienamente operativo.

## Note

- Nessun brief sorgente: fix nato da un'osservazione di Max in chat. Anti-assenso: la diagnosi stessa è l'obiezione (il sintomo "bearish ma non compra" aveva due spiegazioni candidate — stop_buy o phantom; ho escluso stop_buy coi dati prima di toccare il codice).
- Fallback se sbagliato: reversibile (1 riga), ed è paper trading. Ma verificato live, non serve.
- Catena: segue S96a (clean slate, `report_for_CEO/2026-06-04_S96a_RforCEO_clean-slate-testnet.md`).
