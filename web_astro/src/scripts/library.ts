/* /library — shelf toggle. Click on a closed book opens it and closes
   the others. Clicks on links inside an open book are ignored so the
   buy/preview CTAs work normally. */

const books = document.querySelectorAll<HTMLElement>(
  ".library-shelf .shelf-book[data-vol]"
);

books.forEach((b) => {
  b.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    if (target.closest("a")) return;
    if (b.classList.contains("open")) return;
    books.forEach((o) => o.classList.remove("open"));
    b.classList.add("open");
  });
});
