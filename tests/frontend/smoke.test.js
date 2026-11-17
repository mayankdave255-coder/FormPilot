// End-to-end smoke test: loads the real index.html + app.js in jsdom and talks to a running FormPilot server.
// Usage: start the server (python -m uvicorn backend.main:app --port 8000) then `npm test` in tests/frontend.
const { JSDOM } = require('jsdom');
const fs = require('fs'), path = require('path'), assert = require('assert');
const BASE = process.env.BASE_URL || 'http://127.0.0.1:8000/';
const ROOT = path.join(__dirname, '..', '..');
const sleep = ms => new Promise(r => setTimeout(r, ms));
let passed = 0;
const check = async (name, fn) => { try { await fn(); passed++; console.log('  ok   ' + name); } catch (e) { console.error('  FAIL ' + name + '\n       ' + e.message); process.exitCode = 1; } };

(async () => {
  const errors = [];
  const dom = new JSDOM(fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace(/<script src="app.js"><\/script>/, ''), { url: BASE, runScripts: 'outside-only', pretendToBeVisual: true });
  const w = dom.window;
  w.addEventListener('error', e => errors.push(e.message));
  w.URL.createObjectURL = () => 'blob:test'; w.URL.revokeObjectURL = () => {};
  w.scrollTo = () => {}; w.Element.prototype.scrollTo = () => {}; w.confirm = () => true; w.prompt = (_m, d) => d;
  // jsdom has no fetch: bridge to Node's fetch, converting jsdom FormData/File into Node equivalents.
  w.fetch = async (url, opts = {}) => {
    const target = new URL(url, BASE).href; const o = { ...opts };
    if (o.body instanceof w.FormData) {
      const fd = new FormData();
      for (const [k, v] of o.body.entries()) {
        if (typeof v === 'string') fd.append(k, v);
        else { const buf = await new Promise(res => { const fr = new w.FileReader(); fr.onload = () => res(fr.result); fr.readAsArrayBuffer(v); }); fd.append(k, new Blob([buf], { type: v.type }), v.name); }
      }
      o.body = fd;
    }
    return fetch(target, o);
  };
  w.eval(fs.readFileSync(path.join(ROOT, 'app.js'), 'utf8') + '\n;window.__state=state;window.__api=api;window.__upload=uploadFiles;');
  await sleep(600);
  const $ = s => w.document.querySelector(s), $$ = s => [...w.document.querySelectorAll(s)];
  const go = async name => { $(`[data-screen="${name}"]`).click(); await sleep(250); };
  const state = () => w.__state;

  await check('app.js loads and the dashboard renders', () => {
    assert.deepStrictEqual(errors, []);
    assert.ok($('#app').textContent.includes('Welcome to FormPilot'));
  });
  await check('a backend session is created and remembered', () => {
    assert.ok(state().apiReady, 'apiReady should be true');
    assert.ok(w.localStorage.getItem('formpilot.session'));
  });
  await check('all five screens render without errors', async () => {
    for (const [id, text] of [['analysis', 'Document analysis'], ['assistant', "Let's complete this together"], ['review', 'readiness report'], ['draft', 'application draft'], ['dashboard', 'Welcome']]) {
      await go(id); assert.ok($('#screenContent').textContent.includes(text), `${id} missing "${text}"`);
    }
    assert.deepStrictEqual(errors, []);
  });
  await check('API errors show a readable message, not [object Object]', async () => {
    const msg = await w.__api('/sessions/does-not-exist').then(() => 'no error', e => e.message);
    assert.ok(/expired|session/i.test(msg) && !msg.includes('[object'), msg);
  });
  await check('uploading a real PDF fills the analysis screen from the server schema', async () => {
    const pdf = fs.readFileSync(path.join(__dirname, 'sample-form.pdf'));
    const file = new w.File([pdf], 'form.pdf', { type: 'application/pdf' });
    await w.__upload([file], 'application', true);
    for (let i = 0; i < 20 && !state().formFields.length; i++) await sleep(400);
    assert.ok(state().formFields.length >= 3, 'no fields detected');
    await go('analysis');
    const stat = $$('.stat-box strong').map(e => e.textContent);
    assert.strictEqual(Number(stat[0]), state().formFields.length);
    assert.notStrictEqual(stat[0], '18');
  });
  await check('confirming an answer in the assistant saves it on the server', async () => {
    // The guided assistant now walks the actual detected form fields (state.formFields)
    // rather than a fixed 3-question demo script, so the "current" field's API id is
    // read from the app instead of assumed to always be annual_household_income.
    await go('assistant');
    const qs = w.eval('questionList()'); const curApiId = qs[state().question % qs.length].apiId;
    $('#chatInput').value = '350000'; $('#chatForm').dispatchEvent(new w.Event('submit', { cancelable: true })); await sleep(400);
    $('[data-action="confirm-answer"]').click(); await sleep(500);
    const sid = state().sessionId; const res = await (await w.fetch(`/api/v1/sessions/${sid}`)).json();
    assert.strictEqual(res.answers[curApiId].value, '350000');
  });
  await check('"Run checks again" shows server issues on the review screen', async () => {
    await go('review'); $('[data-action="run-validation"]').click(); await sleep(600);
    assert.ok($('#serverChecks'), 'server checks card missing');
    assert.ok($('#serverChecks').textContent.includes('income certificate'));
  });
  await check('draft PDF downloads from the server', async () => {
    await go('draft'); let blob = null;
    w.eval('downloadBlob = (b,n)=>{window.__blob=b;window.__name=n}'); // function declarations are global, so this override takes effect
    $('[data-action="download-pdf"]').click(); await sleep(900);
    assert.ok(w.__blob && w.__blob.size > 500, 'no PDF blob'); assert.ok(/\.pdf$/.test(w.__name));
  });
  await check('the scanner modal opens and the crop button no longer throws', async () => {
    await go('dashboard'); $('[data-action="scanner"]').click(); await sleep(100);
    $('#scannerModal [data-action="crop-page"]').click(); await sleep(100);
    assert.deepStrictEqual(errors, []);
  });
  await check('deleting the workspace removes the session on the server', async () => {
    const sid = state().sessionId; $('[data-action="delete-session"]').click(); await sleep(700);
    assert.strictEqual((await w.fetch(`/api/v1/sessions/${sid}`)).status, 404);
  });
  console.log(`\n${passed} frontend checks passed${process.exitCode ? ' (with failures)' : ''}`);
  process.exit(process.exitCode || 0);
})();
