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

### §4.B2 — NUOVA: Analisi volume intra-Tier 3 (gambe 2+3 del framework parcheggiato)

Assorbe `PARKED_tf_volume_analysis_framework.md` (S108). Non
basta contare quante coin Tier 3 sono bullish — serve anche
la dinamica di volume.

Per ogni coin Tier 3 classificata BULLISH in un dato giorno:
1. Registrare il volume 24h reale
2. Calcolare la variazione di volume vs la media 7gg della
   stessa coin (volume spike = sì/no)
3. Sub-segmentare Tier 3 in due fasce:
   - **T3-micro** (volume < $2M) — zona moonshot/crash dalla
     analisi S108 (BICO +100% a 0.67M, HMSTR -53% a 0.61M)
   - **T3-mid** (volume $2M–$20M) — zona più composta

La domanda specifica: quando Tier 3 si accende, il segnale
leading è concentrato nei T3-mid (volume > 2M, più affidabile)
o nei T3-micro (volume < 2M, puro rumore)? Se i T3-mid con
volume in crescita anticipano i rimbalzi Tier 1/2 ma i T3-micro
no, abbiamo un filtro operativo concreto.

Output aggiuntivo: tabella che confronta accuratezza del segnale
breadth con e senza il filtro volume 2M.

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

2. **Volume come filtro:** Il segnale leading si concentra nei
   T3-mid (>$2M volume) o è diffuso? I T3-micro (<$2M) aggiungono
   informazione o sono rumore? Il volume in crescita (spike vs
   media 7gg) migliora l'accuratezza del segnale?

3. **F&G ci arriva prima o dopo?** Nello stesso episodio, F&G ha
   già segnalato il cambio? Se sì → il segnale breadth è ridondante.
   Se no → aggiunge informazione unica.

4. **Falsi positivi:** Quante volte la breadth Tier 3 si accende
   senza che Tier 1/2 rimbalzi? (Froth speculativa isolata, senza
   propagazione.) Un segnale con troppi falsi positivi non è
   operativo.

5. **Direzione:** Il segnale è pro-ciclico (anticipa rialzi) o
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
2. Sub-segmentazione Tier 3: breadth T3-micro vs T3-mid, con
   e senza filtro volume spike
3. Tabella episodi: data picco breadth T3 (totale e sub-segmento),
   rendimento forward T1/T2 a 24h/3g/7g, valore F&G, volume
   medio delle T3 bullish quel giorno
4. Conclusione: promuovi / parcheggia / boccia (con evidenza)

---

## File assorbiti

Questa nota integrativa assorbe:
- `PARKED_tf_volume_analysis_framework.md` (gamba 2: backtest
  EMA/RSI su dati storici Binance, soglia 2M volume). La gamba 3
  (bibliografia) resta parcheggiata separatamente — è desk
  research, non analisi dati.

Se CC completa questa analisi, la gamba 2 del volume framework
si considera chiusa.

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
