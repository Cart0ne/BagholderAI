# Audit Request 20260507 — V1 Calibration

**Area**: 1 (Tecnica bot/agenti)
**Topic**: Coerenza Sentinel↔Sherpa↔Grid post-Phase 1

## Domanda guida
Dopo il refactor Phase 1 di grid_bot.py, l'interazione tra Sentinel, 
Sherpa e i grid bots è ancora corretta? Sentinel passa a Sherpa dati 
che arrivano coerenti? I parametri scritti da Sherpa nel bot_config 
vengono letti correttamente dai grid bots dopo lo split?

## Scope
- [Sentinel](bot/sentinel/main.py): cosa scrive in DB? Quando? In che formato?
- [Sherpa](bot/sherpa/main.py): cosa legge da Sentinel? Cosa scrive in bot_config?
- [Grid bots](bot/strategies/grid_bot.py): leggono i parametri aggiornati senza rifare init?
- Schema DB: tabelle coinvolte (`bot_config`, eventuali tabelle Sentinel)
- Log recenti per spot-check: ultime 24h dei log Sentinel + Sherpa + grid

NON toccare: codice di trading vero e proprio (FIFO, dust, ecc. — già 
auditato in Phase 1 review).

## Allegati
- Repo aggiornato (sync GitHub via Project Knowledge)
- Path log Mac Mini: `/Volumes/Archivio/bagholderai/logs/` (verificare 
  accessibilità via SSH come da .claude/settings.local.json)

## Output atteso
- Verdetto APPROVED / CON RISERVE / REJECTED su coerenza interazione
- Lista findings con file:linea
- Eventuali drift (es. Sherpa scrive parametro X ma Grid non lo rilegge)
- Sintesi 1-2 righe per PROJECT_STATE.md sezione 9
