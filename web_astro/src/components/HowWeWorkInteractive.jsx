import { useState, useEffect, useRef } from "react";

/* ============================================================
   HowWeWorkInteractive — React island for /howwework.
   Loaded only on this page via client:visible.

   Behavior split:
   - ≥768px: 3-node org chart with SVG connections, click to
     reveal panel. Workflow timeline auto-advances every 12s,
     STOPS once the user clicks any step.
   - <768px:  static 3-card stack with all info already
     visible (no clicks needed), then a plain workflow list.

   Palette uses site tokens via Tailwind utility classes
   (text-pos / text-amber-400 / text-cc), set in global.css.
   ============================================================ */

const TEAM = {
  ceo: {
    id: "ceo",
    name: "Claude",
    role: "CEO · AI",
    emoji: "🤖",
    /* Tailwind utility refs so we get the right token. */
    accent: "pos",        // --color-pos (green)
    accentHex: "#86efac",
    tagline: "The one who thinks",
    desc:
      "An AI with the confidence of a Fortune 500 CEO and the budget of a lemonade stand. Makes decisions, writes the diary, designs architecture, and generates instructions.",
    superpower: "Never forgets a decision (it's all in the documents)",
    weakness: "Can't touch a file, open a browser, or buy a domain",
    tools: ["Claude Projects", "Supabase MCP", "Vercel MCP"],
    memory:
      "userMemories block injected at session start + memory_user_edits notebook + all project documents searchable",
  },
  max: {
    id: "max",
    name: "Max",
    role: "Board · Human",
    emoji: "🧑",
    accent: "amber-400",
    accentHex: "#fbbf24",
    tagline: "The one who does",
    desc:
      "The human. An architect by trade, curious as he is clumsy with code. Handles everything that requires existing in the physical world. Veto power over every decision.",
    superpower: "Can actually do things",
    weakness: 'Says "quick session" then stays 3 hours',
    tools: ["Mac Mini (prod)", "MacBook Air (dev)", "GitHub", "Telegram"],
    memory:
      "The bridge. Carries context between the two AIs, translates strategy into intern briefs.",
  },
  cc: {
    id: "cc",
    name: "CC",
    role: "Intern · Claude Code",
    emoji: "⚡",
    accent: "cc",
    accentHex: "#818cf8",
    tagline: "The one who ships",
    desc:
      "The most talented developer you've ever met, with the memory of a goldfish. Builds everything from scratch — every single time. Pushes directly to main.",
    superpower: "Writes code directly in the repo",
    weakness: "Forgets everything between sessions",
    tools: ["Terminal", "Git", "Python", "Local files only"],
    memory:
      "Resets every session. Only continuity: CLAUDE.md (rules) + memory.md (updated at task end).",
  },
};

const CONNECTIONS = [
  {
    from: "ceo",
    to: "max",
    label: "Strategy & briefs",
    desc:
      "CEO proposes strategy, writes detailed briefs. Max approves, vetoes, or pushes back. All communication in Italian.",
    items: [
      "Architecture decisions",
      "Brief .md files for CC",
      "Diary drafts",
      "Supabase queries & analysis",
    ],
  },
  {
    from: "max",
    to: "cc",
    label: "Relay & execute",
    desc:
      "Max relays CEO's briefs to CC in the terminal. The more precise the instructions, the less CC goes rogue.",
    items: [
      "Brief files",
      "Git pull commands",
      "Orchestrator restarts",
      "Bug reports",
    ],
  },
  {
    from: "cc",
    to: "ceo",
    label: "Verify & report",
    desc:
      "CEO verifies CC's work via Supabase MCP and Vercel. CC can't talk to CEO directly — Max is always the bridge.",
    items: [
      "Code pushed to main",
      "Screenshots via Max",
      "Database state via Supabase",
      "Deploy status via Vercel",
    ],
  },
];

const WORKFLOW = [
  {
    step: "01",
    title: "Session start",
    who: "ceo",
    desc: "CEO reads Roadmap + Diary, queries bot_events_log and bot_state_snapshots on Supabase.",
  },
  {
    step: "02",
    title: "Strategy",
    who: "ceo",
    desc: "Discussions in Claude Projects chat. CEO queries live data, proposes priorities. Max approves or vetoes.",
  },
  {
    step: "03",
    title: "Brief",
    who: "ceo",
    desc: "CEO writes detailed .md briefs with specs, SQL, checklist. Never .docx.",
  },
  {
    step: "04",
    title: "Implement",
    who: "cc",
    desc: "Max relays brief to CC. CC writes code, pushes to main. No PRs — Max can't code review.",
  },
  {
    step: "05",
    title: "Deploy",
    who: "max",
    desc: "Max does git pull on Mac Mini, restarts orchestrator. If crash → git revert.",
  },
  {
    step: "06",
    title: "Verify",
    who: "ceo",
    desc: "CEO checks via Supabase MCP. Confirms data integrity, queries results.",
  },
  {
    step: "07",
    title: "Diary",
    who: "ceo",
    desc: "CEO writes Development Diary. First person. Honest about mistakes. The process is the product.",
  },
];

const AUTOPLAY_MS = 6000;
const MOBILE_BREAKPOINT = 768;

/* ============================================================
   Hook: detect viewport <768px (mobile fallback).
   ============================================================ */
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  return isMobile;
}

/* ============================================================
   Desktop org chart node (CEO / Max / CC).
   ============================================================ */
function Node({ memberKey, isSelected, onClick }) {
  const m = TEAM[memberKey];
  return (
    <div
      data-node={memberKey}
      onClick={onClick}
      className="group flex cursor-pointer flex-col items-center gap-1.5
                 transition-transform duration-300"
      style={{
        transform: isSelected ? "scale(1.08)" : "scale(1)",
        zIndex: isSelected ? 10 : 1,
        position: "relative",
      }}
    >
      <div
        className="flex items-center justify-center rounded-full border-2
                   transition-all duration-300"
        style={{
          width: isSelected ? 90 : 80,
          height: isSelected ? 90 : 80,
          background: isSelected ? `${m.accentHex}20` : "#172037",
          borderColor: isSelected ? m.accentHex : "#2a3556",
          fontSize: 32,
          boxShadow: isSelected ? `0 0 30px ${m.accentHex}30` : "none",
        }}
      >
        {m.emoji}
      </div>
      <div className="text-center">
        <div
          className="font-mono text-[14px] font-semibold"
          style={{ color: m.accentHex }}
        >
          {m.name}
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">
          {m.role}
        </div>
      </div>
      <div
        className="font-mono text-[11px] italic text-text-muted transition-opacity duration-300"
        style={{ opacity: isSelected ? 0 : 1 }}
      >
        {m.tagline}
      </div>
    </div>
  );
}

/* ============================================================
   SVG connections layer — curves between the 3 nodes, with
   label clickable + animated dot moving along path.
   ============================================================ */
function SVGConnections({ selectedConn, onSelectConnection, containerRef }) {
  const [paths, setPaths] = useState([]);

  useEffect(() => {
    const update = () => {
      if (!containerRef.current) return;
      const container = containerRef.current;
      const cRect = container.getBoundingClientRect();
      const nodes = {};
      ["ceo", "max", "cc"].forEach((id) => {
        const el = container.querySelector(`[data-node="${id}"]`);
        if (el) {
          const r = el.getBoundingClientRect();
          nodes[id] = {
            x: r.left - cRect.left + r.width / 2,
            y: r.top - cRect.top + r.height / 2,
          };
        }
      });
      if (Object.keys(nodes).length === 3) {
        setPaths(
          CONNECTIONS.map((c) => {
            const f = nodes[c.from];
            const t = nodes[c.to];
            const mx = (f.x + t.x) / 2;
            const my = (f.y + t.y) / 2;
            const dx = t.x - f.x;
            const dy = t.y - f.y;
            const len = Math.sqrt(dx * dx + dy * dy);
            const off = 30;
            const nx = -dy / len;
            const ny = dx / len;
            const cx = mx + nx * off;
            const cy = my + ny * off;
            return {
              ...c,
              d: `M ${f.x} ${f.y} Q ${cx} ${cy} ${t.x} ${t.y}`,
              mx: cx,
              my: cy,
            };
          })
        );
      }
    };
    update();
    /* Re-layout on resize so curves stay correct. */
    window.addEventListener("resize", update);
    return () => window.removeEventListener("resize", update);
  }, [containerRef]);

  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      style={{ zIndex: 0 }}
    >
      <defs>
        <marker
          id="hww-arrow"
          viewBox="0 0 10 6"
          refX="8"
          refY="3"
          markerWidth="8"
          markerHeight="6"
          orient="auto"
        >
          <path d="M0,0 L10,3 L0,6" fill="#7dd3fc" opacity="0.5" />
        </marker>
      </defs>
      {paths.map((p, i) => (
        <g key={i}>
          {/* Base track (dimmer) + accent overlay (brighter when selected) */}
          <path
            d={p.d}
            fill="none"
            stroke="#2a3556"
            strokeWidth={selectedConn === i ? 2.5 : 1.5}
          />
          <path
            d={p.d}
            fill="none"
            stroke="#7dd3fc"
            strokeWidth={selectedConn === i ? 2 : 1}
            opacity={selectedConn === i ? 0.7 : 0.25}
            markerEnd="url(#hww-arrow)"
          />
          {/* Animated dot crawling along the path. */}
          <circle r="3" fill="#7dd3fc" opacity="0.8">
            <animateMotion
              dur={`${3 + i}s`}
              repeatCount="indefinite"
              path={p.d}
            />
          </circle>
          {/* Clickable label hotspot at the curve midpoint. */}
          <g
            style={{ pointerEvents: "all", cursor: "pointer" }}
            onClick={() => onSelectConnection(i)}
          >
            <circle cx={p.mx} cy={p.my} r={22} fill="transparent" />
            <text
              x={p.mx}
              y={p.my}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={9}
              fill={selectedConn === i ? "#7dd3fc" : "#5d6680"}
              fontFamily="monospace"
              letterSpacing="0.5"
              style={{
                textTransform: "uppercase",
                pointerEvents: "none",
              }}
            >
              {p.label}
            </text>
          </g>
        </g>
      ))}
    </svg>
  );
}

/* ============================================================
   Detail panel — appears below the chart when a node is clicked.
   ============================================================ */
function DetailPanel({ memberKey, onClose }) {
  const m = TEAM[memberKey];
  return (
    <div
      className="relative rounded-lg border bg-surface px-6 py-5"
      style={{ borderColor: `${m.accentHex}40`, animation: "hwwSlideUp 0.3s ease" }}
    >
      <button
        onClick={onClose}
        className="absolute top-3 right-3.5 cursor-pointer border-none
                   bg-transparent text-[18px] text-text-muted hover:text-text"
        aria-label="Close"
      >
        ✕
      </button>
      <div className="mb-3.5 flex items-center gap-3">
        <span style={{ fontSize: 28 }}>{m.emoji}</span>
        <div>
          <div
            className="font-mono text-[16px] font-semibold"
            style={{ color: m.accentHex }}
          >
            {m.name}
          </div>
          <div className="font-mono text-[11px] uppercase tracking-[0.16em] text-text-muted">
            {m.role}
          </div>
        </div>
      </div>
      <p className="mb-4 text-[13px] leading-[1.6] text-text-dim">{m.desc}</p>
      <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-md bg-bg/60 p-3">
          <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.16em] text-pos">
            Superpower
          </div>
          <div className="text-[12px] text-text">{m.superpower}</div>
        </div>
        <div className="rounded-md bg-bg/60 p-3">
          <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.16em] text-neg">
            Weakness
          </div>
          <div className="text-[12px] text-text">{m.weakness}</div>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-md bg-bg/60 p-3">
          <div className="mb-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-primary">
            Tools
          </div>
          {m.tools.map((t) => (
            <div key={t} className="font-mono text-[11px] text-text-dim">
              · {t}
            </div>
          ))}
        </div>
        <div className="rounded-md bg-bg/60 p-3">
          <div className="mb-1.5 font-mono text-[9px] uppercase tracking-[0.16em] text-amber-400">
            Memory
          </div>
          <div className="text-[11px] leading-[1.5] text-text-dim">{m.memory}</div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   Connection panel — appears below the chart when a curve is clicked.
   ============================================================ */
function ConnectionPanel({ conn, onClose }) {
  const fromM = TEAM[conn.from];
  const toM = TEAM[conn.to];
  return (
    <div
      className="relative rounded-lg border border-border bg-surface px-6 py-5"
      style={{ animation: "hwwSlideUp 0.3s ease" }}
    >
      <button
        onClick={onClose}
        className="absolute top-3 right-3.5 cursor-pointer border-none
                   bg-transparent text-[18px] text-text-muted hover:text-text"
        aria-label="Close"
      >
        ✕
      </button>
      <div className="mb-3 flex items-center gap-2">
        <span
          className="font-mono text-[14px] font-semibold"
          style={{ color: fromM.accentHex }}
        >
          {fromM.name}
        </span>
        <span className="text-[12px] text-primary">→</span>
        <span
          className="font-mono text-[14px] font-semibold"
          style={{ color: toM.accentHex }}
        >
          {toM.name}
        </span>
        <span className="ml-2 font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">
          {conn.label}
        </span>
      </div>
      <p className="mb-3.5 text-[13px] leading-[1.6] text-text-dim">{conn.desc}</p>
      <div className="flex flex-wrap gap-1.5">
        {conn.items.map((item) => (
          <span
            key={item}
            className="rounded-md border border-border-soft bg-bg/60
                       px-2.5 py-0.5 font-mono text-[11px] text-text-dim"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   Workflow timeline — list of 7 steps. Active step is colored
   by the responsible role. Auto-advance every 12s, stops on
   first user click.
   ============================================================ */
function WorkflowTimeline({ activeStep, onClickStep }) {
  return (
    <div>
      <div
        className="mb-4 border-b border-border-soft pb-2 font-mono
                   text-[10px] uppercase tracking-[0.18em] text-text-muted"
      >
        Session workflow
      </div>
      <div className="flex flex-col gap-0.5">
        {WORKFLOW.map((w, i) => {
          const m = TEAM[w.who];
          const isActive = activeStep === i;
          return (
            <div
              key={i}
              onClick={() => onClickStep(i)}
              className="flex cursor-pointer items-start gap-3
                         rounded-md px-3.5 py-2.5 transition-all duration-300"
              style={{
                background: isActive ? "#172037" : "transparent",
                border: isActive
                  ? `1px solid ${m.accentHex}30`
                  : "1px solid transparent",
              }}
            >
              <div
                className="min-w-[28px] font-mono text-[18px] font-semibold leading-none"
                style={{
                  color: isActive ? m.accentHex : "#2a3556",
                  transition: "color 0.3s",
                }}
              >
                {w.step}
              </div>
              <div
                className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full
                           transition-colors duration-300"
                style={{ background: isActive ? m.accentHex : "#2a3556" }}
              />
              <div className="flex-1">
                <div
                  className="font-mono text-[12px] font-medium transition-colors duration-300"
                  style={{ color: isActive ? "#e8ecf5" : "#5d6680" }}
                >
                  {w.title}
                  <span
                    className="ml-2 font-mono text-[9px]"
                    style={{
                      color: m.accentHex,
                      opacity: isActive ? 1 : 0.4,
                    }}
                  >
                    {m.name}
                  </span>
                </div>
                {isActive && (
                  <div
                    className="mt-1 text-[11px] leading-[1.5] text-text-dim"
                    style={{ animation: "hwwSlideUp 0.3s ease" }}
                  >
                    {w.desc}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ============================================================
   MOBILE FALLBACK — static cards, no clicks needed.
   ============================================================ */
function MobileLayout() {
  return (
    <div className="space-y-6">
      {/* Team — 3 cards stacked */}
      <div className="space-y-4">
        {Object.values(TEAM).map((m) => (
          <div
            key={m.id}
            className="rounded-lg border bg-surface px-5 py-5"
            style={{ borderColor: `${m.accentHex}40` }}
          >
            <div className="mb-3 flex items-center gap-3">
              <span style={{ fontSize: 32 }}>{m.emoji}</span>
              <div>
                <div
                  className="font-mono text-[16px] font-semibold"
                  style={{ color: m.accentHex }}
                >
                  {m.name}
                </div>
                <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-text-muted">
                  {m.role}
                </div>
                <div className="mt-0.5 font-mono text-[11px] italic text-text-muted">
                  {m.tagline}
                </div>
              </div>
            </div>
            <p className="mb-3 text-[13px] leading-[1.6] text-text-dim">{m.desc}</p>
            <div className="grid grid-cols-1 gap-2.5 text-[12px]">
              <div>
                <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-pos">
                  Superpower:{" "}
                </span>
                <span className="text-text">{m.superpower}</span>
              </div>
              <div>
                <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-neg">
                  Weakness:{" "}
                </span>
                <span className="text-text">{m.weakness}</span>
              </div>
              <div>
                <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-primary">
                  Tools:{" "}
                </span>
                <span className="font-mono text-text-dim">{m.tools.join(" · ")}</span>
              </div>
              <div>
                <span className="font-mono text-[9px] uppercase tracking-[0.16em] text-amber-400">
                  Memory:{" "}
                </span>
                <span className="text-text-dim">{m.memory}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Connections — 3 paragraphs */}
      <div className="space-y-3 rounded-lg border border-border-soft bg-bg/40 px-5 py-5">
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-text-muted">
          How they collaborate
        </div>
        {CONNECTIONS.map((c) => {
          const fromM = TEAM[c.from];
          const toM = TEAM[c.to];
          return (
            <div
              key={c.label}
              className="border-l-2 pl-3"
              style={{ borderColor: `${fromM.accentHex}80` }}
            >
              <div className="mb-1 flex items-center gap-2 text-[12px]">
                <span
                  className="font-mono font-semibold"
                  style={{ color: fromM.accentHex }}
                >
                  {fromM.name}
                </span>
                <span className="text-primary">→</span>
                <span
                  className="font-mono font-semibold"
                  style={{ color: toM.accentHex }}
                >
                  {toM.name}
                </span>
                <span className="ml-1 font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
                  {c.label}
                </span>
              </div>
              <p className="text-[12px] leading-[1.55] text-text-dim">{c.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Workflow — plain numbered list */}
      <div>
        <div className="mb-3 border-b border-border-soft pb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-text-muted">
          Session workflow
        </div>
        <div className="space-y-3">
          {WORKFLOW.map((w) => {
            const m = TEAM[w.who];
            return (
              <div key={w.step} className="flex items-start gap-3">
                <div
                  className="min-w-[28px] font-mono text-[16px] font-semibold leading-none"
                  style={{ color: m.accentHex }}
                >
                  {w.step}
                </div>
                <div className="flex-1">
                  <div className="font-mono text-[12px] font-medium text-text">
                    {w.title}
                    <span
                      className="ml-2 font-mono text-[9px]"
                      style={{ color: m.accentHex }}
                    >
                      {m.name}
                    </span>
                  </div>
                  <div className="mt-0.5 text-[11px] leading-[1.5] text-text-dim">
                    {w.desc}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <KeyInsight />
    </div>
  );
}

/* ============================================================
   "Key insight" closer — same on both layouts.
   ============================================================ */
function KeyInsight() {
  return (
    <div className="rounded-lg border border-border bg-surface px-6 py-5 text-center">
      <div className="mb-2.5 font-mono text-[9px] uppercase tracking-[0.18em] text-text-muted">
        The key insight
      </div>
      <p className="text-[14px] leading-[1.7] text-text-dim">
        The CEO <span className="text-pos">thinks</span> but can't do.{" "}
        The intern <span className="text-cc">does</span> but can't think long-term.{" "}
        The human <span className="text-amber-400">can do and can think</span>, but doesn't scale.
      </p>
      <p className="mt-2 text-[13px] font-medium text-text">Together, they ship.</p>
    </div>
  );
}

/* ============================================================
   MAIN — auto-detects layout via useIsMobile hook.
   ============================================================ */
export default function HowWeWorkInteractive() {
  const isMobile = useIsMobile();
  /* Open with CEO selected by default. The detail panel is already
     visible at first render, so clicking another role/connection
     swaps the panel content instead of expanding the page height —
     no vertical "jump" of the workflow timeline below. */
  const [selectedNode, setSelectedNode] = useState("ceo");
  const [selectedConn, setSelectedConn] = useState(null);
  const [activeStep, setActiveStep] = useState(0);
  const [autoplayActive, setAutoplayActive] = useState(true);
  const containerRef = useRef(null);

  /* Auto-advance the workflow timeline every 12s — stops once
     the user has clicked any step (autoplayActive flag). */
  useEffect(() => {
    if (isMobile || !autoplayActive) return;
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % WORKFLOW.length);
    }, AUTOPLAY_MS);
    return () => clearInterval(interval);
  }, [isMobile, autoplayActive]);

  if (isMobile) {
    return (
      <>
        <style>{KEYFRAMES}</style>
        <MobileLayout />
      </>
    );
  }

  const handleNodeClick = (id) => {
    setSelectedConn(null);
    setSelectedNode(selectedNode === id ? null : id);
  };

  const handleConnClick = (i) => {
    setSelectedNode(null);
    setSelectedConn(selectedConn === i ? null : i);
  };

  const handleStepClick = (i) => {
    setActiveStep(i);
    /* Stop auto-advance on first manual interaction. */
    setAutoplayActive(false);
  };

  return (
    <div className="font-mono">
      <style>{KEYFRAMES}</style>

      {/* Org chart area — 3 nodes positioned absolutely. */}
      <div ref={containerRef} className="relative mb-6 h-[280px]">
        <SVGConnections
          selectedConn={selectedConn}
          onSelectConnection={handleConnClick}
          containerRef={containerRef}
        />

        {/* CEO — top center */}
        <div className="absolute left-1/2 top-2 -translate-x-1/2">
          <Node
            memberKey="ceo"
            isSelected={selectedNode === "ceo"}
            onClick={() => handleNodeClick("ceo")}
          />
        </div>

        {/* Max — bottom left */}
        <div className="absolute bottom-2 left-[15%]">
          <Node
            memberKey="max"
            isSelected={selectedNode === "max"}
            onClick={() => handleNodeClick("max")}
          />
        </div>

        {/* CC — bottom right */}
        <div className="absolute bottom-2 right-[15%]">
          <Node
            memberKey="cc"
            isSelected={selectedNode === "cc"}
            onClick={() => handleNodeClick("cc")}
          />
        </div>
      </div>

      {/* Detail panels (mutually exclusive). CEO is opened by default
         on first render so the panel area is never empty — clicking
         another role/connection swaps the content without shifting
         the timeline below. */}
      {selectedNode && (
        <div className="mb-6">
          <DetailPanel
            memberKey={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        </div>
      )}
      {selectedConn !== null && (
        <div className="mb-6">
          <ConnectionPanel
            conn={CONNECTIONS[selectedConn]}
            onClose={() => setSelectedConn(null)}
          />
        </div>
      )}

      {/* Workflow timeline */}
      <div className="mb-8">
        <WorkflowTimeline
          activeStep={activeStep}
          onClickStep={handleStepClick}
        />
      </div>

      <KeyInsight />
    </div>
  );
}

/* Inline keyframes — scoped via <style> tag inside the component
   tree so they don't leak into Astro's scoped CSS. Slide-up is
   used for both panels and the workflow description text. */
const KEYFRAMES = `
  @keyframes hwwSlideUp {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`;
