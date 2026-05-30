# Proposta — DECISION PANEL: protocollo per decisioni ad alto rischio

**Status:** 🟡 DRAFT / proposta — da discutere col CEO (sessione 2026-05-30 pomeriggio)
**Preparato da:** CC, su richiesta di Max
**Data:** 2026-05-30
**Lingua:** italiano (bozza di lavoro per revisione Max/CEO; il blocco destinato a CLAUDE.md è già in italiano)

---

## Origine e contesto

Adattamento di un pattern suggerito da un utente r/AI_Agents (`pr0file_1`) in
risposta al post BagHolderAI nel megathread. **NON è una copia** del suo prompt:
rielaborato per l'architettura BagHolderAI con (a) differenziazione per
*informazione* e non solo attitudine, (b) gating sui costi, (c) regole
anti-assenso, (d) umano come nodo di sintesi finale.

Risponde al failure mode documentato dopo 90 sessioni: l'AI propone soluzioni
tecnicamente corrette ma "flat", e adotta istantaneamente le controproposte
("yes, that's better") senza vera deliberazione — assenso cieco.

Collega: post Dev.to *"AI Is Useful. But It Doesn't Think Like We Do."* +
entità **Auditor** già esistente (sessione CC fresca, zero continuità).

---

## Bozza di sezione per CLAUDE.md (numero/placement da decidere)

```
═══════════════════════════════════════════
 [7] DECISION PANEL — per decisioni ad alto rischio
═══════════════════════════════════════════

SCOPO
Contrastare due failure mode osservati dopo 90 sessioni:
(a) l'AI propone soluzioni tecnicamente corrette ma "flat";
(b) l'AI adotta istantaneamente una controproposta ("yes, that's better")
    senza vera deliberazione — assenso cieco.
Il panel forza pushback genuino PRIMA di implementare e produce DOMANDE
per l'umano, non un verdetto.

QUANDO SI ATTIVA (gating — NON su ogni azione)
Solo dove "sbagliare costa più che eseguire il panel" (~5x costo / ~10x tempo):
- cambi a regole di trading / parametri di rischio (la classe del bug-soglia)
- decisioni architetturali con blast radius ampio
- azioni difficili da annullare / irreversibili
NON si attiva per: edit di codice puntuali, fix piccoli, brief già ben scopati.
Test rapido: "se questa decisione è sbagliata, il danno supera il costo
del panel?" Se no → salta.

COMPOSIZIONE (differenziata per INFORMAZIONE, non solo attitudine)
Il valore non è "3 personas nella stessa testa" — è contesto + dati diversi.
Tre lenti, ognuna idealmente in sessione FRESCA e/o con informazione diversa:
 1. Skeptic    — fattibilità, rischi, fallacie logiche.  (CC: vede codice/dati)
 2. Contrarian — argomenta la posizione OPPOSTA, teorie alternative.
                 (sessione fresca, forzata a dissentire)
 3. Pragmatist — esecuzione, vincoli reali, conseguenze non volute.
                 (vantaggio operativo / mercato live)
Mappa sugli agenti esistenti: CEO (strategia), CC (codice/dati),
Haiku (mercato ora), Auditor (sessione fresca = home naturale per una lente).

PROCESSO
 1. Posizione: il proponente (di norma il CEO) scrive la decisione come brief
    breve — claim + razionale + cosa cambia.
 2. Critica indipendente: ogni lente critica DA SOLA, senza vedere le altre,
    dalla propria prospettiva/dati. Regola dura: ogni lente DEVE produrre
    ≥1 obiezione reale, o dichiarare esplicitamente perché non ne esiste.
 3. Cross-response: le lenti rispondono brevemente alle critiche altrui.
 4. Sintesi: raccoglie il pushback più forte e produce 3-5 DOMANDE mirate
    all'umano — NON una decisione.
 5. Decide l'umano: Max (o CEO con veto di Max) sceglie col pushback in mano.
    L'umano è il nodo di sintesi finale, non il panel.

ANTI-PATTERN (regole, non consigli)
- Vietato il teatrino dell'assenso: se tutte le lenti concordano al primo giro,
  il panel ha FALLITO — rilancia o usa sessioni più indipendenti.
- Diffida della convergenza stesso-modello: preferisci sessioni FRESCHE
  (zero storia condivisa) e informazione DIVERSA per lente. Se è tutto
  un'unica sessione che recita, è la versione debole: non sovra-fidarti.
- La sintesi non si risolve mai in "yes that's better" riflesso (è il failure
  mode che vogliamo uccidere): output = domande + rischi, mai timbro.
- Il panel ALZA il pavimento, non manda in pensione l'umano. La sintesi
  cross-dominio vera può restare di Max (tesi "AI doesn't think like we do").

LOG
Registra obiezioni del panel + decisione finale nel decision log (formato [4]).
Senza log, il CEO vede solo il risultato e non sa che c'era un trade-off.
```

---

## Decisioni da prendere col CEO

1. **Placement + numero** — provvisorio `[7]`; dove va in CLAUDE.md.
2. **Rigore vs costo** — panel come **sessioni fresche separate** (più vero, più
   lavoro-corriere per Max) o **intra-sessione** (più economico, più debole)?
   È il trade-off centrale da fissare.
3. **Soglia di gating** — cosa conta come "decisione grossa" nel concreto
   (servono esempi reali, non solo categorie).
4. **Casting delle lenti** — chi fa Skeptic/Contrarian/Pragmatist tra
   CEO / CC / Haiku / Auditor.
5. **Flusso file** — formalizzare un `drafts/panel_<topic>.md` per far girare
   posizione → critiche → sintesi via i state file esistenti?

---

## Note operative

- CC **non ha modificato** CLAUDE.md. Questa è solo una proposta in `drafts/`.
- Se approvata: integrare come nuova sezione in CLAUDE.md + (eventuale) menzione
  in WORKFLOW.md; poi spostare questo draft in `drafts/applied/2026-05/`.
- File salvato in locale, **non committato** (decisione di Max — repo multi-macchina).
