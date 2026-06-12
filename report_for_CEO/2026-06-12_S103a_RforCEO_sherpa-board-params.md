# Report S103a — sherpa-board-params — 2026-06-12

**Brief sorgente:** `config/2026-06-12_S103a_brief_sherpa-board-params.md`
**Commit codice:** `a1826fe` (`bot(S103a): 4 protective Board params -> Sherpa-managed...`)
**Migration Supabase:** `s103a_sherpa_board_params` (applicata, verificata)
**Esito:** SHIPPED — **restart NON eseguito** (Max restarta sul Mac Mini; il codice gira al prossimo restart)
**Suite:** 219/219 (198 + 21 nuovi)

---

## 1. Cosa chiedeva il brief

Spostare i 4 parametri protettivi — `stop_buy_drawdown_pct`,
`stop_buy_unlock_hours`, `dead_zone_hours`, `profit_target_pct` (il "min_profit"
del brief) — da Board-only/statici a **Sherpa-managed** su una tabella discreta
**(regime × tier di volatilità)**, con scrittura al cambio regime + cooldown 24h
sull'override Board.

## 2. Anti-assenso (§7) — 1 flag bloccante + 1 obiezione tecnica, risolti con Max PRIMA del codice

**Flag bloccante (drift brief↔stato).** Il brief ribalta una decisione di
**ieri**: S102 (2026-06-11) aveva deciso esplicitamente "**4 parametri restano
Board-only e statici — Sicurezza ≠ strategia**". Ho fermato e segnalato a Max,
mostrando però la sfumatura: il brief è coerente col **principio di ownership**
S102 ("Board=soldi: allocation/$-trade/skim; Sherpa=tutto il resto"). Max (nodo
di sintesi, veto) ha **confermato il ribaltamento**: i 4 vanno a Sherpa,
dinamici. → vedi Decisione 1.

**Obiezione tecnica (tier-flapping).** Il sistema a tier ha un cliff **senza
ammortizzatore** sui parametri di sicurezza (il brief vieta l'amplitude cap su
questi 4: sono interi, il cap sarebbe rumore). SOL è a multiplier ~1.53, a 0.12
dal confine MID/HIGH (1.65); il multiplier è uno stdev a 7 giorni **ricalcolato
ogni ora**. Una coin sul confine riattraverserebbe avanti e indietro →
riscritture secche 2↔1 di un freno che protegge la cassa. L'auto-obiezione del
brief copriva solo la classificazione *una tantum* di una coin nuova, non una
coin *viva* che deriva nel tempo. → Max ha scelto la cura: **debounce**.

## 3. Cosa è stato costruito

### Tabella + tier (`bot/sherpa/board_parameter_rules.py`, nuovo)
`BOARD_TABLE[regime][tier]` (5×3, valori del brief), `classify_tier(mult)` coi
confini **1.30 / 1.65** in `settings.py`, `calculate_board_parameters`. Nessun
cap, nessun clamp (interi). `profit_target_pct` = 0 in tutte e 15 le celle
(scaffolding per attivazione futura). I nomi colonna combaciano con `bot_config`
(`profit_target_pct`, **non** il `min_profit_pct` del brief — verificato:
[config_sync.py:42](../bot/grid_runner/config_sync.py#L42)).

### Debounce (`bot/sherpa/board_debounce.py`, nuovo — DEVIAZIONE dal brief, su direttiva Board)
`decide()` puro: una nuova coppia (regime, tier) osservata deve reggere
**continuativamente 24h** prima che Sherpa la adotti. Copre con **una sola
regola** sia il flapping sul **tier** (orario) sia quello sul **regime** (il
Fear&Greed sul confine di banda — es. `stop_buy_dd` LOW vale 4 in fear e 1 in
neutral, salterebbe 4↔1 a ogni 4h). Una coin **nuova** prende i freni del suo
tier **subito** (debounce solo sui cambi successivi). Stato persistito in
`sherpa_board_state` → il cronometro **sopravvive ai riavvii** (risolve la
fragilità del timer-in-memoria che avevo segnalato a Max).

### Loop (`bot/sherpa/main.py`)
Scrive 7 parametri invece di 3. In LIVE: risolve+debounce i 4 board, scrive i
sopravvissuti (cooldown-aware, riusa `cooldown_manager` invariato), logga
current/proposed board + tier sulla riga proposta. In dry_run: logga il lookup
istantaneo, **nessun** side-effect sullo stato. Whitelist `config_writer.py`
estesa additivamente (i 3 di strategia restano identici nel formato).

### Dashboard (`web_astro/public/admin.html`)
"Last proposals": **sotto-riga "safety"** per coin (current vs proposed
`dd%/unlock_h/dz_h/min_profit%` + badge **tier**), stessa logica colori
(⚠ diff / 🔒 cooldown / ✓ aligned). Bonus onestà: tolte le label **DRY_RUN**
stale (Sherpa è LIVE da S102b) e chiarita la nota stop-buy (la *lampada* resta
derivata; la *soglia* `stop_buy_drawdown_pct` ora è Sherpa-managed).

### Migration `s103a_sherpa_board_params` (approvata da Max, decisione 1)
`sherpa_proposals` +8 colonne (`proposed_stop_buy_dd`, current/proposed per
unlock_h / dead_zone_h / profit_target, `volatility_tier` con CHECK
LOW/MID/HIGH); nuova tabella `sherpa_board_state` (RLS anon select/insert/update,
come il pattern `sherpa_proposals` + update per l'upsert).

## 4. Cosa scriverà il primo tick LIVE (regime attuale: extreme_fear)

Verificato con smoke test sul codice reale (prima classificazione = immediata):

| Coin | tier | scrive (current→target) |
|------|------|--------------------------|
| BTC  | LOW  | dd 2→3, unlock 2→12, dead_zone 4→2 |
| SOL  | MID  | dd 2→4, unlock 0→12 |
| BONK | HIGH | dd 2→5, unlock 1→12, dead_zone 4→2 |

`profit_target` resta 0 ovunque (già 0 nel DB live → nessun clobber). Nessun
override Board nelle 48h → niente cooldown, takeover libero. Sono gli effetti
voluti del brief (allargare il freno e tenere la valvola aperta 12h in panico).

## 5. Decisioni (Decision Log)

**Decisione 1 — i 4 protettivi diventano Sherpa-managed dinamici (ribalta S102).**
RAZIONALE: il principio ownership S102 (Board=soldi, Sherpa=resto) prevale sulla
decisione specifica "statici"; testnet = zero rischio; il go-live mainnet è
gated a parte. ALTERNATIVE: tenere S102 (statici); via di mezzo (solo
`stop_buy_dd` regime-aware). FALLBACK: revert `a1826fe`; togliere i 4 dalla
whitelist `config_writer` li ricongela a Board-only senza altri cambi.

**Decisione 2 — debounce a 24h sulla coppia (regime, tier), persistito in DB
(NON nel brief).** RAZIONALE: senza cap, i freni flapperebbero sul confine
(tier orario + regime sul bordo banda); il dwell sul valore risolto copre
entrambi gli assi con una regola. Costo: ritarda anche le reazioni giuste di
~24h, ma su un freno "prudente durante l'onset" è il lato giusto su cui
sbagliare. ALTERNATIVE: banda morta asimmetrica sui confini (stateless, ma non
copre il regime); congelare il tier all'ingresso (strada B, ma niente
auto-adattamento — Max voleva l'auto-adattamento). FALLBACK: `BOARD_DEBOUNCE_HOURS`
in settings; svuotare `sherpa_board_state` = riparte da "prima classificazione".

**Decisione 3 — colonna DB `profit_target` (non `min_profit_pct`).** RAZIONALE:
il nome reale in `bot_config` è `profit_target_pct`; allineare evita drift
lessicale (memoria `feedback_lexical_drift_after_rename`).

## 6. Off-limits rispettati
NON toccati: `BASE_TABLE`/`RANGES` dei 3 di strategia · `volatility.py` ·
logica Sentinel · allocation/capital_per_trade/skim_pct (restano Board puri) ·
**nessun restart bot**.

## 7. Da fare a Max
1. **Pull + restart orchestrator sul Mac Mini** → il codice va LIVE (la tabella
   `sherpa_board_state` si popola al primo tick, takeover §4).
2. (Opzionale) decidere se pushare ora o al restart — multi-macchina.

## 8. Note / follow-up
- `grid.html` "3 fasce per moneta" = **brief separato** (S103b già in `config/`).
  L'ownership di oggi ne cambia il disegno: non più "Sherpa / Board-sicurezza /
  Board-soldi" ma "Sherpa-strategia / Sherpa-sicurezza / Board-soldi".
- Il cooldown dei 4 board non è loggato in `sherpa_proposals.cooldown_parameters`
  (quella colonna traccia i 3 di strategia) → la sotto-riga dashboard mostra
  diff/aligned ma non il 🔒 per i board. Micro-follow-up se serve.
