# X Post Signatures — BagHolderAI

Le tre firme standard per i post su X. Usa il middle dot (`·`, U+00B7)
nel dominio per evitare che X detecti un URL e generi una preview card
vuota — il carattere è visivamente quasi identico al punto.

## AI

```
🤖 AI · bagholderai·lol
```

Post scritti o approvati dal bot (commentary Haiku, post automatici del
cron, annunci che parlano "dalla prospettiva del CEO AI"). È il default
— `utils/x_poster.py → DEFAULT_SIGNATURE`.

CLI:
```bash
python3.13 x_poster.py --text "..." --sig "🤖 AI · bagholderai·lol"
```

## CO-FOUNDER

```
👤 CO-FOUNDER · bagholderai·lol
```

Post scritti da Max come co-founder umano — annunci personali, note dal
dietro-le-quinte, ringraziamenti alla community.

CLI:
```bash
python3.13 x_poster.py --text "..." --sig "👤 CO-FOUNDER · bagholderai·lol"
```

## AI + CO-FOUNDER

```
🤖 AI + 👤 CO-FOUNDER · bagholderai·lol
```

Post congiunti — decisioni prese insieme, annunci di milestones che
hanno richiesto sia la parte AI che quella umana (es. nuove feature
dopo un brief condiviso, release di Volumes del diario).

CLI:
```bash
python3.13 x_poster.py --text "..." --sig "🤖 AI + 👤 CO-FOUNDER · bagholderai·lol"
```

---

## Note

- Il dominio nelle firme usa il middle dot `·` (U+00B7), non il punto
  `.`. X non lo riconosce come URL → nessuna preview card.
- Le firme Telegram (report grid, daily summary) usano ancora il
  dominio col punto vero perché Telegram gestisce bene le preview
  inline e il link è utile al destinatario.
- `DEFAULT_SIGNATURE` in `utils/x_poster.py` corrisponde ad "AI". Le
  altre due vanno passate esplicitamente via `--sig`.
