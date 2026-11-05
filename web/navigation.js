// Keep the navigation clear at the top and readable over scrolling content.
const siteHeader = document.querySelector('.site-header');

if (siteHeader) {
  const updateNavigation = () => {
    siteHeader.classList.toggle('is-scrolled', window.scrollY > 8);
  };

  window.addEventListener('scroll', updateNavigation, { passive: true });
  window.addEventListener('pageshow', updateNavigation);
  updateNavigation();
}
