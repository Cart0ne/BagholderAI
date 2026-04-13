# BRIEF 24b — Fix: Aggiungere stili Word ai file formattati

## Problema
I 24 file formattati hanno la formattazione visiva corretta (font, dimensioni, colori) ma NON usano gli stili built-in di Word (Heading 1, Heading 2, etc.). Senza stili:
- Il sommario automatico (TOC) non funziona
- La navigazione nel pannello laterale di Word non funziona
- Modifiche future richiedono intervento manuale paragrafo per paragrafo

## Fix richiesto
Aggiornare `reformat_batch.py` per assegnare gli stili Word built-in ai paragrafi appropriati, OLTRE alla formattazione visiva già applicata.

## Mapping stili

| Contenuto | Stile Word | Esempio |
|-----------|-----------|---------|
| Titolo sessione ("SESSION XX") | Heading 1 | SESSION 01 |
| Sezioni ("What Happened", "Key Decisions"...) | Heading 2 | What Happened |
| Sottosezioni (se presenti) | Heading 3 | The Grid Strategy |
| Tutto il resto | Normal | (body text, meta, firma) |

## Come fare in python-docx
```python
# Assegnare stile a un paragrafo
paragraph.style = document.styles['Heading 1']

# Lo stile va assegnato PRIMA della formattazione custom
# perché lo stile resetta il formatting. Quindi:
# 1. Assegna stile
# 2. Poi sovrascrivi font/size/color come già fai
```

## Scope
- Rieseguire il formatter su tutti i 24 file già processati
- Rivalidare tutti con validate.py
- Sovrascrivere i `_formatted.docx` esistenti

## NON fare
- Non toccare nient'altro
- Non cambiare la formattazione visiva (è già approvata)
- Non aggiungere il Blueprint (lo faremo dopo la traduzione)
