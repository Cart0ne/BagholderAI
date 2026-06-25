# Nota integrativa — Brief tier-breadth-regime-signal

**Sessione:** S109, 25 giugno 2026
**Autore:** CEO (Claude), su indicazione Board (Max)
**Si applica a:** `config/2026-06-18_brief_tier-breadth-regime-signal.md`

---

## Riformulazione dell'ipotesi (Board, S109)

Il brief originale (CC, S107) pone la domanda: "la breadth Tier 3 anticipa
o accompagna i movimenti di regime Sentinel / F&G?"

**Max corregge il tiro.** La domanda giusta NON è se Tier 3 correla con F&G
— quello sarebbe ridondante (F&G è già in Sentinel). La domanda è:

> **Un'espansione dei bullish Tier 3 anticipa i rimbalzi di prezzo
> delle coin Tier 1 e Tier 2 che F&G non coglie?**

La logica: quando l'appetito al rischio torna, il denaro speculativo
rientra prima nelle small-cap (Tier 3) perché sono le più sensibili.
Se il movimento è reale, si propaga verso i blue chip (Tier 1/2). F&G
è un indicatore di sentiment aggregato — non misura la struttura del
flusso di capitale lungo la curva di rischio.

Se confermato, questo segnale sarebbe **complementare** a F&G, non
ridondante — e chiuderebbe l'obiezione anti-assenso §6.1 del brief
originale.

---

## Modifiche al piano esecutivo (§4 del brief originale)

### §4.A — Costruire la serie breadth MAINNET (invariato)

Universo: top 150–300 USDT pair per volume reale. Klines 4h.
Stessi indicatori del nostro classifier (EMA20/50, RSI14, ATR14).
Tier per volume reale (soglie 100M / 20M). Finestra: 3–6 mesi
(servono transizioni di mercato reali).

### §4.B — NUOVA: Serie rendimenti Tier 1 e Tier 2

Per ogni giorno della finestra, calcolare il rendimento forward
delle coin Tier 1 e Tier 2 a 24h, 3g e 7g. Usare un paniere
ponderato per volume (es. BTC, ETH, SOL, BNB, XRP per Tier 1;
le top 10–15 per volume per Tier 2).

Questo è l'asse Y dell'analisi — ciò che la breadth dovrebbe
predire.

### §4.C — F&G storico come controllo (NON come target)

Scaricare la serie F&G da alternative.me per lo stesso periodo.
F&G serve come **gruppo di controllo**: se la breadth Tier 3
anticipa i rimbalzi Tier 1/2 ma F&G li anticipa ugualmente,
il segnale è ridondante. Se la breadth li anticipa e F&G no
(o F&G li coglie in ritardo), il segnale aggiunge informazione.

### §4.D — Domande riviste (sostituiscono §4.D del brief originale)

1. **Lead/lag:** Un picco di breadth Tier 3 (es. >20% bullish in
   un giorno dopo giorni a 0–5%) precede un rimbalzo positivo
   delle Tier 1/2 a 24h/3g/7g?

2. **F&G ci arriva prima o dopo?** Nello stesso episodio, F&G ha
   già segnalato il cambio? Se sì → il segnale breadth è ridondante.
   Se no → aggiunge informazione unica.

3. **Falsi positivi:** Quante volte la breadth Tier 3 si accende
   senza che Tier 1/2 rimbalzi? (Froth speculativa isolata, senza
   propagazione.) Un segnale con troppi falsi positivi non è
   operativo.

4. **Direzione:** Il segnale è pro-ciclico (anticipa rialzi) o
   contrarian (picco = fine rally)? La risposta determina come
   cablarlo: pro-ciclico → sblocca buy; contrarian → alza
   protezione.

### §4.E — Eliminata

La serie testnet (§4.B del brief originale) non serve più.
Sappiamo già che il testnet ha tier degenerati. Inutile duplicare
il lavoro.

---

## Vincoli (invariati rispetto al brief originale)

- Read-only assoluto: no scritture Supabase, no codice bot,
  no restart.
- API pubblica Binance (no key) + alternative.me (F&G storico).
- Asset riproducibili in `report_for_CEO/assets/`.
- Nessuna decisione di cablaggio: solo misura → Board decide.

---

## Output atteso

Report per CEO con:
1. Serie breadth per tier (grafico) + serie rendimento Tier 1/2
2. Tabella episodi: data picco breadth T3, rendimento forward
   T1/T2 a 24h/3g/7g, valore F&G dello stesso giorno
3. Conclusione: promuovi / parcheggia / boccia (con evidenza)

---

## Anti-assenso (CEO)

L'ipotesi è elegante, ma il rischio principale è che **non ci
siano abbastanza episodi di transizione** nella finestra 3–6 mesi.
Se il mercato è stato monotonamente bear (come lo è stato
recentemente), la breadth Tier 3 potrebbe essere stata zero per
settimane e non avremmo niente da misurare. In quel caso il
verdetto è **parcheggia** (dati insufficienti), non boccia — e ci
servirà un cambio di mercato reale per validare.

Seconda obiezione: il nostro classifier (EMA20/50 4h) non è
"la verità" — è un proxy. Se la breadth misurata con questo
proxy non mostra segnale, potrebbe semplicemente significare che
il proxy è troppo grossolano, non che l'ipotesi è sbagliata.
Dichiarare questo limite nel report.
