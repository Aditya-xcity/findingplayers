document.addEventListener("DOMContentLoaded", () => {
  const menu = document.querySelector(".mobile-menu");
  const nav = document.querySelector(".nav-links");
  if (menu && nav) {
    menu.addEventListener("click", () => {
      const open = nav.classList.toggle("nav-open");
      menu.setAttribute("aria-expanded", String(open));
    });
  }
  document.querySelectorAll(".flash-close").forEach(button => {
    button.addEventListener("click", () => button.closest(".flash")?.remove());
  });
  document.querySelectorAll("form").forEach(form => {
    form.addEventListener("submit", event => {
      if (!form.checkValidity()) {
        event.preventDefault();
        form.reportValidity();
      }
    });
  });
  // Keep the project search keyboard-friendly without hijacking normal form submission.
  const search = document.querySelector(".search-bar input[name='q']");
  if (search) search.setAttribute("aria-label", "Search projects or people");
});
