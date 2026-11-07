// Real browser smoke test, using Chrome's built-in DevTools protocol (no npm packages).
// Run from the project root: node tests/browser_auth.cjs
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const net = require('node:net');

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
async function freePort() {
  const socket = net.createServer();
  await new Promise(resolve => socket.listen(0, '127.0.0.1', resolve));
  const port = socket.address().port;
  await new Promise(resolve => socket.close(resolve));
  return port;
}
async function until(check, label) {
  const deadline = Date.now() + 30000;
  while (Date.now() < deadline) {
    if (await check()) return;
    await delay(100);
  }
  throw new Error(`Timed out: ${label}`);
}

(async () => {
  const root = process.cwd();
  const output = path.join(root, 'test-results', `browser-${Date.now()}`);
  fs.mkdirSync(output, { recursive: true });
  const python = process.env.PYTHON_EXE || [
    '.venv/Scripts/python.exe', '.runtime/python/python.exe', '.venv/bin/python',
  ].find(file => fs.existsSync(file)) || 'python';
  const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  const appPort = await freePort();
  const debugPort = await freePort();
  const origin = `http://127.0.0.1:${appPort}`;
  const server = spawn(python, ['-c',
    `from app import app; app.run(host='127.0.0.1', port=${appPort}, use_reloader=False)`], {
    cwd: root, windowsHide: true, stdio: 'ignore',
    env: { ...process.env, DATABASE_PATH: path.join(output, 'test.db'),
      SESSION_COOKIE_SECURE: '0', APP_ORIGIN: origin },
  });
  let browser;
  let ws;
  let send;
  try {
    await until(async () => {
      try { return (await fetch(`${origin}/api/health`)).ok; } catch { return false; }
    }, 'Flask startup');
    browser = spawn(chrome, ['--headless=new', '--disable-gpu', '--no-first-run',
      '--no-default-browser-check', `--remote-debugging-port=${debugPort}`,
      `--user-data-dir=${path.join(output, 'chrome')}`, 'about:blank'],
    { windowsHide: true, stdio: 'ignore' });
    let target;
    await until(async () => {
      try {
        const targets = await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json();
        target = targets.find(item => item.type === 'page');
        return !!target;
      } catch { return false; }
    }, 'headless Chrome startup');
    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    let id = 0;
    const pending = new Map();
    const errors = [];
    let loaded = 0;
    ws.onmessage = ({ data }) => {
      const message = JSON.parse(data);
      if (message.method === 'Page.loadEventFired') loaded++;
      if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
      if (pending.has(message.id)) {
        const { resolve, reject } = pending.get(message.id);
        pending.delete(message.id);
        message.error ? reject(new Error(JSON.stringify(message.error))) : resolve(message.result);
      }
    };
    send = (method, params = {}) => new Promise((resolve, reject) => {
      pending.set(++id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
    await send('Runtime.enable');
    await send('Page.enable');
    const evaluate = async expression => {
      const response = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
      if (response.exceptionDetails) throw new Error(JSON.stringify(response.exceptionDetails));
      return response.result.value;
    };
    const wait = (expression, label) => until(() => evaluate(expression), label);
    const go = async url => {
      const previous = loaded;
      await send('Page.navigate', { url: origin + url });
      await until(() => loaded > previous, 'navigation completed');
      await wait(`location.origin === ${JSON.stringify(origin)} && document.readyState === 'complete'`, 'page loaded');
    };
    const reload = async () => {
      const previous = loaded;
      await send('Page.reload');
      await until(() => loaded > previous, 'reload completed');
    };
    const fill = (selector, value) => evaluate(`(() => {
      const input = document.querySelector(${JSON.stringify(selector)});
      input.value = ${JSON.stringify(value)};
      input.dispatchEvent(new Event('input', { bubbles: true }));
    })()`);
    const click = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
    const email = 'browser@example.com';
    const password = 'browser test passphrase 123';

    await go('/dashboard');
    await wait(`location.pathname === '/sign-in.html' && !!document.querySelector('#password')`, 'protected dashboard redirect');
    await go('/sign-up.html');
    await wait(`!!document.querySelector('#display-name')`, 'signup page');
    await fill('#display-name', 'Browser Student');
    await fill('#email', email);
    await fill('#password', password);
    await click('.password-toggle');
    assert.equal(await evaluate(`document.querySelector('#password').type`), 'text');
    await click('.password-toggle');
    await click('button[type="submit"]');
    await wait(`location.pathname === '/sign-in.html' && location.search.includes('registered') && document.readyState === 'complete'`, 'signup integration');
    await fill('#email', email);
    await fill('#password', 'wrong password');
    await click('button[type="submit"]');
    await wait(`document.querySelector('#demo-note').textContent.includes('Incorrect email or password')`, 'invalid password feedback');
    await fill('#password', password);
    await click('button[type="submit"]');
    await wait(`location.pathname === '/dashboard' && document.body.textContent.includes('No results yet')`, 'login and dashboard');
    await wait(`document.querySelector('.nav-sign-in').textContent === 'Sign out'`, 'authenticated navigation');
    await reload();
    await wait(`document.readyState === 'complete' && document.querySelector('.nav-sign-in').textContent === 'Sign out'`, 'session after refresh');
    await go('/TakeTest.html');
    await wait(`!!document.querySelector('#current-answer')`, 'assessment page');
    for (const [index, value] of [7, 5, 4, 5, 7].entries()) {
      await fill('#current-answer', String(value));
      await click('#next-question');
      if (index < 4) await wait(`document.querySelector('.question-number').textContent.includes('Question ${index + 2}')`, 'next question');
    }
    await wait(`location.pathname === '/dashboard' && document.querySelector('.empty-state li')?.textContent.includes('Predicted stress level')`, 'saved prediction');
    await reload();
    await wait(`!!document.querySelector('.empty-state li') && document.querySelector('.nav-sign-in').textContent === 'Sign out'`, 'history after refresh');
    await click('.nav-sign-in');
    await wait(`location.pathname === '/sign-in.html' && document.readyState === 'complete'`, 'logout');
    assert.equal(await evaluate(`fetch('/api/history').then(r => r.status)`), 401);
    await go('/dashboard');
    await wait(`location.pathname === '/sign-in.html'`, 'protection after logout');
    assert.deepEqual(errors, [], 'No uncaught frontend exceptions');
    console.log('PASS: browser signup, password toggle, invalid login, login, refresh, prediction, private history, logout, route protection.');
  } finally {
    if (send && ws?.readyState === WebSocket.OPEN) {
      try { await send('Browser.close'); } catch {}
    }
    ws?.close();
    browser?.kill();
    server.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
