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

const renderEntry = (entry: Entry, expanded: boolean): string => {
  const isBuilding = entry.status === "BUILDING";
  const badgeClasses = isBuilding
    ? "border-neu/40 text-neu bg-neu/5"
    : "border-pos/30 text-pos bg-pos/5";
  const badgeText = isBuilding ? "● building" : "complete";

  const tagsHTML = (entry.tags ?? []).map(t =>
    `<span class="rounded-md border border-border-soft bg-surface/50
                  px-2 py-0.5 font-mono text-[10px] text-text-muted">
       #${escapeHTML(t)}
     </span>`
  ).join("");

  return `
    <div class="log-entry cursor-pointer border-b border-border-soft py-2.5
                px-3 transition-colors hover:bg-surface/40 first:border-t
                ${expanded ? "expanded" : ""}">
      <div class="log-header flex items-center gap-3">
        <span class="font-mono text-[10.5px] uppercase tracking-[0.14em]
                     text-text-muted shrink-0 w-[88px]">
          Session ${entry.session}
        </span>
        <span class="flex-1 text-[14.5px] text-text font-medium">
          ${escapeHTML(entry.title)}
        </span>
        <span class="shrink-0 rounded-full border px-2 py-0.5
                     font-mono text-[9px] uppercase tracking-[0.16em]
                     ${badgeClasses}">
          ${badgeText}
        </span>
      </div>
      <div class="log-body pt-2.5 text-[13.5px] leading-[1.6] text-text-dim">
        <p>${escapeHTML(entry.summary || "—")}</p>
        ${tagsHTML ? `<div class="mt-2.5 flex flex-wrap gap-2">${tagsHTML}</div>` : ""}
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
      `?select=day,session,title,summary,status,tags` +
      `&order=session.desc`,
      { headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` } },
    );
    if (!r.ok) throw new Error(`${r.status}`);
    const entries = (await r.json()) as Entry[];

    if (!entries.length) return;

    /* Detect if container had already become visible (IntersectionObserver
       in Layout.astro fires on load — by the time fetch resolves, the
       observer may have already been unobserved). */
    const wasVisible = container.classList.contains("is-visible");
    container.classList.remove("is-visible");

    container.innerHTML = entries
      .map((e, i) => renderEntry(e, i === 0))
      .join("");

    setText("diary-count", String(entries.length));

    /* Re-trigger stagger animation on the freshly rendered children. */
    if (wasVisible) {
      requestAnimationFrame(() => container.classList.add("is-visible"));
    } else {
      /* Container not yet observed → re-observe after replacement so
         the Layout's IntersectionObserver picks it up. */
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
