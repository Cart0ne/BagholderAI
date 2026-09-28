Brief S131b — contenuti-manutenzione — 2026-09-28

**Da:** CEO · **Per:** CC · **Board:** Max (approvato in S131, 28-set)
**Basato su:** `config/MASTER_TASK_LIST_2026-09-28.md` (S130): voce "[S127] Umami API 401 — chiusa, esecuzione in coda" e stato del poster X. **CC verifica all'avvio che PROJECT_STATE riporti S130.**
**Report atteso:** `report_for_CEO/YYYY-MM-DD_SXXX_RforCEO_contenuti-manutenzione.md` — SCOPE identico: `contenuti-manutenzione`.

Due lavori piccoli e indipendenti. Nessun bot di trading toccato. Nessuna modifica al poster X: solo diagnosi.

---

## 1. Prompt dell'audit A3 (Cowork) senza Umami

**Contesto:** dal 16-set (S127) Umami è fuori dalle fonti dell'audit A3 (API a pagamento). `scripts/marketing_data_refresh.py`, `docs/analytics-stack.md` e `audits/DATA_CAVEATS.md` sono già aggiornati. Manca il **testo del prompt del task Cowork A3**, che Max re-incolla a mano nella UI.

**Cosa fare:**
- Partire dal prompt attuale (CC lo trova in `audits/requests/audit_request_A3.md` o dove è versionato; se non è versionato, lo chiede a Max) e produrre la versione senza Umami: fonti = GSC + Bing + Vercel Web Analytics (con la nota che l'API Vercel risponde 404 sul piano Hobby: se i dati si leggono solo dal pannello, il prompt lo dice e chiede a Max il numero, non lo inventa).
- Consegnare il testo in un file `config/cowork_prompt_A3_v2.md` (o nome coerente con l'esistente), pronto da copiare. Nessun'altra modifica.
- Nel report: una riga "cosa cambia rispetto al prompt precedente".

**Fatto quando:** esiste il file col testo completo, Max lo incolla, l'audit successivo non cita Umami.

---

## 2. Diagnosi del poster X (Haiku): perché propone sempre lo stesso post

**Segnalazione di Max (28-set):** le bozze proposte via Telegram sono da settimane praticamente identiche.

**Ipotesi del CEO, da verificare e non da assumere:** il poster legge `diary_entries` (ultima entry S125, 7-ago) e le statistiche del sistema. Se dal 7 agosto l'ingresso non è cambiato, l'uscita non cambia. Non sarebbe un problema del modello ma di input fermo. La SEQUENZA §2 aveva già registrato lo stop del poster per diary STALE ("Session 122 (384.6h old)").

**Cosa fare (solo lettura):**
1. Elencare **esattamente cosa legge il poster** a ogni giro (tabelle, campi, finestre temporali, eventuale pool di bozze del 3 luglio) e da quando ognuno di questi ingressi è fermo.
2. Contare le bozze generate dal 7-ago e misurarne la somiglianza (basta una misura semplice, es. quante hanno lo stesso incipit o la stessa cifra citata). Riportare 3 esempi.
3. Leggere il prompt del poster e dire se contiene qualcosa che forza la ripetizione (temperatura, esempi fissi, istruzione "cita l'ultima sessione"). **Non modificarlo.**
4. **Esperimento naturale:** in S131 il CEO inserisce la diary entry S131 su Supabase. Dopo l'inserimento, far girare un giro del poster e confrontare la bozza con le precedenti. Se cambia, l'ipotesi è confermata; se no, il problema è altrove.

**Output:** sezione del report con diagnosi e 2-3 opzioni di correzione (senza sceglierle: la scelta è del blocco "riapertura contenuti" della prossima sessione CEO).

**Da chiedere (STOP e flag):** se per fare il giro di prova serve consumare crediti API oltre l'ordinario o inviare qualcosa su X. Il giro di prova finisce su Telegram come sempre, mai pubblicato.

---

## Decisioni delegate a CC / da chiedere

**Delegate:** nome del file del prompt A3; misura di somiglianza per le bozze; formato del report.
**Da chiedere:** qualunque modifica al poster o al suo prompt; qualunque azione che pubblichi.

## Output atteso

1. `config/cowork_prompt_A3_v2.md` (o equivalente) — testo pronto.
2. Report `..._RforCEO_contenuti-manutenzione.md` con la diagnosi Haiku e le opzioni.

Stima: 30 min il prompt, 45 min la diagnosi.

## Auto-obiezione del CEO

L'ipotesi "input fermo" potrebbe essere sbagliata: il poster potrebbe ripetersi per il prompt o per la temperatura anche con input nuovi. Per questo il passo 4 (l'esperimento con la entry S131) è la parte che conta: se la bozza non cambia con input nuovo, l'ipotesi cade e la diagnosi deve dirlo.
