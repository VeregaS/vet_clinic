for (const nav of document.querySelectorAll(".masthead nav, .day-tabs")) {
  let hovered = null;
  let destination = null;
  function place(animate = false) {
    const item = destination || hovered || nav.querySelector("a:focus-visible") || nav.querySelector("[aria-current]");
    nav.classList.toggle("nav-interacting", animate);
    nav.style.setProperty("--bar-width", (item?.offsetWidth || 0) + "px");
    if (item) {
      nav.style.setProperty("--bar-x", item.offsetLeft + "px");
      nav.style.setProperty("--bar-y", (item.offsetTop + item.offsetHeight - 2) + "px");
    }
  }

  place();
  nav.classList.add("moving-line");
  for (const link of nav.querySelectorAll("a")) {
    link.addEventListener("click", event => {
      if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      destination = link;
      place(true);
    });
    link.addEventListener("pointerenter", event => {
      if (event.pointerType === "touch") return;
      hovered = link;
      place(true);
    });
  }
  nav.addEventListener("pointerleave", () => { hovered = null; place(true); });
  nav.addEventListener("focusin", event => {
    if (event.target.matches(":focus-visible")) hovered = null;
    place(true);
  });
  window.addEventListener("pageshow", event => {
    if (!event.persisted) return;
    destination = hovered = null;
    place();
  });
  nav.addEventListener("focusout", () => requestAnimationFrame(() => place(true)));
  new ResizeObserver(() => place()).observe(nav);
  document.fonts.ready.then(() => place());
}
