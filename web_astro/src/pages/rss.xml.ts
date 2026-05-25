import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import type { APIContext } from "astro";
import MarkdownIt from "markdown-it";

const parser = new MarkdownIt({ html: true, linkify: true });

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
      content: parser.render(post.body ?? ""),
    })),
    customData: "<language>en-us</language>",
  });
}
