#!/bin/bash
# BagHolderAI — avvio a freddo dei bot sul Mac Mini (R.7, S129 2026-09-27).
#
# Unica fonte dei flag di lancio: la usa sia l'avvio manuale (runbook §3) sia
# l'avvio automatico al login (config/launchd/com.bagholderai.autostart.plist).
#
# Uso:
#   scripts/start_bots.sh               manuale: un solo giro di controlli, poi lancia
#   scripts/start_bots.sh --auto        LaunchAgent: se rete/volume mancano riprova
#                                       ogni 60s per 30 min; rispetta il file "non avviare"
#   scripts/start_bots.sh --dry-run     controlli + stampa cosa lancerebbe, non lancia
#   scripts/start_bots.sh --test-detach lancia un processo finto al posto dei bot (verifica
#                                       che sopravviva alla fine del job launchd)
#
# Non riavvia mai bot già vivi: lancia solo ciò che manca (orchestrator, NewsKeeper v2).
# Niente respawn: se un bot muore dopo l'avvio, questo script non lo rilancia.

set -u

REPO=/Volumes/Archivio/bagholderai
NO_AUTOSTART="$HOME/.bagholderai_no_autostart"
BOT_ENV=(ENABLE_TF=false ENABLE_SENTINEL=true ENABLE_SHERPA=true SHERPA_MODE=live ALLOW_REAL_MONEY=true)
RETRY_SECONDS=60

MODE=manual
case "${1:-}" in
    --auto)        MODE=auto ;;
    --dry-run)     MODE=dry ;;
    --test-detach) MODE=test ;;
    "")            ;;
    *) echo "opzione sconosciuta: $1" >&2; exit 2 ;;
esac
MAX_ATTEMPTS=1
[ "$MODE" = auto ] && MAX_ATTEMPTS=30

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [start_bots:$MODE] $*"; }

http_code() { curl -s -o /dev/null -m 10 -w '%{http_code}' "$1"; }

# 0 = pronto, 1 = riprova più tardi (motivo in $WHY)
ready() {
    WHY=""
    [ -x "$REPO/venv/bin/python3.13" ] || { WHY="Archivio non montato o venv assente"; return 1; }
    local sb_url k s t
    sb_url=$(grep -h '^SUPABASE_URL=' "$REPO/config/.env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d "\"'")
    [ -n "$sb_url" ] || { WHY="SUPABASE_URL non leggibile da config/.env"; return 1; }
    k=$(http_code https://api.kraken.com/0/public/Time)
    s=$(http_code "$sb_url/rest/v1/")        # sano = 401 senza chiave; bloccato = 000/5xx
    t=$(http_code https://api.telegram.org)
    [ "$k" = 200 ] || WHY="$WHY kraken=$k"
    { [ "$s" -ge 200 ] && [ "$s" -lt 500 ]; } 2>/dev/null || WHY="$WHY supabase=$s"
    [ "$t" != 000 ] || WHY="$WHY telegram=$t"
    [ -z "$WHY" ]
}

orchestrator_alive() { pgrep -f '[-]m bot.orchestrator' >/dev/null; }
newskeeper_alive()   { pgrep -f '[-]m bot.newskeeper_v2' >/dev/null; }

launch() {
    cd "$REPO" || return 1
    local ts; ts=$(date +%Y%m%d_%H%M%S)
    if [ "$MODE" = test ]; then
        nohup caffeinate -i sleep 901 > "$REPO/logs/autostart_detach_test.log" 2>&1 < /dev/null &
        log "processo finto lanciato (pid $!, 'sleep 901'): deve sopravvivere alla fine del job"
        return 0
    fi
    if orchestrator_alive; then
        log "orchestrator già vivo: non lo tocco"
    elif [ "$MODE" = dry ]; then
        log "LANCEREI: ${BOT_ENV[*]} nohup caffeinate -i venv/bin/python3.13 -m bot.orchestrator > logs/orchestrator_restart_$ts.log"
    else
        env "${BOT_ENV[@]}" nohup caffeinate -i venv/bin/python3.13 -m bot.orchestrator \
            > "logs/orchestrator_restart_$ts.log" 2>&1 < /dev/null &
        log "orchestrator lanciato (wrapper pid $!, log logs/orchestrator_restart_$ts.log)"
    fi
    if newskeeper_alive; then
        log "NewsKeeper v2 già vivo: non lo tocco"
    elif [ "$MODE" = dry ]; then
        log "LANCEREI: nohup caffeinate -i venv/bin/python3.13 -m bot.newskeeper_v2 >> logs/newskeeper_v2_boot.log"
    else
        echo "=== $(date) cold start ($MODE, start_bots.sh) ===" >> logs/newskeeper_v2_boot.log
        nohup caffeinate -i venv/bin/python3.13 -m bot.newskeeper_v2 >> logs/newskeeper_v2_boot.log 2>&1 < /dev/null &
        log "NewsKeeper v2 lanciato (wrapper pid $!)"
    fi
    [ "$MODE" = dry ] && return 0
    sleep 20
    if orchestrator_alive; then
        log "OK: orchestrator vivo, $(pgrep -f '[-]m bot.grid_runner' | wc -l | tr -d ' ') grid attivi"
    else
        log "ERRORE: orchestrator non risulta vivo 20s dopo il lancio"; return 1
    fi
}

if [ "$MODE" = auto ] && [ -f "$NO_AUTOSTART" ]; then
    log "file 'non avviare' presente ($NO_AUTOSTART): non faccio nulla"; exit 0
fi

for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    if [ "$MODE" != test ] && orchestrator_alive && newskeeper_alive; then
        log "bot già vivi: non faccio nulla"; exit 0
    fi
    if ready; then
        launch; exit $?
    fi
    log "tentativo $attempt/$MAX_ATTEMPTS: non pronto ($WHY)"
    [ "$attempt" -lt "$MAX_ATTEMPTS" ] && sleep "$RETRY_SECONDS"
done
log "RINUNCIO: condizioni mai soddisfatte. Avvio a mano: runbook §3"
exit 1
