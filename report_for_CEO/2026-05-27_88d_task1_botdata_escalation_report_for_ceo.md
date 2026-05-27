# Report per CEO — Brief 88d Task 1 escalato (numeri homepage Grid/TF)

**Da:** Claude Code (Intern)
**Data:** 2026-05-27 (S88)
**Brief:** `config/brief_88d_ui_debts.md` — Task 1 (finding audit 1.2)
**Stato:** Task 2, 3, 4 SHIPPED. **Task 1 NON applicato — serve decisione CEO.**

---

## Perché mi sono fermato su Task 1

Il brief assume (riga 33) che i numeri reali di Grid/TF *"potrebbero essere
identici o leggermente diversi"* dai placeholder a video. **Verificato su
Supabase: non è così.** La premessa del Task 1 è falsa, e applicarlo alla
lettera cambia la narrazione pubblica in modo che il brief non aveva previsto.

| Card homepage | Placeholder attuale (hardcoded) | **Realtà DB (config v3)** |
|---|---|---|
| Grid | 179 vinte / **0** perse | **19 vinte / 2 perse** |
| TF   | 174 vinte / 105 perse | **0 / 0 — TF non ha mai tradato** |

### Tre fatti dietro questi numeri

1. **TF non ha eseguito nessun trade** in questo testnet: zero righe
   `managed_by='tf'` nella tabella `trades`. Mostrare il dato vivo significa
   scrivere pubblicamente **"TF: 0 vittorie / 0 sconfitte"**. È onesto, ma è
   una scelta editoriale, non un fix tecnico.
2. **Grid crolla da 179 a 19** non per un errore: il testnet Binance si
   resetta ~1 volta al mese. Il 179/0 era il cumulato di un'era precedente;
   il 19/2 è l'era attuale (dal ~8 maggio). **Implicazione strutturale:** ogni
   reset testnet azzera questi contatori → un numero "vinte/perse live"
   ripartirà periodicamente da zero. Forse vinte/perse non è la metrica giusta
   da esporre live.
3. La query suggerita nel brief è tecnicamente sbagliata (`side='SELL'`
   maiuscolo: nel DB è minuscolo `'sell'`; `managed_by='tf'` non esiste). Lo so
   sistemare — lo segnalo solo perché conferma che il brief è stato scritto
   senza interrogare il DB.

---

## Decisione richiesta

Tre opzioni sul tavolo (Max ha già visto i numeri e ha scelto di girarle a te):

- **A — Numeri reali, così come sono.** Grid 19/2 live, TF mostra apertamente
  0/0. Massima trasparenza, coerente con l'audit. Costo narrativo: TF appare
  "non ha mai fatto niente", Grid sembra molto meno attivo.
- **B — Reali per Grid, TF "scanning".** Grid 19/2 live; per TF, invece di
  0/0, un messaggio tipo "scanning Tier 1-2, no trades yet" (la card già recita
  "Scanning Tier 1-2 assets. Shitcoins excluded."). Evita il 0/0 secco e resta
  veritiero.
- **C — Cambiare metrica.** Visto il reset mensile, esporre qualcosa di più
  stabile (es. P&L Grid corrente, o "giorni live") invece di vinte/perse, che
  si azzera a ogni reset.

Quando decidi, riapro il Task 1 con un mini-brief o procedo direttamente.
Il commento-placeholder nel codice (`index.astro:37-38`) resta lì finché non
chiudiamo questo punto.

---

## Cosa ho già shippato (resto del brief 88d)

- **Task 2** — banner trasparenza "perché 0 trade": riga sulla dashboard
  (sezione Today) che appare solo con 0 trade oggi + regime fear, con ultimo
  trade + giorni di osservazione. Regime corrente verificato = `fear`, ultimo
  trade 16 maggio → il banner è attivo ora. Nessun dato sensibile esposto.
- **Task 3** — fallback diario aggiornato a S88/S87/S86 (era fermo a S54/S55,
  25 giorni fa) + commento "aggiorna a ogni release".
- **Task 4** — mock dashboard rinfrescato ai valori reali correnti
  (era Day 34 / 2 maggio) + commento "aggiorna a ogni release".
