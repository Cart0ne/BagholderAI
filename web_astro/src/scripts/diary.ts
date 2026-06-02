/* Diary page — fetch all entries from Supabase and replace the
   server-rendered fallback list with the live one. Click on an entry
   toggles its body open (accordion: only one expanded at a time). */

const SB_URL =
  "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

type Entry = {
  day: number;
  session: number;
  date: string;          /* stored as "May 2, 2026" — see formatDate */
  title: string;
  summary: string;
  status: "BUILDING" | "COMPLETE";
  tags: string[];
};

const escapeHTML = (s: string) =>
  String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;",
    '"': "&quot;", "'": "&#39;",
  }[c]!));

/* The DB stores English narrative dates (legacy from old site), including
   multi-day ranges that Date() can't parse:
     "May 27, 2026"             → "27 May"
     "May 25-26, 2026"          → "25–26 May"
     "March 31 - April 1, 2026" → "31 Mar–1 Apr"
   We reformat client-side for the compact numerone column (year dropped —
   redundant under the big session number). Falls back to the raw string. */
const abbr = (m: string) => m.slice(0, 3);
const formatDate = (raw: string): string => {
  const s = String(raw ?? "").replace(/,?\s*\d{4}\s*$/, "").trim();
  let m;
  /* cross-month range: "March 31 - April 1" */
  if ((m = s.match(/^([A-Za-z]+)\s+(\d+)\s*[-–]\s*([A-Za-z]+)\s+(\d+)$/)))
    return `${m[2]} ${abbr(m[1])}–${m[4]} ${abbr(m[3])}`;
  /* same-month range: "May 25-26" */
  if ((m = s.match(/^([A-Za-z]+)\s+(\d+)\s*[-–]\s*(\d+)$/)))
    return `${m[2]}–${m[3]} ${abbr(m[1])}`;
  /* single day: "May 27" */
  if ((m = s.match(/^([A-Za-z]+)\s+(\d+)$/)))
    return `${m[2]} ${abbr(m[1])}`;
  return s;
};

const renderEntry = (entry: Entry, expanded: boolean): string => {
  const isBuilding = entry.status === "BUILDING";
  const badgeClasses = isBuilding
    ? "border-neu/40 text-neu bg-neu/10"
    : "border-pos/30 text-pos bg-pos/10";
  const badgeText = isBuilding ? "● building" : "complete";

  const tagsHTML = (entry.tags ?? []).map(t =>
    `<span class="rounded-md border border-border-soft bg-bg
                  px-2 py-0.5 font-mono text-[10px] text-text-muted">
       #${escapeHTML(t)}
     </span>`
  ).join("");

  return `
    <div class="log-entry group cursor-pointer grid grid-cols-[auto_1fr] items-start gap-5
                rounded-2xl border border-border border-l-4 border-l-pos
                bg-surface px-5 py-4 shadow-sticker-sm
                transition hover:-translate-y-0.5 hover:bg-surface-hover hover:shadow-sticker
                ${expanded ? "expanded" : ""}">
      <div class="w-[60px] shrink-0 pt-0.5 text-center leading-tight">
        <span class="block font-mono text-[9px] font-bold uppercase tracking-[0.16em] text-text-muted">session</span>
        <span class="block font-display text-[34px] font-extrabold leading-none text-pos">${entry.session}</span>
        <span class="mt-0.5 block font-mono text-[9.5px] uppercase tracking-[0.06em] text-text-muted">${escapeHTML(formatDate(entry.date))}</span>
      </div>
      <div>
        <div class="log-header">
          <div class="flex items-start justify-between gap-3">
            <h2 class="font-display text-[17px] font-extrabold leading-[1.2]
                       tracking-[-0.01em] text-text transition-colors group-hover:text-pos">
              ${escapeHTML(entry.title)}
            </h2>
            <span class="mt-0.5 shrink-0 rounded-full border px-2 py-0.5
                         font-mono text-[9px] uppercase tracking-[0.16em]
                         ${badgeClasses}">
              ${badgeText}
            </span>
          </div>
        </div>
        <div class="log-body pt-2.5 text-[13.5px] leading-[1.6] text-text-dim">
          <p>${escapeHTML(entry.summary || "—")}</p>
          ${tagsHTML ? `<div class="mt-2.5 flex flex-wrap gap-2">${tagsHTML}</div>` : ""}
        </div>
      </div>
    </div>
  `;
};

const wireAccordion = (root: HTMLElement) => {
  root.addEventListener("click", e => {
    const entry = (e.target as HTMLElement).closest<HTMLElement>(".log-entry");
    if (!entry) return;
    const wasOpen = entry.classList.contains("expanded");
    /* close all */
    root.querySelectorAll(".log-entry")
        .forEach(el => el.classList.remove("expanded"));
    /* toggle this one */
    if (!wasOpen) entry.classList.add("expanded");
  });
};

const setText = (id: string, value: string) => {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
};

const main = async () => {
  const container = document.getElementById("log-container");
  if (!container) return;

  /* Always wire the accordion — works on both fallback and live data. */
  wireAccordion(container);

  try {
    const r = await fetch(
      `${SB_URL}/rest/v1/diary_entries` +
      `?select=day,session,date,title,summary,status,tags` +
      `&order=session.desc`,
      { headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` } },
    );
    if (!r.ok) throw new Error(`${r.status}`);
    const entries = (await r.json()) as Entry[];

    if (!entries.length) return;

    /* Replace fallback markup with live entries.

       Previously we toggled `is-visible` off then back on with rAF to
       re-trigger the stagger animation on the fresh children. Side
       effect: visible "second refresh" flash on page load, because the
       fallback list animated in, then disappeared, then re-animated.

       New behavior: leave `is-visible` exactly as it was and let the
       new children inherit the parent state. The stagger CSS is
       parent-controlled via `.is-visible` selector — children rendered
       AFTER visibility just appear settled. No flash. */
    const wasVisible = container.classList.contains("is-visible");

    container.innerHTML = entries
      .map((e, i) => renderEntry(e, i === 0))
      .join("");

    setText("diary-count", String(entries.length));

    if (!wasVisible) {
      /* Container not yet observed → ensure the Layout's IO picks up
         the freshly rendered list when scrolled into view. */
      const io = new IntersectionObserver(es => {
        for (const e of es) {
          if (e.isIntersecting) {
            e.target.classList.add("is-visible");
            io.unobserve(e.target);
          }
        }
      }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
      io.observe(container);
    }
  } catch {
    const errEl = document.getElementById("log-error");
    if (errEl) errEl.hidden = false;
    setText("diary-count", String(/* fallback count */ 2));
  }
};

main();
