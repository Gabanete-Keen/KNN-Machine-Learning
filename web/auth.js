document.querySelectorAll('.password-toggle').forEach((button) => {
  const input = document.getElementById(button.getAttribute('aria-controls'));
  if (!input) return;

  button.addEventListener('click', () => {
    const showPassword = input.type === 'password';
    input.type = showPassword ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(showPassword));
    button.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
  });
});

const authForm = document.querySelector('.auth-form');
const signupPage = window.location.pathname.endsWith('/sign-up.html');
const statusNote = document.querySelector('#demo-note');
statusNote.setAttribute('role', 'status');
statusNote.setAttribute('aria-live', 'polite');

authForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!authForm.reportValidity()) return;
  const button = authForm.querySelector('button[type="submit"]');
  if (button.disabled) return;
  button.disabled = true;
  authForm.setAttribute('aria-busy', 'true');
  button.textContent = signupPage ? 'Creating account...' : 'Signing in...';
  statusNote.textContent = '';
  try {
    const payload = { email: document.querySelector('#email').value,
      password: document.querySelector('#password').value };
    if (signupPage) payload.display_name = document.querySelector('#display-name').value;
    const result = await window.pahuwayRequest(signupPage ? '/api/signup' : '/api/login', payload);
    window.location.assign(signupPage ? '/sign-in.html?registered=1' : result.redirect);
  } catch (error) {
    statusNote.textContent = error.message;
  } finally {
    button.disabled = false;
    authForm.removeAttribute('aria-busy');
    button.textContent = signupPage ? 'Sign up' : 'Sign in';
  }
});

if (!signupPage && new URLSearchParams(window.location.search).has('registered')) {
  statusNote.textContent = 'Account created. Sign in with your email and password.';
}
