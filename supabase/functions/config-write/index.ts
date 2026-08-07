/* config-write — il "portiere" delle scritture di configurazione (S125, 2026-08-07).
 *
 * PERCHE' ESISTE
 * Fino a oggi /grid e /tf scrivevano su bot_config direttamente dal browser con
 * la chiave `anon`, che e' pubblicata nel sorgente del sito. Il database aveva
 * una policy RLS `anon_update_bot_config` con condizione `true`: chiunque poteva
 * cambiare i parametri di bot che da oggi muovono denaro reale su Kraken. La
 * password di /grid e' un controllo lato browser — nasconde l'interfaccia, non
 * chiude la porta.
 *
 * Le policy di scrittura anonima sono state rimosse (migrazione
 * s125_close_anon_write_policies). Questa funzione e' la sola via rimasta.
 *
 * COSA FA IN PIU' DI UNA SEMPLICE SERRATURA
 * Siccome ogni modifica passa da un punto solo, quel punto puo' rifiutare anche
 * le sciocchezze, non solo gli sconosciuti. Un controllo nel browser non vale
 * niente (chiunque lo aggira); qui vale. Rifiuta:
 *   - valori fuori scala o non numerici (la virgola al posto del punto e' gia'
 *     normalizzata dal client, ma qui non ci fidiamo)
 *   - capital_per_trade piu' grande dell'allocazione
 *   - un'allocazione piu' piccola di quanto e' GIA' investito su quella moneta
 *     (mandarebbe la cassa disponibile in negativo)
 *   - un totale allocato oltre il tetto (MAX_TOTAL_ALLOCATION_USD, default 1000)
 *
 * SEGRETI (Dashboard -> Edge Functions -> Secrets)
 *   GRID_ADMIN_SECRET          obbligatorio. Impostato da Max, mai transitato in chat.
 *   MAX_TOTAL_ALLOCATION_USD   opzionale, default 1000.
 *
 * AMBITO
 * Solo `bot_config`. `trend_config` (~50 colonne, bot fermo da S125) rientra
 * quando rientra il Trend Follower: e' la stessa funzione con un'altra tabella
 * in allowlist, non un lavoro nuovo.
 */

const ALLOWED_ORIGIN = "https://bagholderai.lol";

const cors = {
  "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Vary": "Origin",
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });

/* Confronto a tempo costante: un confronto normale esce al primo carattere
 * diverso, e la differenza di tempo si misura. Qui il costo non dipende dal
 * punto in cui le due stringhe divergono. */
function secretsMatch(a: string, b: string): boolean {
  const ea = new TextEncoder().encode(a);
  const eb = new TextEncoder().encode(b);
  if (ea.length !== eb.length) return false;
  let diff = 0;
  for (let i = 0; i < ea.length; i++) diff |= ea[i] ^ eb[i];
  return diff === 0;
}

/* Campi scrivibili e intervalli ammessi. I limiti su dead_zone_hours e
 * stop_buy_unlock_hours NON sono inventati: rispecchiano i CHECK gia' presenti
 * a database (0<x<=168 e 0<=x<=168), cosi' il rifiuto arriva con un messaggio
 * leggibile invece che come errore SQL. */
const FIELDS: Record<string, { min: number; max: number; label: string }> = {
  capital_allocation:    { min: 1,    max: 5000, label: "Allocazione ($)" },
  capital_per_trade:     { min: 0.5,  max: 5000, label: "$ per operazione" },
  skim_pct:              { min: 0,    max: 100,  label: "Skim %" },
  buy_pct:               { min: 0.05, max: 50,   label: "Buy %" },
  sell_pct:              { min: 0.05, max: 50,   label: "Sell %" },
  profit_target_pct:     { min: 0,    max: 50,   label: "Min profit %" },
  idle_reentry_hours:    { min: 0,    max: 168,  label: "Idle re-entry (ore)" },
  stop_buy_drawdown_pct: { min: 0,    max: 100,  label: "Stop-buy drawdown %" },
  stop_buy_unlock_hours: { min: 0,    max: 168,  label: "Stop-buy unlock (ore)" },
  dead_zone_hours:       { min: 0.25, max: 168,  label: "Dead-zone (ore)" },
};

function serviceKey(): string {
  const legacy = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (legacy) return legacy;
  /* Formato nuovo: dizionario JSON di chiavi segrete. */
  try {
    const dict = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}");
    const first = Object.values(dict)[0];
    if (typeof first === "string") return first;
  } catch { /* cade nel controllo sotto */ }
  return "";
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ ok: false, error: "method not allowed" }, 405);

  const expected = Deno.env.get("GRID_ADMIN_SECRET") ?? "";
  const SB_URL = Deno.env.get("SUPABASE_URL") ?? "";
  const SB_KEY = serviceKey();
  if (!expected || !SB_URL || !SB_KEY) {
    return json({ ok: false, error: "function not configured" }, 500);
  }

  let body: {
    secret?: string;
    symbol?: string;
    changes?: Record<string, unknown>;
  };
  try {
    body = await req.json();
  } catch {
    return json({ ok: false, error: "malformed body" }, 400);
  }

  if (!secretsMatch(String(body.secret ?? ""), expected)) {
    /* Nessun dettaglio: non diciamo se manca, se e' corta o se e' sbagliata. */
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  const symbol = String(body.symbol ?? "").trim();
  if (!symbol) return json({ ok: false, error: "symbol mancante" }, 400);

  const changes = body.changes ?? {};
  const keys = Object.keys(changes);
  if (!keys.length) return json({ ok: false, error: "nessuna modifica" }, 400);

  /* 1 — campi ammessi e numeri validi */
  const clean: Record<string, number> = {};
  for (const k of keys) {
    const spec = FIELDS[k];
    if (!spec) return json({ ok: false, error: `campo non modificabile: ${k}` }, 400);
    const raw = changes[k];
    const n = typeof raw === "number" ? raw : Number(String(raw).replace(",", "."));
    if (!Number.isFinite(n)) {
      return json({ ok: false, error: `${spec.label}: "${raw}" non e' un numero` }, 400);
    }
    if (n < spec.min || n > spec.max) {
      return json({
        ok: false,
        error: `${spec.label}: ${n} fuori intervallo (${spec.min} … ${spec.max})`,
      }, 400);
    }
    clean[k] = n;
  }

  const sb = (path: string, init?: RequestInit) =>
    fetch(`${SB_URL}/rest/v1/${path}`, {
      ...init,
      headers: {
        apikey: SB_KEY,
        Authorization: `Bearer ${SB_KEY}`,
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });

  /* 2 — riga corrente: serve per i valori "prima" nel registro e per i
   *     controlli incrociati sui campi NON toccati da questa modifica. */
  const curRes = await sb(
    `bot_config?symbol=eq.${encodeURIComponent(symbol)}&select=*`,
  );
  if (!curRes.ok) return json({ ok: false, error: "lettura riga fallita" }, 502);
  const curRows = await curRes.json();
  const cur = Array.isArray(curRows) ? curRows[0] : null;
  if (!cur) return json({ ok: false, error: `riga inesistente: ${symbol}` }, 404);

  const after = { ...cur, ...clean };

  /* 3 — controlli incrociati, quelli che un campo da solo non puo' vedere */
  const alloc = Number(after.capital_allocation);
  const perTrade = Number(after.capital_per_trade);
  if (perTrade > alloc) {
    return json({
      ok: false,
      error: `$ per operazione (${perTrade}) piu' grande dell'allocazione (${alloc})`,
    }, 400);
  }

  if ("capital_allocation" in clean) {
    /* Quanto e' gia' dentro su questa moneta, in questo ciclo. Se l'allocazione
     * scende sotto, la cassa disponibile del bot va in negativo. */
    const tRes = await sb(
      `trades?symbol=eq.${encodeURIComponent(symbol)}` +
      `&cycle=eq.${encodeURIComponent(String(cur.cycle))}` +
      `&select=side,cost`,
    );
    if (tRes.ok) {
      const trades = await tRes.json() as { side: string; cost: string }[];
      const invested = trades.reduce(
        (s, t) => s + (t.side === "buy" ? Number(t.cost) : -Number(t.cost)), 0,
      );
      if (alloc < invested) {
        return json({
          ok: false,
          error: `allocazione ${alloc} sotto il gia' investito ` +
                 `${invested.toFixed(2)} su ${symbol}: la cassa andrebbe in negativo`,
        }, 400);
      }
    }

    /* Tetto complessivo. La funzione non puo' vedere il saldo Kraken (non ha —
     * e non deve avere — le chiavi dell'exchange), quindi il tetto e' un numero
     * dichiarato, alzabile dal pannello dei segreti. */
    const cap = Number(Deno.env.get("MAX_TOTAL_ALLOCATION_USD") ?? "1000");
    const aRes = await sb(
      "bot_config?is_active=eq.true&select=symbol,capital_allocation",
    );
    if (aRes.ok) {
      const rows = await aRes.json() as { symbol: string; capital_allocation: string }[];
      const total = rows.reduce(
        (s, r) => s + (r.symbol === symbol ? alloc : Number(r.capital_allocation)), 0,
      );
      if (total > cap) {
        return json({
          ok: false,
          error: `totale allocato ${total.toFixed(2)} oltre il tetto di ${cap}`,
        }, 400);
      }
    }
  }

  /* 4 — scrittura con la chiave vera */
  const upd = await sb(
    `bot_config?symbol=eq.${encodeURIComponent(symbol)}`,
    {
      method: "PATCH",
      headers: { Prefer: "return=representation" },
      body: JSON.stringify({ ...clean, updated_at: new Date().toISOString() }),
    },
  );
  if (!upd.ok) {
    return json({ ok: false, error: `scrittura fallita (${upd.status})` }, 502);
  }
  const updated = await upd.json();
  if (!Array.isArray(updated) || !updated.length) {
    return json({ ok: false, error: "nessuna riga aggiornata" }, 500);
  }

  /* 5 — registro. Ora e' una prova: prima chiunque poteva inserirci righe con
   *     la chiave pubblica, quindi non provava nulla. */
  const auditRows = Object.keys(clean).map((k) => ({
    symbol,
    parameter: k,
    old_value: cur[k] === null || cur[k] === undefined ? null : String(cur[k]),
    new_value: String(clean[k]),
    changed_by: "manual-ceo",
  }));
  let auditOk = true;
  try {
    const a = await sb("config_changes_log", {
      method: "POST",
      headers: { Prefer: "return=minimal" },
      body: JSON.stringify(auditRows),
    });
    auditOk = a.ok;
  } catch {
    auditOk = false;
  }

  return json({ ok: true, auditOk, row: updated[0] });
});
