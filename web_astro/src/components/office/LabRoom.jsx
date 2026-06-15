/* ============================================================
   /office "The AI Lab" — animated HQ scene (React island).
   Ported from the design handoff (config/bagholderAI dashboard.zip →
   lab-room.jsx). Faithful port: inline styles + CSS keyframes kept
   verbatim. Only the DATA SLOTS are wired to real live data via the
   same canonical layer used by /home, /grid, /dashboard:
     - Board: net worth + per-coin P&L% + sparkline (computeCanonicalState)
     - Sentinel monitor: real risk_score
     - Grid monitor: real net realized P&L
   Loaded via client:visible from src/pages/office.astro.
   ============================================================ */
import React, { useState, useEffect } from "react";
import { computeCanonicalState, fetchLivePrices } from "../../lib/pnl-canonical";

// Design tokens (from brain-cards-shared.jsx; mirror of refactor/theme.css).
const BH = {
  bg: '#D7E0CA', surface: '#FFFFFF', panel: '#E9EEDF', hover: '#F4F7EE',
  border: '#D2DCC4', borderSoft: '#DFE4D5',
  text: '#283026', dim: '#455041', muted: '#59634F',
  primary: '#3F7589', primarySoft: '#D6E5EC',
  pos: '#4E8A57', posSoft: '#DCEAD3', neg: '#BC4032', negSoft: '#F2DAD4',
  neu: '#2F7E91', neuSoft: '#D2E6EA', warn: '#B79029', warnSoft: '#F2E9CC',
  sentinel: '#4E8198', sentinelSoft: '#D5E6EE', sherpa: '#BC4032', sherpaSoft: '#F2DAD4',
  news: '#6E68B0', newsSoft: '#E2E0F2',
  mono: '"JetBrains Mono", monospace', sans: '"Inter", sans-serif',
  display: '"Bricolage Grotesque", sans-serif', shadowSm: '0 6px 16px rgba(74,118,140,0.12)',
};

// Shared animation keyframes (from office-shared.jsx).
const OFFICE_KEYFRAMES = `
@keyframes bhBob { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-3px)} }
@keyframes bhStep { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-4px) rotate(2deg)} }
@keyframes bhTicker { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
@keyframes bhPulse { 0%,100%{opacity:1} 50%{opacity:0.35} }
@keyframes bhSteam {
  0%{opacity:0;transform:translateY(0) scale(.55)}
  25%{opacity:.65} 70%{opacity:.3}
  100%{opacity:0;transform:translateY(-24px) scale(1.2)}
}
@keyframes bhSpin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }
@keyframes bhFloatY { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
@keyframes bhGlow { 0%,100%{opacity:.5} 50%{opacity:.85} }
`;
function OfficeStyle() { return <style>{OFFICE_KEYFRAMES}</style>; }

/* ── live data layer — same anon key + canonical engine as dashboard-live.ts
   (anon is public, RLS enforces read-only). Single source of truth so the
   board number matches /home and /dashboard exactly. ── */
const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";
const SB_HEADERS = { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` };
const CYCLE = "testnet_2";                       // S96a clean slate (bump on reset)
const CQ = `&cycle=eq.${CYCLE}`;
const GRID_INITIAL = 500, TF_INITIAL = 100, TOTAL_INITIAL = 600;

async function sbGet(path) {
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, { headers: SB_HEADERS });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}
async function sbGetAll(path) {                  // Range-header pagination (anon caps at 1000/page)
  const out = []; const PAGE = 1000;
  for (let from = 0; ; from += PAGE) {
    const r = await fetch(`${SB_URL}/rest/v1/${path}`, {
      headers: { ...SB_HEADERS, Range: `${from}-${from + PAGE - 1}` },
    });
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    const rows = await r.json();
    out.push(...rows);
    if (rows.length < PAGE) break;
  }
  return out;
}
const fmtUsd = (n) => `$${Math.abs(n).toFixed(2)}`;
const fmtSigned = (n) => `${n >= 0 ? '+' : '-'}${fmtUsd(n)}`;
const fmtPct = (n) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

// Sparkline polyline from a net-worth series, fit to a w×h viewBox.
function sparkPath(vals, w, h) {
  const pts = (vals || []).filter(Number.isFinite);
  if (pts.length < 2) return { pts: `2,${h / 2} ${w - 2},${h / 2}`, last: { x: w - 2, y: h / 2 } };
  const min = Math.min(...pts), max = Math.max(...pts), span = (max - min) || 1;
  const X = (i) => 2 + (i / (pts.length - 1)) * (w - 4);
  const Y = (v) => (h - 2) - ((v - min) / span) * (h - 6);
  const arr = pts.map((v, i) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`);
  const li = pts.length - 1;
  return { pts: arr.join(' '), last: { x: X(li), y: Y(pts[li]) } };
}

const EMPTY_LIVE = {
  ready: false, netWorthStr: '—', pctStr: '—', pctColor: BH.muted,
  coins: [], spark: [], risk: null, gridRealizedStr: '—',
};

// Fetches the real portfolio + risk every 60s and exposes the board/monitor slots.
function useOfficeData() {
  const [data, setData] = useState(EMPTY_LIVE);
  useEffect(() => {
    let alive = true;
    async function load() {
      try {
        const [trades, skimRows, sparkRows, sentRows] = await Promise.all([
          sbGetAll(`trades?select=symbol,side,amount,cost,fee,fee_asset,created_at,managed_by&config_version=eq.v3${CQ}&order=created_at.asc`),
          sbGet(`reserve_ledger?select=symbol,amount&config_version=eq.v3${CQ}`),
          sbGet(`daily_pnl?select=date,total_value&managed_by=eq.grid${CQ}&order=date.desc&limit=7`),
          sbGet(`sentinel_scores?select=risk_score&score_type=eq.fast&order=created_at.desc&limit=1`),
        ]);
        const gridTrades = trades.filter((t) => t.managed_by === 'grid');
        const tfTrades = trades.filter((t) => t.managed_by === 'tf' || t.managed_by === 'tf_grid');
        const gridSyms = new Set(gridTrades.map((t) => t.symbol));
        const tfSyms = new Set(tfTrades.map((t) => t.symbol));
        const gridSkim = (skimRows || []).reduce((s, r) => gridSyms.has(r.symbol) ? s + Number(r.amount || 0) : s, 0);
        const tfSkim = (skimRows || []).reduce((s, r) => tfSyms.has(r.symbol) ? s + Number(r.amount || 0) : s, 0);
        const prices = await fetchLivePrices([...gridSyms, ...tfSyms]);
        const grid = computeCanonicalState(gridTrades, gridSkim, prices, GRID_INITIAL);
        const tf = computeCanonicalState(tfTrades, tfSkim, prices, TF_INITIAL);
        const netWorth = grid.netWorth + tf.netWorth;
        const totalPnl = grid.totalPnL + tf.totalPnL;
        const totalPct = (totalPnl / TOTAL_INITIAL) * 100;
        const order = { 'BTC/USDT': 0, 'SOL/USDT': 1, 'BONK/USDT': 2 };
        const coins = (grid.perCoin || [])
          .slice()
          .sort((a, b) => (order[a.symbol] ?? 9) - (order[b.symbol] ?? 9))
          .map((c) => ({ sym: c.symbol.replace('/USDT', ''), pct: c.unrealizedPct }));
        const spark = (sparkRows || []).map((r) => Number(r.total_value)).reverse().filter(Number.isFinite);
        const risk = (sentRows && sentRows[0] && sentRows[0].risk_score != null)
          ? Math.round(Number(sentRows[0].risk_score)) : null;
        if (!alive) return;
        setData({
          ready: true,
          netWorthStr: fmtUsd(netWorth),
          pctStr: fmtPct(totalPct),
          pctColor: totalPnl >= 0 ? BH.pos : BH.neg,
          coins, spark, risk,
          gridRealizedStr: fmtSigned(grid.netRealized),
        });
      } catch (e) {
        console.warn('[office] live data failed:', e);
      }
    }
    load();
    const id = setInterval(load, 60000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  return data;
}

// Mockup 5 — "The AI Lab", CENTRAL one-point perspective (NOT isometric).
// STEP 1 — empty room only: the architectural shell + daylight. The projection
// "contract": a single vanishing point; every plane (floor, back wall, ceiling,
// two side walls) derives from it. Later steps drop furniture/characters onto the
// floor by ground coordinates and scale them by depth — no hand-tuned pixels.

const ROOM = (() => {
  const W = 1040, H = 730;
  const VP = { x: 520, y: 231 };   // vanishing point (lower horizon → more floor)
  const sx = 0.577, sy = 0.48;     // horizontal / vertical back-wall scale → back wall ≈ 600×350
  const toBack = (x, y) => ({ x: VP.x + sx * (x - VP.x), y: VP.y + sy * (y - VP.y) });
  const f = { tl: { x: 0, y: 0 }, tr: { x: W, y: 0 }, bl: { x: 0, y: H }, br: { x: W, y: H } };
  const b = { tl: toBack(0, 0), tr: toBack(W, 0), bl: toBack(0, H), br: toBack(W, H) };
  // a point on a side wall: side 'L'|'R', t = front→back (0..1), v = top→bottom (0..1)
  const wallPt = (side, t, v) => {
    const A = side === 'L' ? f.tl : f.tr;
    const B = side === 'L' ? b.tl : b.tr;
    const C = side === 'L' ? b.bl : b.br;
    const D = side === 'L' ? f.bl : f.br;
    const top = { x: A.x + t * (B.x - A.x), y: A.y + t * (B.y - A.y) };
    const bot = { x: D.x + t * (C.x - D.x), y: D.y + t * (C.y - D.y) };
    return { x: top.x + v * (bot.x - top.x), y: top.y + v * (bot.y - top.y) };
  };
  return { W, H, VP, f, b, wallPt };   // (handoff returned a stray `s` that was never defined)
})();

// ── per-bot monitor screen contents (frontal, facing the viewer) ──
function ScrCandles() {
  const bars = [[10, 18, 1], [6, 24, 0], [14, 12, 1], [8, 22, 1], [16, 10, 0], [7, 20, 1]];
  return <svg viewBox="0 0 70 40" style={{ width: '100%', height: '100%' }}>{bars.map(([t, h, up], i) => { const c = up ? BH.pos : BH.neg; return <g key={i}><line x1={6 + i * 11} y1={t - 3} x2={6 + i * 11} y2={t + h + 3} stroke={c} strokeWidth="1" /><rect x={3 + i * 11} y={t} width="6" height={h} rx="1" fill={c} /></g>; })}</svg>;
}
function ScrLadder() {
  const rows = [['#BC4032', 74], ['#BC4032', 56], ['#59634F', 44], ['#4E8A57', 38], ['#4E8A57', 24]];
  return <div style={{ padding: '4px 6px', height: '100%', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 3 }}>{rows.map(([c, w], i) => (<div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ width: 3, height: 3, borderRadius: 9, background: c }} /><span style={{ flex: 1, height: 3, background: '#2b332e', borderRadius: 2, position: 'relative', overflow: 'hidden' }}><span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${w}%`, background: c, opacity: 0.75, borderRadius: 2 }} /></span></div>))}</div>;
}
function ScrEquity({ accent, value }) {
  return <div style={{ height: '100%', padding: '4px 6px', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}><div style={{ fontFamily: BH.mono, fontSize: 5.5, letterSpacing: '0.08em', color: '#8FA08C' }}>NET REALIZED</div><svg viewBox="0 0 70 24" style={{ width: '100%', flex: 1 }}><polyline points="2,21 14,17 26,19 38,11 50,13 62,5 68,3" fill="none" stroke={accent} strokeWidth="1.4" strokeLinejoin="round" /></svg><div style={{ fontFamily: BH.display, fontWeight: 800, fontSize: 11, color: '#fff', lineHeight: 1 }}>{value ?? '—'}</div></div>;
}
function ScrRadar({ accent }) {
  return <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><div style={{ width: '74%', height: '74%', borderRadius: '50%', border: `1px solid ${accent}80`, position: 'relative', overflow: 'hidden' }}><div style={{ position: 'absolute', inset: '24%', borderRadius: '50%', border: `1px solid ${accent}55` }} /><div style={{ position: 'absolute', left: '50%', top: '50%', width: '50%', height: 1, background: `linear-gradient(90deg,${accent},transparent)`, transformOrigin: '0 0', animation: 'bhSpin 3s linear infinite' }} /><div style={{ position: 'absolute', left: '70%', top: '34%', width: 3, height: 3, borderRadius: 9, background: accent }} /></div></div>;
}
function ScrTrend({ accent }) {
  return <svg viewBox="0 0 70 40" style={{ width: '100%', height: '100%' }}><polyline points="2,30 12,24 22,27 34,16 44,20 56,9 68,12" fill="none" stroke={accent} strokeWidth="1.6" strokeLinejoin="round" /><circle cx="68" cy="12" r="2" fill={accent} /></svg>;
}
function ScrNews() {
  return <div style={{ padding: '4px 5px', height: '100%', boxSizing: 'border-box', overflow: 'hidden' }}><div style={{ fontFamily: BH.mono, fontSize: 5.5, fontWeight: 700, letterSpacing: '0.1em', color: BH.news, marginBottom: 3 }}>NEWS FEED</div>{[BH.neg, BH.pos, BH.muted, BH.neg].map((c, i) => <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 3, marginBottom: 3 }}><span style={{ width: 3, height: 3, borderRadius: 9, background: c, flexShrink: 0 }} /><span style={{ height: 2.5, flex: 1, background: '#3a4641', borderRadius: 2, maxWidth: `${80 - i * 10}%` }} /></div>)}</div>;
}
function ScrShield({ accent, value }) {
  return <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}><svg width="20" height="24" viewBox="0 0 20 24"><path d="M10 1 19 4v7c0 6-4 9.5-9 12C5 20.5 1 17 1 11V4L10 1Z" fill={accent} /><path d="M6 11.5 9 14.5 14.5 8" stroke="#fff" strokeWidth="1.7" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg><div><div style={{ fontFamily: BH.mono, fontSize: 5.5, color: '#8FA08C' }}>RISK</div><div style={{ fontFamily: BH.display, fontWeight: 800, fontSize: 14, color: '#fff', lineHeight: 1 }}>{value ?? '—'}</div></div></div>;
}
function ScrParams() {
  return <div style={{ padding: '4px 6px', height: '100%', boxSizing: 'border-box', display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 4 }}>{[['grid', 72, BH.pos], ['step', 42, BH.warn], ['win', 58, BH.neu]].map(([l, v, c], i) => <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 4 }}><span style={{ fontFamily: BH.mono, fontSize: 5.5, color: '#8FA08C', width: 14 }}>{l}</span><span style={{ flex: 1, height: 3, background: '#2b332e', borderRadius: 2, overflow: 'hidden' }}><span style={{ display: 'block', height: '100%', width: `${v}%`, background: c, borderRadius: 2 }} /></span></div>)}</div>;
}

function LabMonitor({ w = 42, h = 34, accent, children }) {
  return (
    <div style={{ flexShrink: 0 }}>
      <div style={{ width: w, background: '#2A332E', borderRadius: 5, padding: 3, boxShadow: `0 4px 9px rgba(40,48,38,0.18), 0 0 11px ${accent}44` }}>
        <div style={{ height: h, background: '#141A17', borderTop: `2px solid ${accent}`, borderRadius: 3, overflow: 'hidden', boxShadow: `inset 0 0 10px ${accent}30` }}>{children}</div>
      </div>
      <div style={{ width: 4, height: 5, background: '#AEB6A6', margin: '0 auto' }} />
      <div style={{ width: 16, height: 3, background: '#99A38E', borderRadius: 2, margin: '0 auto' }} />
    </div>
  );
}

// Frontal workstation: 3/4 desk with the monitors on the top (facing the viewer),
// bot standing IN FRONT to one side, feet planted. Desk width adapts to the
// number of screens so 1-monitor stations stay compact. Bubble: top | left | right.
const STATION_FEET = 0.855;   // fraction of the bot image height where the feet sit
function LabStation({ x, baseY, scale = 1, accent, name, task, botSrc, screens = [], mirror, bubble = 'top', deskAngle, alarm, bubbleScale = 1, roamTo, roamAnim = 'bhRoam', roamFlip = 'bhRoamFlip', roamDur = 13, bubbleAnim, bubbleDur = 22, flash, href }) {
  const n = screens.length;
  const monW = n >= 3 ? 44 : 54, monH = n >= 3 ? 32 : 40;
  const monitorsW = n * monW + (n - 1) * 5;
  const deskW = monitorsW + 40;
  const imgW = 122, imgH = 164, overlap = 16;
  const boxW = imgW - overlap + deskW;
  const boxH = 230, floorY = boxH - 24, deskTopY = floorY - 64;
  const botCxN = imgW / 2, deskCxN = imgW - overlap + deskW / 2;
  const botCx = mirror ? boxW - botCxN : botCxN;
  const deskCx = mirror ? boxW - deskCxN : deskCxN;
  const botTop = floorY - STATION_FEET * imgH;
  const homeScreenX = x + (botCx - boxW / 2) * scale;          // bot's resting screen-x
  const roamDX = roamTo != null ? (roamTo - homeScreenX) / scale : 0;
  const bub = (
    <div style={{ position: 'relative', background: '#FFFFFF', border: `1px solid ${BH.border}`, borderLeft: `3px solid ${accent}`, borderRadius: 10, boxShadow: '0 6px 14px rgba(70,66,52,0.13)', padding: '5px 9px', width: 116, animation: 'bhFloatY 4.6s ease-in-out infinite' }}>
      <div style={{ fontFamily: BH.mono, fontSize: 7, fontWeight: 700, letterSpacing: '0.13em', textTransform: 'uppercase', color: accent, marginBottom: 1 }}>{name}</div>
      <div style={{ fontFamily: BH.sans, fontSize: 10, lineHeight: 1.3, color: BH.dim }}>{task}</div>
      {bubble === 'top' && <div style={{ position: 'absolute', bottom: -5, left: '50%', marginLeft: -4, width: 9, height: 9, background: '#FFFFFF', borderRight: `1px solid ${BH.border}`, borderBottom: `1px solid ${BH.border}`, transform: 'rotate(45deg)' }} />}
    </div>
  );
  const monBlockH = deskAngle ? 51 : (monH + 14);                  // monitor block height
  const monAnchorY = deskAngle ? (deskTopY - 2 + ((deskW / 2 + 6) * 0.5) * 0.28) : (deskTopY - 2);
  const monTopY = monAnchorY - monBlockH;                          // local y of the monitor's top edge
  let bubbleWrap;
  if (bubble === 'right') bubbleWrap = { left: botCx + imgW / 2 - 8, top: boxH - 176 };
  else if (bubble === 'left') bubbleWrap = { left: botCx - imgW / 2 - 122, top: boxH - 176 };
  else bubbleWrap = { left: deskCx, bottom: boxH - monTopY + 5, transform: `translateX(-50%) scale(${bubbleScale})`, transformOrigin: 'bottom center' };
  const Frame = href ? 'a' : 'div';
  return (
    <Frame href={href} className={href ? 'bh-click' : undefined} style={{ position: 'absolute', left: x, top: baseY, transform: `translate(-50%,-100%) scale(${scale})`, transformOrigin: 'bottom center', zIndex: Math.round(baseY), display: 'block', textDecoration: 'none' }}>
      <div style={{ position: 'relative', width: boxW, height: boxH, fontFamily: BH.sans }}>
        {/* contact shadow */}
        <div style={{ position: 'absolute', left: 18, top: floorY - 14, width: boxW - 36, height: 28, borderRadius: '50%', background: 'rgba(70,66,52,0.14)', filter: 'blur(7px)' }} />
        {deskAngle ? (() => {
          const hw = deskW / 2 + 6, hh = (deskW / 2 + 6) * 0.5, thick = 9, cyT = deskTopY - 2;
          const T = [deskCx, cyT - hh], R = [deskCx + hw, cyT], B = [deskCx, cyT + hh], L = [deskCx - hw, cyT];
          const legH = floorY - B[1];   // constant leg length → feet form a rhombus on the floor (iso)
          const face = (pts, bg, key, br) => <div key={key} style={{ position: 'absolute', inset: 0, width: boxW, height: boxH, clipPath: `polygon(${pts.map(p => p[0] + 'px ' + p[1] + 'px').join(',')})`, background: bg, boxShadow: br ? `inset 0 0 0 1px ${br}` : 'none' }} />;
          return (
            <React.Fragment>
              {/* back + side legs — drawn BEFORE the top so they sit behind it */}
              {[[T, 0], [L, 5], [R, -5]].map(([p, dx], i) => <div key={'lg' + i} style={{ position: 'absolute', left: p[0] - 3 + dx, top: p[1] - 1, width: 6, height: legH, background: '#C9C3B0', borderRadius: '0 0 2px 2px' }} />)}
              {/* desk edge thickness (two front faces) */}
              {face([L, B, [B[0], B[1] + thick], [L[0], L[1] + thick]], 'linear-gradient(180deg,#CFC9B6,#BDB7A3)', 'fl')}
              {face([B, R, [R[0], R[1] + thick], [B[0], B[1] + thick]], 'linear-gradient(180deg,#DCD6C4,#CAC4B1)', 'fr')}
              {/* rhombus top */}
              {face([T, R, B, L], 'linear-gradient(155deg,#F6F3EA,#E7E2D3)', 'tp', '#EBE6D8')}
              {/* front leg — drawn AFTER the top, in front */}
              <div style={{ position: 'absolute', left: B[0] - 3, top: B[1] - 1, width: 6, height: legH, background: '#BDB7A4', borderRadius: '0 0 2px 2px' }} />
              {/* contact pad under the monitor */}
              <div style={{ position: 'absolute', left: deskCx, top: cyT + 2, width: hw * 1.05, height: hh * 0.85, transform: 'translate(-50%,-50%)', borderRadius: '50%', background: 'rgba(70,66,52,0.05)' }} />
              {/* monitor — frontal, 16:9 */}
              <div style={{ position: 'absolute', left: deskCx, top: cyT + hh * 0.28, transform: 'translate(-50%,-100%)', transformOrigin: 'bottom center', filter: 'drop-shadow(0 4px 6px rgba(70,66,52,0.14))' }}>
                {alarm && (
                  <div style={{ position: 'absolute', right: '100%', top: '42%', transform: 'translateY(-50%)', marginRight: -2, width: 18, height: 16, zIndex: 2 }}>
                    {/* pulsing glow */}
                    <div style={{ position: 'absolute', left: -7, top: '50%', transform: 'translateY(-50%)', width: 30, height: 30, borderRadius: '50%', background: 'radial-gradient(circle, rgba(188,64,50,0.55), transparent 66%)', animation: 'bhGlow 1.1s ease-in-out infinite' }} />
                    {/* mount bracket against the monitor edge */}
                    <div style={{ position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)', width: 4, height: 13, background: '#2A332E', borderRadius: '1px 0 0 1px' }} />
                    <div style={{ position: 'absolute', right: 3, top: '50%', transform: 'translateY(-50%)', width: 3, height: 9, background: '#46515b' }} />
                    {/* red siren dome bulging left */}
                    <div style={{ position: 'absolute', right: 5, top: '50%', transform: 'translateY(-50%)', width: 12, height: 13, borderRadius: '62% 38% 38% 62% / 50%', background: 'radial-gradient(circle at 34% 34%, #F1A99D, #BC4032 72%)', boxShadow: '0 0 6px rgba(188,64,50,0.6)', animation: 'bhPulse 0.85s ease-in-out infinite' }} />
                    {/* glossy highlight */}
                    <div style={{ position: 'absolute', right: 12, top: '34%', width: 3, height: 3, borderRadius: '50%', background: 'rgba(255,255,255,0.75)' }} />
                  </div>
                )}
                <LabMonitor accent={accent} w={66} h={37}>{screens[0]}</LabMonitor>
              </div>
            </React.Fragment>
          );
        })() : (
          <React.Fragment>
            {/* desk top surface (3/4, receding) */}
            <div style={{ position: 'absolute', left: deskCx - deskW / 2, top: deskTopY - 26, width: deskW, height: 30, background: 'linear-gradient(180deg,#F4F1E8,#E6E1D2)', clipPath: 'polygon(8% 100%, 92% 100%, 80% 0%, 20% 0%)', borderTop: '1px solid #F7F5EE' }} />
            {/* desk front apron */}
            <div style={{ position: 'absolute', left: deskCx - deskW / 2 + 8, top: deskTopY, width: deskW - 16, height: 15, background: 'linear-gradient(180deg,#E3DECF,#D2CCB9)', borderRadius: '0 0 3px 3px', boxShadow: '0 5px 9px rgba(70,66,52,0.10)' }} />
            {/* legs */}
            <div style={{ position: 'absolute', left: deskCx - deskW / 2 + 12, top: deskTopY + 15, width: 8, height: floorY - deskTopY - 15, background: '#C9C3B0', borderRadius: '0 0 2px 2px' }} />
            <div style={{ position: 'absolute', left: deskCx + deskW / 2 - 20, top: deskTopY + 15, width: 8, height: floorY - deskTopY - 15, background: '#C9C3B0', borderRadius: '0 0 2px 2px' }} />
            {/* monitors on the desk, facing the viewer */}
            <div style={{ position: 'absolute', left: deskCx, transform: 'translateX(-50%)', bottom: boxH - deskTopY + 2, display: 'flex', alignItems: 'flex-end', gap: 5 }}>
              {screens.map((s, i) => <LabMonitor key={i} accent={accent} w={monW} h={monH}>{s}</LabMonitor>)}
            </div>
          </React.Fragment>
        )}
        {/* send/receive flash over the monitor */}
        {flash && <div style={{ position: 'absolute', left: deskCx, top: monTopY - 4, width: deskW + 10, height: monBlockH + 8, transform: 'translateX(-50%)', borderRadius: 6, background: `radial-gradient(ellipse at 50% 45%, ${accent}, transparent 72%)`, opacity: 0, animation: `${flash} 22s linear infinite`, mixBlendMode: 'screen', zIndex: 4, pointerEvents: 'none' }} />}
        {/* bot — either resting, or roaming to a colleague and back */}
        {roamTo != null ? (
          <div style={{ position: 'absolute', left: botCx, top: botTop, width: imgW, height: imgH, marginLeft: -imgW / 2, zIndex: 6, '--roam': `${roamDX}px`, animation: `${roamAnim} ${roamDur}s ease-in-out infinite`, filter: 'drop-shadow(0 6px 8px rgba(70,66,52,0.16))' }}>
            <div style={{ width: '100%', height: '100%', animation: `${roamFlip} ${roamDur}s ease-in-out infinite` }}>
              <img src={botSrc} alt={name} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', animation: 'bhRoamStep 0.5s ease-in-out infinite' }} />
            </div>
          </div>
        ) : (
          <div style={{ position: 'absolute', left: botCx, top: botTop, width: imgW, height: imgH, marginLeft: -imgW / 2, zIndex: 5, transformOrigin: 'bottom center', animation: 'bhBreathe 4.2s ease-in-out infinite', filter: 'drop-shadow(0 6px 8px rgba(70,66,52,0.16))' }}>
            <img src={botSrc} alt={name} style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', transform: mirror ? 'scaleX(-1)' : 'none' }} />
          </div>
        )}
        {/* speech bubble */}
        {task && <div style={{ position: 'absolute', ...bubbleWrap, zIndex: 6, ...(bubbleAnim ? { animation: `${bubbleAnim} ${bubbleDur}s linear infinite` } : {}) }}>{bub}</div>}
      </div>
    </Frame>
  );
}

// ── environment props (frontal cutouts, depth-scaled, depth-sorted) ──────────
function Prop({ x, y, scale = 1, zi, shadowW = 40, children }) {
  return (
    <div style={{ position: 'absolute', left: x, top: y, transform: `translate(-50%,-100%) scale(${scale})`, transformOrigin: 'bottom center', zIndex: zi || Math.round(y) }}>
      <div style={{ position: 'absolute', left: '50%', bottom: -5, width: shadowW, height: shadowW * 0.32, transform: 'translateX(-50%)', borderRadius: '50%', background: 'rgba(70,66,52,0.16)', filter: 'blur(4px)' }} />
      {children}
    </div>
  );
}
function PlantProp(p) {
  return <Prop {...p} shadowW={46}><div style={{ position: 'relative', width: 54, height: 74 }}>
    <div style={{ position: 'absolute', left: 6, bottom: 26, width: 18, height: 42, background: '#5E8A54', borderRadius: '50% 50% 48% 52%', transform: 'rotate(-17deg)' }} />
    <div style={{ position: 'absolute', left: 30, bottom: 26, width: 18, height: 42, background: '#7FA873', borderRadius: '48% 52% 50% 50%', transform: 'rotate(17deg)' }} />
    <div style={{ position: 'absolute', left: 17, bottom: 30, width: 20, height: 48, background: '#6F9B64', borderRadius: '52% 48% 50% 50%' }} />
    <div style={{ position: 'absolute', left: 11, bottom: 0, width: 32, height: 32, background: 'linear-gradient(180deg,#CE926A,#A96B43)', clipPath: 'polygon(10% 0,90% 0,82% 100%,18% 100%)', borderRadius: '3px 3px 5px 5px' }} />
  </div></Prop>;
}
function ServerRackProp(p) {
  return <Prop {...p} shadowW={58}><div style={{ position: 'relative', width: 54, height: 150, background: 'linear-gradient(180deg,#D3DBE0,#B4BEC6)', borderRadius: 4, border: '1px solid #C2CBD2', boxShadow: '0 6px 14px rgba(40,60,70,0.14)', overflow: 'hidden' }}>
    {[0, 1, 2, 3, 4, 5, 6, 7, 8].map(i => <div key={i} style={{ position: 'absolute', left: 6, right: 6, top: 6 + i * 16, height: 12, background: '#222B30', borderRadius: 2, display: 'flex', alignItems: 'center', gap: 3, paddingLeft: 4 }}>
      <span style={{ width: 3, height: 3, borderRadius: 9, background: BH.pos, animation: `bhPulse ${0.9 + i * 0.27}s ease-in-out infinite` }} />
      <span style={{ width: 3, height: 3, borderRadius: 9, background: i % 2 ? BH.warn : BH.neu, animation: `bhPulse ${1.3 + i * 0.2}s ease-in-out infinite` }} />
      <span style={{ width: 14, height: 2, borderRadius: 2, background: '#3a4651' }} />
    </div>)}
  </div></Prop>;
}
function SirenProp(p) {
  return <Prop {...p} shadowW={20}><div style={{ position: 'relative', width: 22, height: 42 }}>
    <div style={{ position: 'absolute', left: '50%', bottom: 18, width: 36, height: 36, transform: 'translateX(-50%)', borderRadius: '50%', background: 'radial-gradient(circle, rgba(188,64,50,0.5), transparent 68%)', animation: 'bhGlow 1.3s ease-in-out infinite' }} />
    <div style={{ position: 'absolute', left: '50%', bottom: 0, width: 4, height: 20, transform: 'translateX(-50%)', background: '#9097a0' }} />
    <div style={{ position: 'absolute', left: '50%', bottom: 16, width: 20, height: 7, transform: 'translateX(-50%)', background: '#2A332E', borderRadius: 2 }} />
    <div style={{ position: 'absolute', left: '50%', bottom: 21, width: 16, height: 15, transform: 'translateX(-50%)', background: 'radial-gradient(circle at 40% 28%, #E78A7E, #BC4032)', borderRadius: '50% 50% 38% 38%', animation: 'bhPulse 1.0s ease-in-out infinite' }} />
  </div></Prop>;
}
function MugProp(p) {
  const steam = p.steam || 1;
  return <Prop {...p} shadowW={16}><div style={{ position: 'relative', width: 18, height: 22 }}>
    {[0, 1, 2].map(i => <div key={i} style={{ position: 'absolute', left: 3 + i * 4.5, top: -5, width: 3.2 * steam, height: 4.5 * steam, borderRadius: '60% 60% 50% 50%', background: 'rgba(255,255,255,0.92)', filter: 'blur(0.4px)', opacity: 0, animation: `bhSteam 2.4s ease-out ${i * 0.55}s infinite` }} />)}
    <div style={{ position: 'absolute', left: 1, bottom: 0, width: 13, height: 14, background: '#FFFFFF', border: `1px solid ${BH.border}`, borderRadius: '2px 2px 4px 4px' }}><div style={{ position: 'absolute', top: 2, left: 2, right: 2, height: 3, background: '#7a5a3e', borderRadius: 1 }} /></div>
    <div style={{ position: 'absolute', left: 13, bottom: 3, width: 4, height: 6, border: `1.5px solid ${BH.border}`, borderLeft: 'none', borderRadius: '0 4px 4px 0' }} />
  </div></Prop>;
}
function BoxesProp(p) {
  return <Prop {...p} shadowW={50}><div style={{ position: 'relative', width: 56, height: 52 }}>
    <div style={{ position: 'absolute', left: 4, bottom: 0, width: 46, height: 30, background: 'linear-gradient(180deg,#DBB57F,#C29A60)', borderRadius: 2 }}><div style={{ position: 'absolute', top: '46%', left: 0, right: 0, height: 3, background: 'rgba(120,90,50,0.32)' }} /><div style={{ position: 'absolute', top: 0, bottom: 0, left: '50%', width: 3, marginLeft: -1.5, background: 'rgba(120,90,50,0.22)' }} /></div>
    <div style={{ position: 'absolute', left: 18, bottom: 28, width: 34, height: 24, background: 'linear-gradient(180deg,#E4C18E,#CDA46A)', borderRadius: 2 }}><div style={{ position: 'absolute', top: '46%', left: 0, right: 0, height: 2.5, background: 'rgba(120,90,50,0.28)' }} /></div>
  </div></Prop>;
}

function LabRoom() {
  const { W, H, VP, f, b, wallPt } = ROOM;
  // live Rome time for the wall clock
  const [now, setNow] = React.useState(() => new Date());
  React.useEffect(() => { const id = setInterval(() => setNow(new Date()), 30000); return () => clearInterval(id); }, []);
  const live = useOfficeData();   // real net worth / coins / sparkline / risk / grid realized
  const rome = new Date(now.toLocaleString('en-US', { timeZone: 'Europe/Rome' }));
  const clockH = (rome.getHours() % 12) * 30 + rome.getMinutes() * 0.5;
  const clockM = rome.getMinutes() * 6;
  const poly = (pts) => `polygon(${pts.map(p => `${p.x}px ${p.y}px`).join(',')})`;
  const plane = { position: 'absolute', inset: 0, width: W, height: H };

  // ── floor perspective grid (very subtle) ──
  const gridLines = [];
  for (let i = 0; i <= 8; i++) {
    const xf = (i / 8) * W;
    const back = { x: 0.5 * xf + b.bl.x, y: b.bl.y };   // where the line hits the back-floor edge
    gridLines.push(<line key={'d' + i} x1={xf} y1={H} x2={back.x} y2={back.y} />);
  }
  [0.18, 0.4, 0.64, 0.9].forEach((tt, i) => {
    const y = H + tt * (b.bl.y - H);
    const k = (H - y) / (H - b.bl.y);                   // 0 at front … 1 at back
    const lx = k * b.bl.x, rx = W - k * b.bl.x;
    gridLines.push(<line key={'h' + i} x1={lx} y1={y} x2={rx} y2={y} />);
  });

  // ── side window quad (perspective rectangle on a side wall) ──
  const windowQuad = (side) => [
    wallPt(side, 0.30, 0.20), wallPt(side, 0.95, 0.26),
    wallPt(side, 0.95, 0.74), wallPt(side, 0.30, 0.80),
  ];
  const mullions = (side) => [0.46, 0.62, 0.78].map((t, i) => {
    const a = wallPt(side, t, side === 'L' ? 0.20 + (t - 0.30) * (0.06 / 0.65) : 0.20 + (t - 0.30) * (0.06 / 0.65));
    const top = wallPt(side, t, 0.20 + (t - 0.30) * (0.06 / 0.65));
    const bot = wallPt(side, t, 0.80 - (t - 0.30) * (0.06 / 0.65));
    return <line key={i} x1={top.x} y1={top.y} x2={bot.x} y2={bot.y} stroke="#FBFCF8" strokeWidth="3" opacity="0.85" />;
  });

  // ── the company board, mounted high on the back wall ──
  // S106a: enlarged 1.18× (origin top-center) for readability + nudged up to
  // 124 to keep clearance from the CEO podium below. The bhBoardFlash halo
  // (search bhBoardFlash) is scaled/positioned in lockstep so it stays framed.
  const Board = () => (
    <div style={{ position: 'absolute', left: VP.x, top: 124, width: 300, transform: 'translateX(-50%) scale(1.18)', transformOrigin: 'center top', zIndex: 8 }}>
      <div style={{ position: 'absolute', inset: '6px -6px -10px -6px', background: 'rgba(70,66,52,0.10)', filter: 'blur(8px)', borderRadius: 12 }} />
      <a className="bh-board-link" href="/dashboard" style={{ position: 'relative', display: 'block', textDecoration: 'none', background: '#FFFFFF', border: `1px solid ${BH.border}`, borderRadius: 12, boxShadow: BH.shadowSm, padding: 7 }}>
        <div style={{ background: '#FCFDFB', border: `1px solid ${BH.borderSoft}`, borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', borderBottom: `1px solid ${BH.borderSoft}`, background: BH.hover }}>
            <span style={{ fontFamily: BH.mono, fontSize: 9, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: BH.primary }}>Portfolio Overview</span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontFamily: BH.mono, fontSize: 7, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: BH.pos }}><span style={{ width: 5, height: 5, borderRadius: 99, background: live.ready ? BH.pos : BH.muted, animation: 'bhPulse 1.8s ease-in-out infinite' }} />live</span>
          </div>
          <div style={{ display: 'flex', gap: 10, padding: '8px 11px 4px' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: BH.mono, fontSize: 6.5, letterSpacing: '0.12em', textTransform: 'uppercase', color: BH.muted, marginBottom: 4 }}>Net worth · live</div>
              {(() => {
                const sp = sparkPath(live.spark, 150, 56);
                const col = live.ready ? live.pctColor : BH.muted;
                return (
                  <svg viewBox="0 0 150 56" style={{ width: '100%', height: 56, display: 'block' }}>
                    <polyline points={sp.pts} fill="none" stroke={col} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
                    <circle cx={sp.last.x} cy={sp.last.y} r="2.4" fill={col} />
                  </svg>
                );
              })()}
            </div>
            <div style={{ width: 86, display: 'flex', flexDirection: 'column', gap: 4, paddingTop: 2 }}>
              {[
                ...live.coins.map((c) => ({ k: c.sym, v: fmtPct(c.pct), color: c.pct >= 0 ? BH.pos : BH.neg })),
                { k: 'TOTAL', v: live.pctStr, color: live.pctColor, total: true },
              ].map((row) => (
                <div key={row.k} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: row.total ? `1px solid ${BH.borderSoft}` : 'none', paddingTop: row.total ? 4 : 0 }}>
                  <span style={{ fontFamily: BH.mono, fontSize: 7.5, fontWeight: row.total ? 700 : 500, color: row.total ? BH.text : BH.muted }}>{row.k}</span>
                  <span style={{ fontFamily: BH.mono, fontSize: 8, fontWeight: 700, color: row.color }}>{row.v}</span>
                </div>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 7, padding: '0 11px 9px' }}>
            <span style={{ fontFamily: BH.display, fontWeight: 800, fontSize: 19, color: BH.text }}>{live.netWorthStr}</span>
            <span style={{ fontFamily: BH.mono, fontSize: 8.5, fontWeight: 700, color: live.pctColor }}>{live.pctStr}</span>
          </div>
        </div>
      </a>
    </div>
  );

  // ── the CEO podium: low round museum pedestal, Bag standing on top ──
  const Podium = () => {
    const cx = VP.x, cy = 480;          // top-surface ellipse centre (on the floor, against the back wall)
    const rx = 70, ry = 18, bodyH = 24;
    return (
      <div style={{ position: 'absolute', left: 0, top: 0, zIndex: 520 }}>
        {/* contact shadow on the floor */}
        <div style={{ position: 'absolute', left: cx - rx - 14, top: cy + bodyH - ry, width: (rx + 14) * 2, height: ry * 2 + 10, borderRadius: '50%', background: 'rgba(70,66,52,0.16)', filter: 'blur(7px)' }} />
        {/* soft brand glow ring around the base */}
        <div style={{ position: 'absolute', left: cx - rx - 10, top: cy + bodyH - ry - 8, width: (rx + 10) * 2, height: (ry + 8) * 2, borderRadius: '50%', border: `2px solid ${BH.primary}`, opacity: 0.5, boxShadow: `0 0 22px 3px ${BH.primary}55`, animation: 'bhGlow 3.2s ease-in-out infinite' }} />
        {/* cylinder body */}
        <div style={{ position: 'absolute', left: cx - rx, top: cy, width: rx * 2, height: bodyH, background: 'linear-gradient(180deg,#E4DFCF,#CFC9B4)' }} />
        <div style={{ position: 'absolute', left: cx - rx, top: cy + bodyH - ry, width: rx * 2, height: ry * 2, borderRadius: '50%', background: '#CFC9B4' }} />
        {/* top surface */}
        <div style={{ position: 'absolute', left: cx - rx, top: cy - ry, width: rx * 2, height: ry * 2, borderRadius: '50%', background: 'radial-gradient(ellipse at 50% 38%, #F6F3E9, #E5E0D0)', border: '1px solid #D6D0BD' }} />
        {/* Bag, the CEO — standing on the pedestal */}
        <a className="bh-click" href="/howwework" style={{ position: 'absolute', left: cx, top: cy - ry - 124, width: 130, height: 130, marginLeft: -65, display: 'block' }}>
          <img src="/office/backpack-sky-40.svg" alt="Bag, the CEO" style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', animation: 'bhBob 3.6s ease-in-out infinite', filter: 'drop-shadow(0 12px 14px rgba(70,66,52,0.22))' }} />
        </a>
        {/* CEO label floating above */}
        <div style={{ position: 'absolute', left: cx, top: cy - ry - 142, transform: 'translateX(-50%)', display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: BH.mono, fontSize: 8.5, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase', color: BH.primary, background: 'rgba(255,255,255,0.92)', border: `1px solid ${BH.primary}55`, borderRadius: 99, padding: '3px 10px', whiteSpace: 'nowrap', boxShadow: '0 3px 9px rgba(70,66,52,0.14)', zIndex: 2 }}>
          <span style={{ width: 5, height: 5, borderRadius: 99, background: BH.pos, animation: 'bhPulse 1.5s ease-in-out infinite' }} />CEO active
        </div>
      </div>
    );
  };

  // ── pendant lamps (cord + dome + soft pool of light) ──
  const Lamp = ({ x, y, scale = 1 }) => (
    <div style={{ position: 'absolute', left: x, top: 0, width: 0, height: 0, zIndex: 6 }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width: 1.5, height: y, background: '#C9C7BB', transform: 'translateX(-50%)' }} />
      <div style={{ position: 'absolute', left: 0, top: y, width: 46 * scale, height: 22 * scale, transform: 'translate(-50%,-2px)', background: 'linear-gradient(180deg,#FBFBF6,#E6E5DC)', borderRadius: '50% 50% 46% 46% / 80% 80% 40% 40%', boxShadow: '0 6px 14px rgba(60,60,50,0.12)' }} />
      <div style={{ position: 'absolute', left: 0, top: y + 14 * scale, width: 80 * scale, height: 80 * scale, transform: 'translate(-50%,0)', background: 'radial-gradient(ellipse at 50% 0%, rgba(255,247,220,0.55), transparent 70%)', pointerEvents: 'none' }} />
    </div>
  );

  return (
    <div className="office-scene" style={{ position: 'relative', width: W, height: 630, background: '#D7E0CA', fontFamily: BH.sans }}>
      <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', background: '#EDEBE2', WebkitMaskImage: 'linear-gradient(to right, transparent 0, #000 34px, #000 calc(100% - 34px), transparent 100%), linear-gradient(to bottom, transparent 0, #000 30px, #000 calc(100% - 30px), transparent 100%)', WebkitMaskComposite: 'source-in', maskImage: 'linear-gradient(to right, transparent 0, #000 34px, #000 calc(100% - 34px), transparent 100%), linear-gradient(to bottom, transparent 0, #000 30px, #000 calc(100% - 30px), transparent 100%)', maskComposite: 'intersect' }}>
      <div style={{ position: 'absolute', left: 0, top: -50, width: W, height: H }}>
      <OfficeStyle />
      <style>{`
        @keyframes bhRoam { 0%,15%{transform:translateX(0)} 38%,60%{transform:translateX(var(--roam))} 83%,100%{transform:translateX(0)} }
        @keyframes bhRoamFlip { 0%,60%{transform:scaleX(-1)} 64%,96%{transform:scaleX(1)} 100%{transform:scaleX(-1)} }
        @keyframes bhRoamStep { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(-3px) rotate(1.5deg)} }
        @keyframes bhRoamNK { 0%,5%{transform:translateX(0)} 18%,30%{transform:translateX(var(--roam))} 43%,100%{transform:translateX(0)} }
        @keyframes bhFlipNK { 0%,30%{transform:scaleX(1)} 32%,43%{transform:scaleX(-1)} 45%,100%{transform:scaleX(1)} }
        @keyframes bhRoamSEN { 0%,31%{transform:translate(0,0)} 33%{transform:translate(0,-12px)} 34.5%{transform:translate(0,0)} 36%{transform:translate(0,-7px)} 37.5%,50%{transform:translate(0,0)} 60%,72%{transform:translate(var(--roam),0)} 85%,100%{transform:translate(0,0)} }
        @keyframes bhFlipSEN { 0%,72%{transform:scaleX(1)} 74%,85%{transform:scaleX(-1)} 87%,100%{transform:scaleX(1)} }
        @keyframes bhBubTF { 0%,12%{opacity:1} 16%,82%{opacity:0} 86%,100%{opacity:1} }
        @keyframes bhBubGRID { 0%,35%{opacity:1} 38%,60%{opacity:0} 63%,100%{opacity:1} }
        @keyframes bhBubNK { 0%,3%{opacity:1} 7%,41%{opacity:0} 45%,100%{opacity:1} }
        @keyframes bhBubSEN { 0%,16%{opacity:1} 18%,30%{opacity:0} 32%,48%{opacity:1} 50%,85%{opacity:0} 87%,100%{opacity:1} }
        @keyframes bhBubSHE { 0%,58%{opacity:1} 60%,72%{opacity:0} 74%,100%{opacity:1} }
        @keyframes bhBreathe { 0%,100%{transform:scaleY(1)} 50%{transform:scaleY(1.02)} }
        .bh-board-link { transition: transform .18s ease, box-shadow .18s ease; }
        .bh-board-link:hover { transform: translateY(-3px); box-shadow: 0 14px 30px rgba(40,60,70,0.22); }
        .bh-click { cursor: pointer; transition: filter .15s ease; }
        .bh-click:hover { filter: brightness(1.06); }
        @media (prefers-reduced-motion: reduce) {
          .office-scene *, .office-scene *::before, .office-scene *::after { animation: none !important; }
        }
        @keyframes bhFlashSend { 0%,84%{opacity:0} 86.5%{opacity:0.8} 90%,100%{opacity:0} }
        @keyframes bhFlashRecv { 0%,97%{opacity:0} 99.3%{opacity:0.85} 100%{opacity:0} }
        @keyframes bhTypingDot { 0%,70%,100%{opacity:0.3; transform:translateY(0)} 35%{opacity:1; transform:translateY(-2px)} }
        @keyframes bhBriefGRID { 0%,39%{opacity:0} 42%,57%{opacity:1} 60%,100%{opacity:0} }
        @keyframes bhBriefSEN { 0%,17%{opacity:0} 20%,29%{opacity:1} 31%,100%{opacity:0} }
        @keyframes bhBriefSHE { 0%,59%{opacity:0} 62%,71%{opacity:1} 73%,100%{opacity:0} }
        @keyframes bhHeadline {
          0%,49%{opacity:0; transform:translate(0,0) rotate(-8deg) scale(1)}
          50%{opacity:1; transform:translate(0,0) rotate(-8deg) scale(1)}
          53%{opacity:1; transform:translate(95px,-200px) rotate(3deg) scale(0.92)}
          56%{opacity:1; transform:translate(195px,-320px) rotate(9deg) scale(0.84)}
          59%{opacity:1; transform:translate(270px,-340px) rotate(5deg) scale(0.8)}
          61%,100%{opacity:0; transform:translate(270px,-340px) rotate(5deg) scale(0.8)}
        }
        @keyframes bhBoardFlash { 0%,58.5%{opacity:0} 60.5%{opacity:0.7} 64%,100%{opacity:0} }
        @keyframes bhAlertGlow { 0%,29%{opacity:0} 31%{opacity:0.9} 34%{opacity:0.45} 37%{opacity:0.8} 44%,100%{opacity:0} }
        @keyframes bhAlertChip { 0%,36%{opacity:0; transform:translate(-50%,-100%) scale(0.6)} 38%{opacity:1; transform:translate(-50%,-100%) scale(1)} 45%{opacity:1; transform:translate(-50%,-100%) scale(1)} 47%,100%{opacity:0; transform:translate(-50%,-100%) scale(1)} }
        @keyframes bhPlane {
          0%,86%{opacity:0; transform:translate(0,0) rotate(0deg) scale(1)}
          87%{opacity:1; transform:translate(0,0) rotate(0deg) scale(1)}
          88.25%{opacity:1; transform:translate(-47px,-93px) rotate(47deg) scale(0.97)}
          89.5%{opacity:1; transform:translate(-93px,-178px) rotate(94deg) scale(0.94)}
          90.75%{opacity:1; transform:translate(-140px,-249px) rotate(141deg) scale(0.92)}
          92%{opacity:1; transform:translate(-187px,-298px) rotate(188deg) scale(0.89)}
          93.25%{opacity:1; transform:translate(-234px,-324px) rotate(235deg) scale(0.86)}
          94.5%{opacity:1; transform:translate(-280px,-324px) rotate(282deg) scale(0.83)}
          95.75%{opacity:1; transform:translate(-327px,-300px) rotate(329deg) scale(0.8)}
          97%{opacity:1; transform:translate(-374px,-255px) rotate(376deg) scale(0.78)}
          98.25%{opacity:1; transform:translate(-420px,-195px) rotate(423deg) scale(0.75)}
          99.5%{opacity:1; transform:translate(-467px,-128px) rotate(470deg) scale(0.72)}
          100%{opacity:0; transform:translate(-467px,-128px) rotate(470deg) scale(0.72)}
        }
      `}</style>

      {/* BACK WALL (far plane) */}
      <div style={{ position: 'absolute', left: b.tl.x, top: b.tl.y, width: b.tr.x - b.tl.x, height: b.bl.y - b.tl.y, background: 'linear-gradient(180deg,#F4F2EA,#ECE9DE)', boxShadow: 'inset 0 0 80px rgba(120,116,98,0.07)' }} />

      {/* CEILING */}
      <div style={{ ...plane, clipPath: poly([f.tl, f.tr, b.tr, b.tl]), background: 'linear-gradient(180deg,#F8F8F3,#EEEDE6)' }} />

      {/* FLOOR */}
      <div style={{ ...plane, clipPath: poly([f.bl, f.br, b.br, b.bl]), background: 'linear-gradient(180deg,#E0DBCC 0%,#E9E5D8 40%,#EFEBDF 100%)' }} />
      <svg width={W} height={H} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        <g stroke="#7A6F4F" strokeWidth="1" opacity="0.06">{gridLines}</g>
      </svg>

      {/* SIDE WALLS */}
      <div style={{ ...plane, clipPath: poly([f.tl, b.tl, b.bl, f.bl]), background: 'linear-gradient(90deg,#E6E3D8,#EFEDE4)' }} />
      <div style={{ ...plane, clipPath: poly([f.tr, b.tr, b.br, f.br]), background: 'linear-gradient(270deg,#E6E3D8,#EFEDE4)' }} />

      {/* WINDOWS — daylight + distant skyscraper skyline on the side walls */}
      {['L', 'R'].map(side => {
        const x0 = side === 'L' ? 60 : 825, x1 = side === 'L' ? 215 : 980;
        const baseY = 548, minTop = 286, hs = [0.5, 0.82, 0.38, 0.95, 0.6, 0.78, 0.46, 0.88, 0.55, 0.7, 0.42, 0.9];
        const rects = []; let x = x0 - 8, i = 0;
        while (x < x1 + 8) {
          const w = 11 + (i % 3) * 6, h = (baseY - minTop) * hs[i % hs.length], top = baseY - h;
          rects.push(<rect key={'b' + i} x={x} y={top} width={w} height={h + 70} fill={i % 2 ? '#A6BACE' : '#94AAC4'} opacity="0.5" />);
          for (let r = 0; r < 4; r++) { const ly = top + 10 + r * 13; if (ly < baseY) rects.push(<rect key={'w' + i + '_' + r} x={x + 3} y={ly} width={3} height={3} fill="#EAF2FA" opacity="0.55" />); }
          x += w + 5; i++;
        }
        return (
          <div key={side} style={{ ...plane, clipPath: poly(windowQuad(side)), background: 'linear-gradient(180deg,#EAF3FB 0%,#DCEBF6 45%,#CFE2F1 100%)', boxShadow: 'inset 0 0 30px rgba(150,190,220,0.4)' }}>
            <svg width={W} height={H} style={{ position: 'absolute', inset: 0 }}>{rects}</svg>
          </div>
        );
      })}
      <svg width={W} height={H} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        {mullions('L')}{mullions('R')}
      </svg>
      {/* daylight bleed into the room */}
      <div style={{ position: 'absolute', left: 70, top: 150, width: 240, height: 360, background: 'radial-gradient(ellipse at 0% 40%, rgba(220,236,248,0.5), transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', right: 70, top: 150, width: 240, height: 360, background: 'radial-gradient(ellipse at 100% 40%, rgba(220,236,248,0.5), transparent 70%)', pointerEvents: 'none' }} />

      {/* ARCHITECTURAL SEAMS (give the box solidity) */}
      <svg width={W} height={H} style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
        <g stroke="#CFCBBC" strokeWidth="1.5" fill="none" opacity="0.9">
          {/* vertical wall corners */}
          <line x1={b.tl.x} y1={b.tl.y} x2={b.bl.x} y2={b.bl.y} />
          <line x1={b.tr.x} y1={b.tr.y} x2={b.br.x} y2={b.br.y} />
          {/* wall/ceiling */}
          <line x1={b.tl.x} y1={b.tl.y} x2={b.tr.x} y2={b.tr.y} />
        </g>
        {/* baseboard where walls meet the floor */}
        <g stroke="#C6C1B0" strokeWidth="4" fill="none" strokeLinecap="round">
          <line x1={b.bl.x} y1={b.bl.y} x2={b.br.x} y2={b.br.y} />
          <line x1={f.bl.x} y1={f.bl.y} x2={b.bl.x} y2={b.bl.y} opacity="0.7" />
          <line x1={f.br.x} y1={f.br.y} x2={b.br.x} y2={b.br.y} opacity="0.7" />
        </g>
      </svg>

      {/* PENDANT LAMPS */}
      <Lamp x={VP.x} y={98} scale={0.8} />
      <Lamp x={300} y={72} scale={1.05} />
      <Lamp x={740} y={72} scale={1.05} />

      {/* soft ceiling light cones — longer/stronger at the sides, wide & soft over the board */}
      {[[300, 88, 30, 168, 360, 0.34], [740, 88, 30, 168, 360, 0.34], [520, 104, 50, 250, 286, 0.2]].map(([cx, ct, tw, bw, ch, it], i) => (
        <div key={'cone' + i} style={{ position: 'absolute', left: 0, top: 0, width: W, height: H, clipPath: `polygon(${cx - tw / 2}px ${ct}px, ${cx + tw / 2}px ${ct}px, ${cx + bw / 2}px ${ct + ch}px, ${cx - bw / 2}px ${ct + ch}px)`, background: `linear-gradient(180deg, rgba(255,238,176,${it}) 0%, rgba(255,240,190,${it * 0.5}) 45%, transparent 100%)`, mixBlendMode: 'screen', pointerEvents: 'none', zIndex: 3 }} />
      ))}

      {/* board on the back wall + CEO podium (against the wall) */}
      <Board />
      <Podium />
      {/* steaming coffee on the CEO podium */}
      <MugProp x={560} y={487} scale={1.6} steam={1.7} zi={540} />

      {/* STEP 4 — the five workstations around the CEO (horseshoe) */}
      {/* back row — small & far */}
      <LabStation x={300} baseY={510} scale={0.62} accent={BH.pos} name="GRID" task="Executing range orders" href="#"
        botSrc="/office/grid-bot.svg" bubbleScale={1.35} bubbleAnim="bhBubGRID" bubbleDur={13} flash="bhFlashRecv" screens={[<ScrCandles />, <ScrLadder />, <ScrEquity accent={BH.pos} value={live.gridRealizedStr} />]} />
      <LabStation x={744} baseY={510} scale={0.62} mirror accent={BH.warn} name="TRENDFOLLOWER" task="Scanning the market…" href="#"
        botSrc="/office/trend-follower.svg" bubbleScale={1.35} roamTo={318} bubbleAnim="bhBubTF" bubbleDur={13} screens={[<ScrRadar accent={BH.warn} />, <ScrTrend accent={BH.warn} />]} />
      {/* front row — large & near */}
      <LabStation x={186} baseY={666} scale={0.9} accent={BH.news} name="NEWSKEEPER" task="Reading the latest news" href="#"
        botSrc="/office/newskeeper.svg" screens={[<ScrNews />]} deskAngle roamTo={430} roamAnim="bhRoamNK" roamFlip="bhFlipNK" roamDur={22} bubbleAnim="bhBubNK" />
      <LabStation x={520} baseY={678} scale={0.9} accent={BH.sentinel} name="SENTINEL" task="Monitoring risk levels" href="#"
        botSrc="/office/sentinel.svg" screens={[<ScrShield accent={BH.sentinel} value={live.risk} />]} roamTo={800} roamAnim="bhRoamSEN" roamFlip="bhFlipSEN" roamDur={22} bubbleAnim="bhBubSEN" />
      <LabStation x={854} baseY={666} scale={0.9} mirror accent={BH.sherpa} name="SHERPA" task="Optimizing parameters" href="#"
        botSrc="/office/sherpa.svg" screens={[<ScrParams />]} deskAngle alarm bubbleAnim="bhBubSHE" flash="bhFlashSend" />

      {/* ── STEP 6 (start) — environment props, my taste ── */}
      {/* soft rug, front-centre */}
      <div style={{ position: 'absolute', left: 520, top: 598, width: 320, height: 96, transform: 'translate(-50%,-50%)', borderRadius: '50%', background: 'radial-gradient(ellipse at 50% 50%, rgba(63,117,137,0.12), rgba(63,117,137,0.05) 62%, transparent 74%)', border: '1.5px solid rgba(63,117,137,0.12)', zIndex: 2 }} />
      {/* wall clock */}
      <div style={{ position: 'absolute', left: 772, top: 196, width: 34, height: 34, borderRadius: '50%', background: '#FFFFFF', border: `2px solid ${BH.border}`, boxShadow: BH.shadowSm, zIndex: 8 }}>
        <div style={{ position: 'absolute', left: '50%', top: '50%', width: 2, height: 7, background: BH.text, transformOrigin: 'bottom', transform: `translate(-50%,-100%) rotate(${clockH}deg)`, borderRadius: 2 }} />
        <div style={{ position: 'absolute', left: '50%', top: '50%', width: 1.5, height: 11, background: BH.muted, transformOrigin: 'bottom', transform: `translate(-50%,-100%) rotate(${clockM}deg)`, borderRadius: 2 }} />
        <div style={{ position: 'absolute', left: '50%', top: '50%', width: 3, height: 3, background: BH.text, borderRadius: '50%', transform: 'translate(-50%,-50%)' }} />
      </div>
      {/* server racks behind the back-row monitors, filling the back wall */}
      <ServerRackProp x={268} y={486} scale={0.92} />
      <ServerRackProp x={800} y={480} scale={1.0} />
      {/* stacked boxes (startup vibe), back-left */}
      <BoxesProp x={400} y={528} scale={1.16} zi={560} />
      {/* potted plants */}
      <PlantProp x={62} y={666} scale={1.0} />
      <PlantProp x={628} y={662} scale={0.7} />
      <PlantProp x={636} y={506} scale={0.52} zi={590} />
      {/* coffee mugs on a couple of desks */}
      <MugProp x={372} y={458} scale={0.5} />
      <MugProp x={566} y={600} scale={0.6} />

      {/* Sherpa → GRID crumpled-paper message, after the Sentinel→Sherpa visit */}
      <div style={{ position: 'absolute', left: 795, top: 554, zIndex: 999, animation: 'bhPlane 22s linear infinite', willChange: 'transform, opacity', pointerEvents: 'none' }}>
        <div style={{ position: 'relative', width: 30, height: 29 }}>
          <div style={{ position: 'absolute', inset: 0, borderRadius: '52% 48% 50% 50% / 50% 52% 48% 50%', background: 'radial-gradient(circle at 38% 32%, #FBE6AE, #ECC766 58%, #DCA63F)', boxShadow: '0 5px 8px rgba(70,66,52,0.24), inset -4px -4px 7px rgba(150,110,40,0.22)' }} />
          <svg viewBox="0 0 48 46" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
            <g stroke="rgba(150,105,30,0.42)" strokeWidth="1.2" fill="none">
              <path d="M11 15 L22 22 L15 31" />
              <path d="M22 22 L34 16 L33 29 L22 22" />
              <path d="M15 31 L26 33 L33 29" />
              <path d="M22 22 L20 10" />
            </g>
          </svg>
        </div>
      </div>

      {/* shared "briefing" chips (dark, typing dots) — shown only during a meeting */}
      {[[285, 398, 'bhBriefGRID', 13], [457, 536, 'bhBriefSEN', 22], [845, 540, 'bhBriefSHE', 22]].map(([cx, cy, anim, dur]) => (
        <div key={anim} style={{ position: 'absolute', left: cx, top: cy, transform: 'translate(-50%,-100%)', zIndex: 850, opacity: 0, animation: `${anim} ${dur}s linear infinite`, pointerEvents: 'none' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: 'rgba(40,48,38,0.92)', borderRadius: 99, padding: '5px 10px', boxShadow: '0 5px 12px rgba(40,48,38,0.28)' }}>
            <span style={{ fontFamily: BH.mono, fontSize: 7.5, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#CFE0D2' }}>briefing</span>
            <span style={{ display: 'inline-flex', gap: 2.5 }}>{[0, 1, 2].map(i => <span key={i} style={{ width: 3.5, height: 3.5, borderRadius: 9, background: '#9FD3B0', animation: `bhTypingDot 1.2s ease-in-out ${i * 0.18}s infinite` }} />)}</span>
          </div>
        </div>
      ))}

      {/* NewsKeeper event — headline flies to the board, which flashes on receipt */}
      <div style={{ position: 'absolute', left: VP.x, top: 122, width: 304, height: 158, transform: 'translateX(-50%) scale(1.18)', transformOrigin: 'center top', borderRadius: 13, border: `2px solid ${BH.news}`, boxShadow: `0 0 22px 3px ${BH.news}`, opacity: 0, animation: 'bhBoardFlash 22s linear infinite', zIndex: 9, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', left: 234, top: 584, zIndex: 900, opacity: 0, animation: 'bhHeadline 22s linear infinite', pointerEvents: 'none' }}>
        <div style={{ background: '#FFFFFF', border: `1px solid ${BH.border}`, borderLeft: `3px solid ${BH.news}`, borderRadius: 7, boxShadow: '0 6px 14px rgba(70,66,52,0.18)', padding: '4px 7px', width: 96 }}>
          <div style={{ fontFamily: BH.mono, fontSize: 6.5, fontWeight: 700, letterSpacing: '0.12em', color: BH.news, marginBottom: 1 }}>NEWS</div>
          <div style={{ fontFamily: BH.sans, fontSize: 8, lineHeight: 1.2, color: BH.dim }}>SEC delays ETF vote</div>
        </div>
      </div>

      {/* risk-alert event — Sherpa siren burst + Sentinel startles + sends a RISK signal */}
      <div style={{ position: 'absolute', left: 792, top: 600, width: 64, height: 64, transform: 'translate(-50%,-50%)', borderRadius: '50%', background: `radial-gradient(circle, ${BH.neg}, transparent 66%)`, opacity: 0, animation: 'bhAlertGlow 22s linear infinite', mixBlendMode: 'screen', zIndex: 800, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', left: 492, top: 540, transform: 'translate(-50%,-100%)', opacity: 0, animation: 'bhAlertChip 22s linear infinite', zIndex: 850, pointerEvents: 'none' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, background: BH.neg, borderRadius: 99, padding: '4px 9px', boxShadow: `0 4px 12px ${BH.neg}66` }}>
          <span style={{ width: 0, height: 0, borderLeft: '4px solid transparent', borderRight: '4px solid transparent', borderBottom: '7px solid #fff' }} />
          <span style={{ fontFamily: BH.mono, fontSize: 7.5, fontWeight: 700, letterSpacing: '0.13em', color: '#fff' }}>RISK ALERT</span>
        </div>
      </div>

      {/* (wip marker removed) */}
      </div>
      </div>
    </div>
  );
}

export default LabRoom;
