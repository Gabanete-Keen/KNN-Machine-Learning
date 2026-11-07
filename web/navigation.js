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

async function updateAccountNavigation() {
  const accountLink = document.querySelector('.nav-sign-in');
  if (!accountLink || !window.pahuwaySession) return;
  try {
    const session = await window.pahuwaySession();
    if (!session) {
      accountLink.textContent = 'Sign in';
      accountLink.href = 'sign-in.html';
      accountLink.onclick = null;
      document.querySelectorAll('a[href="/dashboard"]').forEach((link) => {
        link.href = 'results.html';
      });
      return;
    }
    accountLink.textContent = 'Sign out';
    accountLink.href = '#';
    accountLink.removeAttribute('aria-current');
    accountLink.onclick = async (event) => {
      event.preventDefault();
      try {
        await window.pahuwayRequest('/api/logout', {});
        sessionStorage.removeItem('pahuway-result');
        window.location.assign('/sign-in.html');
      } catch (error) {
        accountLink.textContent = 'Retry sign out';
        accountLink.title = error.message;
      }
    };
    document.querySelectorAll('a[href="results.html"]').forEach((link) => {
      link.href = '/dashboard';
    });
  } catch (error) {
    accountLink.title = error.message;
  }
}
window.addEventListener('pageshow', updateAccountNavigation);
