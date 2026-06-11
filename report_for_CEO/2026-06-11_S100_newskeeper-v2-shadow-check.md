# NewsKeeper v2 «Barometro» — Shadow Check T+36h
**Data**: 2026-06-11 · **Sessione**: S100 (routine remota)  
**Brief sorgente**: `briefresolved.md/2026-06-09_S100_brief_newskeeper-v2-barometro.md`  
**Check eseguito**: ~08:20 UTC (circa 36h dal lancio shadow 2026-06-09 20:05 UTC)

---

## 1. Query 1 — Salute signals (ultime 36h)

| classifier | rows | distinct_keys | high | medium | discard | directional |
|---|---|---|---|---|---|---|
| `barometro_v1` | **203** | 28 | 50 | 100 | 53 | 116 |
| `barometro_fallback` | **0** | — | — | — | — | — |

- 203 righe scritte da Haiku (`barometro_v1`) in 36h — processo attivo e produttivo.
- **ZERO righe `barometro_fallback`**: Haiku non ha mai fallito un'invocazione. Eccellente.
- 28 event_key distinti: la dedup event-level funziona (gli stessi articoli vengono ri-processati nei cicli successivi con la stessa key; l'aggregatore deduplica prima del voto). Media ~7.25 righe/key = storie che permangono nel feed 24h e vengono ri-viste più volte.
- 116/203 (57%) voti direzionali — il classificatore prende posizione sulla maggioranza degli item non-discard.
- Distribuzione relevance: 50 high / 100 medium / 53 discard (~26% discard, in linea con l'atteso su feed misti).

---

## 2. Query 2 — Freschezza

| ultimo_segnale (UTC) | tot_36h |
|---|---|
| 2026-06-11 **07:17:18** | 203 |

- Ultimo segnale **~1h fa** rispetto al check. Ampiamente dentro la soglia 2h.
- Il processo è **vivo e scrive regolarmente** (ciclo ogni ~15 min).

---

## 3. Query 3 — Regime aggregato (ultime 36h)

| kind | n | ultimo (UTC) |
|---|---|---|
| `heartbeat` | 6 | 2026-06-11 06:17 |
| `flip` | 1 | 2026-06-10 00:08 |

- 6 heartbeat in 36h (intervallo ~6h, by design write-on-change).
- Ultimo heartbeat **06:17 UTC** (~2h fa dal check) — ampiamente dentro la soglia 8h.
- **1 flip** avvenuto: da `neutral` → `bearish` a 2026-06-10 00:08 UTC (circa 4h dopo il primo tick del barometro).

---

## 4. Query 4 — Regime dettaglio (ultime 8 righe, più recente prima)

| ts (UTC) | state | net_score | abstain_frac | vote_count | kind |
|---|---|---|---|---|---|
| 06-11 06:17 | **bearish** | −0.6639 | **0** | 19 | heartbeat |
| 06-11 00:16 | bearish | −0.4035 | 0 | 18 | heartbeat |
| 06-10 18:13 | bearish | −0.4286 | 0 | 19 | heartbeat |
| 06-10 12:10 | bearish | −0.7439 | 0 | 16 | heartbeat |
| 06-10 06:09 | bearish | −0.5333 | 0 | 16 | heartbeat |
| 06-10 00:08 | bearish | −0.4706 | 0 | 16 | **flip** |
| 06-09 20:05 | neutral | −0.4555 | 0 | 6 | heartbeat |

Il barometro è rimasto `bearish` per le ultime ~31h senza interruzioni. Il net_score varia da −0.40 a −0.74 — ben al di sotto della soglia di flip (~−0.12/−0.15). Nessun segnale di inversione imminente. Il vote_count sale da 6 (primo tick, feed parzialmente caricato) a 16-19 nei cicli successivi, che è il regime stabile atteso.

---

## 5. Verdetto

### ✅ OK — Barometro operativo e sano

Tutti i criteri di salute soddisfatti:

| Criterio | Soglia | Valore | Esito |
|---|---|---|---|
| Righe `barometro_v1` | > 0 (idealmente centinaia) | **203** | ✅ |
| Righe `barometro_fallback` | = 0 | **0** | ✅ |
| Freschezza ultimo segnale | < 2h | **~1h** | ✅ |
| Heartbeat regime nelle ultime 8h | ≥ 1 | **1** (06:17 UTC) | ✅ |
| `abstain_frac` | non alto (< ~0.5) | **0** su tutti i tick | ✅ |

Nessuna anomalia. Il processo gira, Haiku classifica con piena confidenza, il regime registra correttamente.

---

## 6. Valutazione muto-vs-lento (metrica critica)

**Il barometro NON è muto. È lento, come previsto.**

`abstain_frac = 0` su tutte le 7 righe regime disponibili — nessun voto astiene. Questo significa che Haiku classifica con confidenza sufficiente tutti gli item che superano la soglia di relevance. Il regime si è mosso (flip neutral→bearish a T+4h), il net_score ha ampiezza significativa (range −0.40/−0.74), e il vote_count è stabile a 16-19.

**Rischio "muto"**: non presente allo stato attuale. Da tenere monitorato nelle prossime settimane se il mercato si stabilizzasse in una fase laterale mista, dove le news potrebbero diventare più ambigue e Haiku potrebbe iniziare ad astenersi.

**Nota anti-assenso B (da PROJECT_STATE §3)**: i parametri sono stati calibrati su un mercato solo-bear. Lo stato bearish persistente (31h) non consente ancora di osservare la risposta del barometro a un rimbalzo. Il verdetto T+14 (~23 giugno) è il momento giusto per valutare l'adattamento a condizioni miste, non questo check T+36h.

---

## 7. Promemoria verdetto T+14

**Verdetto GRANDE a T+14 (~23 giugno)**: validare i flip del barometro vs ritorno prezzo BTC a 24h (da `sentinel_scores.btc_price` a flip+24h), **NON vs Fear&Greed** (circolare).

- Flip da validare: `neutral→bearish` avvenuto **2026-06-10 00:08 UTC** (net_score −0.4706, vote_count 16). Cercare `sentinel_scores.btc_price` intorno a quella timestamp e confrontare con il prezzo 24h dopo.
- Se i 14gg restano solo-bear senza inversioni: verdetto parziale, estendere l'osservazione.
- Esiti possibili: promuovere (cablaggio Sentinel) o bocciare (→ `/news`, blog "esperimento fallito").

---

*Report generato da sessione remota di verifica (Claude Code, ambiente cloud). Nessuna modifica al codice bot, nessun restart.*
