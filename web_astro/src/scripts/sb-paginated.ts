/* Supabase REST paginated fetch.
   The anon role caps responses at 1000 rows even when `limit=N` is
   larger; we paginate via Range header until a short page comes back
   (or hit a 10k safety cap). Pattern mirrors admin.html sbFetchAll. */

const SB_URL = "https://pxdhtmqfwjwjhtcoacsn.supabase.co";
const SB_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB4ZGh0bXFmd2p3amh0Y29hY3NuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4NDI1OTIsImV4cCI6MjA4OTQxODU5Mn0." +
  "G76lvYWrqlM0z2RoSkU1uAglfMBKN_rXvBGOQhb4kdg";

export async function sbFetchAll<T>(
  path: string,
  pageSize = 1000,
): Promise<T[]> {
  const safetyCap = 10000;
  const all: T[] = [];
  let offset = 0;
  while (offset < safetyCap) {
    const res = await fetch(`${SB_URL}/rest/v1/${path}`, {
      headers: {
        apikey: SB_KEY,
        Authorization: `Bearer ${SB_KEY}`,
        "Range-Unit": "items",
        Range: `${offset}-${offset + pageSize - 1}`,
      },
    });
    if (!res.ok && res.status !== 206) {
      throw new Error(`Supabase ${res.status} on ${path}`);
    }
    const page = (await res.json()) as T[];
    if (!Array.isArray(page) || page.length === 0) break;
    all.push(...page);
    if (page.length < pageSize) break;
    offset += pageSize;
  }
  return all;
}
