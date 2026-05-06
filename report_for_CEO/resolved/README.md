# report_for_CEO/resolved/

Cartella per report storici la cui questione è **chiusa**: la feature è shipped e in produzione, oppure il problema sollevato è stato risolto da un commit successivo, oppure la decisione è stata presa e applicata.

Stesso pattern di `briefresolved.md/` per i brief: i file restano leggibili nel git history, ma escono dalla lista attiva.

**Quando spostare un report qui:**
- La feature/proposal descritta è in `bot_config` / live in produzione
- Il bug discusso è chiuso (commit di fix referenziato nel report o noto al CEO)
- La decisione richiesta è stata presa e applicata

**Quando NON spostare:**
- Il report è un'analisi di stato che potrebbe servire come baseline per confronti futuri (es. snapshot performance pre-feature)
- Il report ha sezioni TODO ancora aperte
- La discussione è in pausa ma non chiusa
