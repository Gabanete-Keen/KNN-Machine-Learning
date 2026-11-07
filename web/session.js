// Session state always comes from the server; the HttpOnly cookie stays private.
const backendHelp = 'Unable to reach the authentication server. Run app.py and open http://127.0.0.1:5000.';
async function authFetch(url, options) {
  if (window.location.protocol === 'file:') throw new Error(backendHelp);
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(backendHelp);
  }
  if (!(response.headers.get('Content-Type') || '').includes('application/json')) {
    throw new Error(backendHelp);
  }
  return response;
}

window.pahuwaySession = async () => {
  const response = await authFetch('/api/session', { credentials: 'same-origin', cache: 'no-store' });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error('Unable to check your session. Please try again.');
  return response.json();
};

window.pahuwayRequest = async (url, data) => {
  const session = await window.pahuwaySession();
  const response = await authFetch(url, {
    method: 'POST', credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json',
      ...(session ? { 'X-CSRF-Token': session.csrf_token } : {}) },
    body: JSON.stringify(data),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Unable to complete your request.');
  return result;
};
