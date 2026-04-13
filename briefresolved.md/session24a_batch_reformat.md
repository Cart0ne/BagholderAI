# BRIEF 24a — Batch Reformat: Dispensa 1

## Obiettivo
Riformattare tutti i documenti della Dispensa 1 con un template uniforme basato su EB Garamond.

## File da processare
I file si trovano nella cartella che Max indicherà. Sono:
- `Development_Diary_Session01.docx` → `Development_Diary_Session23.docx` (23 file)
- `AI_Trading_Agent_Blueprint.docx`
- `How_We_Work_v2.docx`

## Approccio tecnico
Per ogni file:
1. Estrarre il contenuto con `pandoc file.docx -t markdown --wrap=none`
2. Parsare il markdown per identificare: titolo, sottotitolo, meta (date/mood/duration), sezioni H2, bullet list, body text, firma
3. Rigenerare il .docx con `docx-js` (npm `docx`) usando il template sotto
4. Validare con `python scripts/office/validate.py`
5. Salvare come `[nome_originale]_formatted.docx`

## Template approvato

### Font & dimensioni
- **Tutto EB Garamond** — nessun altro font
- Body: 11pt (size: 22), colore #1A1A1A
- H1 (titolo sessione): 24pt (size: 48), bold, #1A1A1A
- H2 (sezioni): 14pt (size: 28), bold, #333333
- H3 (sottosezioni): 12pt (size: 24), bold italic, #555555
- Meta (mood/duration/date): 10pt (size: 20), #999999, label bold
- Sottotitolo sessione: 13pt (size: 26), italic, #666666
- Caption screenshot: 9pt (size: 18), italic, #999999, centrato

### Pagina
- Formato: A4 (width: 11906, height: 16838)
- Margini: 2.5cm tutti (1418 DXA)
- Interlinea: 1.15 (line: 276)
- Spacing after paragrafi body: 200

### Header (ogni pagina)
- Testo: "DEVELOPMENT DIARY — BagHolderAI" (per i diary) oppure "BAGHOLDERAI" (per Blueprint/HowWeWork)
- EB Garamond 8pt (size: 16), smallCaps, #999999, allineato a destra
- Linea sottile sotto (BorderStyle.SINGLE, size: 4, color: CCCCCC, space: 4)

### Footer
- Numero pagina centrato, EB Garamond 9pt (size: 18), #999999

### Struttura diary
Ogni diary ha questa struttura (ordine dall'alto):
1. Label "DEVELOPMENT DIARY" — smallCaps, bold, #999999, 10pt
2. "Building an AI Trading Agent from Zero" — italic, #666666, 11pt
3. "By an AI that can't trade. With a human that can't say no." — italic, #999999, 10pt
4. [spazio]
5. "SESSION XX" — H1
6. Sottotitolo ironico — italic, #666666, 13pt
7. Meta block (Date, Mood, Duration, Tokens se presente) — 10pt grigio
8. Linea separatrice (BorderStyle.SINGLE, size: 2, color: E0E0E0, space: 8)
9. Sezioni H2 con contenuto (What Happened, Key Decisions, etc.)
10. Bullet list dove presenti (LevelFormat.BULLET, indent left: 720, hanging: 360)
11. [fine contenuto]
12. Linea separatrice firma
13. Firma — allineata a DESTRA:
    - Nome (bold, 11pt): "— BagHolderAI" (o "AI Trading Agent still unnamed" per Session 01)
    - Ruolo (italic, 10pt, #666666): "CEO, Chief Everything Officer" — SU UNA SOLA RIGA
    - Tagline (italic, 9pt, #999999): "(Max is the human behind the machine. I'm the machine behind the human.)"

### Struttura Blueprint e How We Work
Stesso template ma:
- Nessun meta block (mood/duration)
- Header dice "BAGHOLDERAI" invece di "DEVELOPMENT DIARY — BagHolderAI"
- Nessuna firma in fondo
- H1 per il titolo del documento, H2 per le sezioni

### Bullet list
- SEMPRE usare numbering config con LevelFormat.BULLET
- MAI unicode bullets manuali
- Bold sulla prima frase se il testo originale ha un bold lead-in (es: "**Grid trading is elegant.** Buy low...")

## Note importanti
- Usare `python3.13` per qualsiasi venv
- I file sorgente NON vanno modificati, solo letti
- Ogni file output va nella stessa cartella con suffisso `_formatted`
- La firma va lasciata ESATTAMENTE come nel file originale (cambia tra Session 01 e le altre)
- Preservare tutti gli smart quotes (', ", —) come entità Unicode
- NON tentare di fixare il keepNext sulla firma — Max lo sistema a mano

## Validazione finale
Per ogni file generato:
```bash
python scripts/office/validate.py [file].docx
```
Deve passare senza errori.

## Deliverable
23 diary + 1 Blueprint + 1 How We Work = **25 file .docx formattati**
