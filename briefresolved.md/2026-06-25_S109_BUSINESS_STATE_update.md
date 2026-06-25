# BUSINESS_STATE Update — S109 (2026-06-25)

**Istruzioni per CC:** applicare queste modifiche a BUSINESS_STATE.md.

---

## §1 — Header

Aggiornare:
```
**Last updated:** 2026-06-25 — Session 109 (Sherpa verdict + breadth signal analysis + bug cleanup + pre-mainnet infra).
```

## §4 — Decisioni Strategiche Recenti

Aggiungere IN CIMA alla tabella:

| 2026-06-25 (S109) | **Verdetto Sherpa 15gg: PASS per go-live** | Parametri protettivi stabili entro 24h. sell_pct flicker cosmetico (1-2bp/tick, 80-101 cambi in 14gg su SOL/BONK). Fix A/B/C rimandato a dopo osservazione regime change reale. Zero transizioni di regime nel periodo (extreme_fear continuo). Non blocca mainnet |
| 2026-06-25 (S109) | **Breadth signal Tier 3 → Tier 1/2: PARCHEGGIATO** | Analisi 6 mesi mainnet (422 coin, survivorship-safe): T3 NON anticipa rimbalzi T1/2 — semmai contrarian debole. F&G domina (corr -0.29 vs forward T1 7g), T3 correla 0.395 con F&G (ridondante). Soglia $2M filtra rumore ma non produce segnale. Ri-testare dopo regime risk-on sostenuto. Gamba 2 del volume framework CHIUSA (esito negativo) |
| 2026-06-25 (S109) | **Bug backlog azzerato + infra pre-mainnet shipped** | 4 bug chiusi (PortfolioManager rimosso, datetime deprecation 409→0 warning, exchange_order_id null fixato, validation_system aggiornato). Infra: slippage_buffer_pct colonna in bot_config (migration applicata), dust write-off come evento persistito, config chain 8 test e2e. Tutto committato, restart pending |
| 2026-06-25 (S109) | **Mobile smoke test eliminato da Fase 1** | Max lo fa già quotidianamente. Eliminato come gate formale |

## §5 — Domande Aperte per CC

Rimuovere (DONE):
- ~~Integration test config reader chain~~
- ~~DeprecationWarning datetime.utcnow()~~
- ~~PortfolioManager istanziato ma mai usato~~

## §6 — Vincoli/Deadline

Aggiornare la riga go-live:
```
| **Go-live mainnet** | Nessuna data fissa | Fase 1 quasi vuota: restano solo 1.3 (sessione go-live experiment) e 1.8 (Board approval). Bug backlog azzerato. Infra pre-mainnet shipped (restart pending). Gate esterno: annuncio Binance MiCA (atteso entro 30 giugno) |
```

## §7 — Cosa NON sta succedendo

Aggiungere:
```
| **Breadth Tier 3 come segnale Sentinel** | PARCHEGGIATO (S109). Analisi 6 mesi non supporta l'ipotesi (contrarian debole, ridondante con F&G). Ri-test dopo regime risk-on sostenuto. Script deterministico riutilizzabile |
```

Rimuovere (ora in §4 come decisione):
- ~~la riga "Sentinel market breadth da TF scanner — Phase B/C"~~ (sostituita dal parcheggio esplicito sopra)

---

## Follow-up da report CC S109

1. **Restart Mac Mini pending** — i fix bot/ sono committati ma non live. Max decide quando.
2. **git mv validation_and_control_system.md** → `config/` — riparare link rotti. CC può procedere.
