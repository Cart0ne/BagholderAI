# BRIEF — 36i: idle_reentry rapido per TF-managed

**Status (2026-04-19):** SUPERATO dal 39a. Il 39a ha già impostato
`idle_reentry_hours=1` sulle nuove ALLOCATE TF
(`bot/trend_follower/allocator.py:590`), più aggressivo del valore 2h
proposto qui — coerente con `scan_interval_hours=1` deployato insieme.
Archiviato senza azione residua. Nessuna modifica al codice richiesta.

---

**Date:** 2026-04-17
**Priority:** LOW — attivare quando CEO passa a rotation ≤ 1h
**Prerequisito:** 36e v2 + integration clamp deployati ✅
**Target branch:** `main` (push diretto)
**Deploy:** on-demand, richiede restart orchestrator per far ricaricare ai grid_runner il nuovo valore di bot_config

---

## Problema

Oggi `idle_reentry_hours` default è **24h**. Significa che se TF alloca una coin BULLISH e il grid fa la prima buy auto ma poi il prezzo vola via senza mai dippare del `buy_pct`, il bot resta con 1 solo lot per tutto il ciclo di allocazione (4h oggi, 1h in futuro) — perdendo il resto del movimento.

Esempio concreto: TST/USDT allocata 17 apr, ATR 13%, buy_pct=2.0 → se sale 15% senza dip > 2%, il bot fa 1 lot, aspetta +6% sell, chiude. Perde gli altri 9% di movimento.

---

## Fix

In `bot/trend_follower/allocator.py → apply_allocations`, aggiungere al `row_fields` di ALLOCATE:

```python
"idle_reentry_hours": 2,  # TF: re-enter fast on stale grids (vs 24h manual)
```

### Effetto

- Grid TF dopo 2h di zero trade → resetta reference a current price → nuova buy (logica già implementata in grid_bot, nessuna modifica lato bot)
- Se il coin va laterale/scende, idle non scatta (le buy normali partono sui dip)
- Se TF rotation accelera a 1h, 2h = al più 2 scan persi prima del re-entry — coerente

### Coupling con rotation interval

Il brief non tocca `scan_interval_hours` (separato, decisione CEO su `trend_config`). Ma la combinazione naturale è:
- `scan_interval_hours = 1` + `idle_reentry_hours = 2` → TF valuta swap ogni ora, grid si riallinea ogni 2h se stallato
- Se CEO mantiene `scan_interval = 4`, `idle_reentry = 2` resta comunque ragionevole (riequilibra 2× per ciclo)

---

## Applicazione alle allocate esistenti

Come da 36e integration: **non fare mass-update**. Le coin già attive mantengono `idle_reentry_hours` attuale (letto al loro ALLOCATE). Le nuove ALLOCATE/SWAP usano 2h.

Se CEO vuole applicare subito a MOVR/TST, può farlo via admin dashboard (campo già editable in `/admin` o `/tf`).

---

## Test

Aggiungere a `tests/test_trend_36e_v2.py` (o file nuovo):

- [ ] Mock ALLOCATE decision → verify `row_fields["idle_reentry_hours"] == 2`
- [ ] DEALLOCATE path non tocca idle_reentry (resta invariato)

In realtà il test può essere inline in un blocco "=== Session 36i ===" di 5 righe — non richiede file separato.

---

## Files da modificare

| File | Azione |
|---|---|
| `bot/trend_follower/allocator.py` | 1 riga in `row_fields` |
| `tests/test_trend_36e_v2.py` | 1 check aggiunto |

---

## Rollback

```bash
git revert <commit_hash>
git push origin main
ssh max@Mac-mini-di-Max.local 'cd /Volumes/Archivio/bagholderai && git pull'
# Restart orchestrator per far ripartire grid_runner con il vecchio default
```

Nessuna migration DB. Le coin allocate con `idle_reentry_hours=2` manterranno quel valore (o si possono aggiornare manualmente via admin).

---

## Commit format

```
feat(trend-follower): idle_reentry_hours=2 on TF ALLOCATE

Grids managed by the TF now reset their buy reference after 2h of
zero trades instead of inheriting the 24h manual default. Prevents
TF bots from riding a single lot through a sustained uptrend when
the price never dips enough to trigger the ATR-adaptive buy_pct.

Only new ALLOCATE/SWAP allocations are affected — existing rows keep
their current idle_reentry value unless manually updated via admin.
```

---

## Out of scope

- Rendere `tf_idle_reentry_hours` configurabile via `trend_config` (brief futuro se serve tunabilità dinamica)
- Mass-update delle allocate esistenti
- Cambiare `scan_interval_hours` (decisione CEO separata)
- Varianti strategy-based (momentum ladder, trailing buy) — brief 36f o successivi
