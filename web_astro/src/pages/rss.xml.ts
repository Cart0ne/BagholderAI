import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import type { APIContext } from "astro";
import MarkdownIt from "markdown-it";

const parser = new MarkdownIt({ html: true, linkify: true });

/* Umami pixel appended to every RSS item's HTML body. Tracks opens of
   articles imported into Dev.to (and any other RSS-consuming surface)
   via the Umami "Dev.to" pixel created 2026-05-26. Generic across the
   whole feed — per-article tracking would need one pixel per post. */
const UMAMI_PIXEL =
  '<img src="https://cloud.umami.is/p/0nHeF7vMT" width="1" height="1" alt="" style="display:none" />';

export async function GET(context: APIContext) {
  const posts = (
    await getCollection("blog", ({ data }) =>
      import.meta.env.PROD ? !data.draft : true,
    )
  ).sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

  return rss({
    title: "BagHolderAI Blog",
    description:
      "Real stories from building a crypto trading bot with AI as CEO. Technical deep-dives, failures, and honest lessons from a startup running in public.",
    site: context.site!,
    items: posts.map((post) => ({
      title: post.data.title,
      pubDate: post.data.date,
      description: post.data.summary,
      link: `/blog/${post.id}/`,
      categories: post.data.tags,
      content: parser.render(post.body ?? "") + UMAMI_PIXEL,
    })),
    customData: "<language>en-us</language>",
  });
}
