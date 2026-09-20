# UI-Test: echte Oberfläche + echtes Backend (Fake-KI) in Chromium. Nur für die Entwicklung.
import subprocess, sys, json, time, os, urllib.request, re
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
SHOTS = os.environ.get('SHOTS', '/tmp/zx-shots'); os.makedirs(SHOTS, exist_ok=True)
proc = subprocess.Popen(['node', os.path.join(HERE, 'bridge.mjs')], stdout=subprocess.PIPE, text=True)
port = int(proc.stdout.readline().strip().split('=')[1])
BASE = f'http://127.0.0.1:{port}'
def totp(secret, offset=0): return urllib.request.urlopen(f'{BASE}/totp?secret={secret}&offset={offset}').read().decode()

MOCK = """
(() => {
  const BASE = '%BASE%'; const SID = Math.floor(Math.random()*1e6)+10; const L = {chat:[],engine:[],ml:[],ended:[]};
  const enc = (v) => { if (v instanceof Float32Array) return {__b64: btoa(String.fromCharCode(...new Uint8Array(v.buffer,v.byteOffset,v.byteLength))), t:'f32'};
    if (v instanceof ArrayBuffer) return {__b64: btoa(String.fromCharCode(...new Uint8Array(v))), t:'u8'};
    if (Array.isArray(v)) return v.map(enc); if (v && typeof v==='object') return Object.fromEntries(Object.entries(v).map(([k,x])=>[k,enc(x)])); return v; };
  const call = (ch) => async (p) => { const r = await fetch(BASE+'/invoke', {method:'POST', headers:{'x-sid':SID}, body: JSON.stringify({channel:ch, payload: enc(p)})}); return r.json(); };
  const map = {authStatus:'auth:status',authSetup:'auth:setup',authRegister:'auth:register',authLogin:'auth:login',authQr:'auth:qr',authVerify2fa:'auth:verify2fa',authEnroll:'auth:enroll',authLogout:'auth:logout',authPing:'auth:ping',
    load:'app:load',saveChats:'chats:save',saveSettings:'settings:save',send:'chat:send',stop:'chat:stop',extractFile:'file:extract',transcribe:'voice:transcribe',
    changePassword:'account:changePassword',totpBegin:'account:totpBegin',totpConfirm:'account:totpConfirm',totpDisable:'account:totpDisable',deleteAccount:'account:delete',openExternal:'shell:open',
    adminStepUp:'admin:stepUp',adminUsers:'admin:users',adminSetStatus:'admin:setStatus',adminDeleteUser:'admin:deleteUser',adminPolicyGet:'admin:policyGet',adminPolicySet:'admin:policySet',
    adminSetSearchKey:'admin:setSearchKey',adminAudit:'admin:audit',adminModelDownload:'admin:modelDownload',adminModelUse:'admin:modelUse'};
  const api = { __sid: SID }; for (const [k,v] of Object.entries(map)) api[k] = call(v);
  api.onChatEvent = cb => L.chat.push(cb); api.onEngine = cb => L.engine.push(cb); api.onMl = cb => L.ml.push(cb); api.onSessionEnded = cb => L.ended.push(cb); api.onSplash = () => {}; api.onUpdate = () => {};
  setInterval(async () => { try { const evs = await (await fetch(BASE+'/events?sid='+SID)).json(); for (const e of evs) { if (e.c==='chat:event') L.chat.forEach(f=>f(e.p)); else if (e.c==='engine:status') L.engine.forEach(f=>f(e.p)); else if (e.c==='ml:status') L.ml.forEach(f=>f(e.p)); else if (e.c==='session:ended') L.ended.forEach(f=>f(e.p)); else (window.__events = window.__events||[]).push(e); } } catch(e){} }, 40);
  window.zayriox = api;
})();
""".replace('%BASE%', BASE)

errors = []
def new_page(b, w=1280, h=800):
    pg = b.new_context(viewport={'width': w, 'height': h}, bypass_csp=True).new_page()  # CSP wird nur für die Test-Brücke umgangen
    pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
    pg.add_init_script(MOCK)
    pg.goto('file://' + os.path.abspath(os.path.join(ROOT, 'renderer', 'index.html')))
    return pg
def shot(pg, name): pg.wait_for_timeout(350); pg.screenshot(path=f'{SHOTS}/{name}.png')
def fill(pg, sel, val): pg.fill(sel, val)

try:
  with sync_playwright() as p:
    b = p.chromium.launch()
    # ---------- 1) Einrichtung des Owners mit Pflicht-2FA ----------
    pg = new_page(b)
    pg.wait_for_selector('#authForm')
    assert 'Willkommen bei Zayriox' in pg.inner_text('#auth')
    assert pg.is_hidden('#app'), 'Haupt-App darf vor der Anmeldung nicht sichtbar sein'
    shot(pg, '01_setup')
    fill(pg, 'input[name=username]', 'chef'); fill(pg, 'input[name=email]', 'chef@example.com'); fill(pg, 'input[name=password]', 'kurz')
    pg.click('button[type=submit]'); pg.wait_for_function("document.querySelector('.auth-msg').textContent.length>0")
    assert '10 Zeichen' in pg.inner_text('.auth-msg'), pg.inner_text('.auth-msg')
    PW = 'Owner-Passwort-123'
    fill(pg, 'input[name=password]', PW); pg.click('button[type=submit]')
    pg.wait_for_selector('#secretBox')
    secret = pg.inner_text('#secretBox').replace(' ', '')
    shot(pg, '02_enroll')
    fill(pg, 'input[name=code]', '000000'); pg.click('button[type=submit]'); pg.wait_for_function("document.querySelector('.auth-msg').textContent.includes('falsch')")
    fill(pg, 'input[name=code]', totp(secret)); pg.click('button[type=submit]')
    pg.wait_for_selector('.codes code')
    codes = [c.inner_text() for c in pg.query_selector_all('.codes code')]
    assert len(codes) == 8
    assert pg.is_disabled('#goApp'); pg.check('#savedCodes'); shot(pg, '03_recovery'); pg.click('#goApp')
    pg.wait_for_selector('#app:not([hidden])')
    assert pg.is_visible('#btnOwner'), 'Owner sieht den Owner-Bereich'
    assert 'Zayriox' in pg.title() and 'Syprah' not in pg.content()
    # ---------- 2) Modell herunterladen (Owner) ----------
    pg.wait_for_selector('[data-act=download]'); shot(pg, '04_onboarding')
    pg.click('[data-act=download]'); pg.wait_for_selector('.suggest', timeout=5000)
    assert 'Bereit' in pg.inner_text('#statusPill')
    # ---------- 3) Chat: Pro Max, Streaming, Denken, Quellen ----------
    pg.click('#modeBtn'); pg.click('[data-mode=promax]')
    pg.click('#btnWeb'); assert pg.get_attribute('#btnWeb', 'aria-pressed') == 'true'
    pg.click('#input'); pg.keyboard.type('Was ist Berlin?'); pg.keyboard.press('Enter')
    pg.wait_for_selector('.msg.assistant .think'); assert pg.get_attribute('#btnSend', 'aria-label') == 'Antwort stoppen'
    shot(pg, '05_thinking')
    pg.wait_for_selector('.msg.assistant .sources a', timeout=8000); pg.wait_for_selector('.msg.assistant .code', timeout=8000)
    pg.wait_for_function("document.querySelector('#btnSend').getAttribute('aria-label')==='Senden'", timeout=8000)
    assert 'Berlin – Wikipedia' in pg.inner_text('.sources'); assert 'Pro Max' in pg.inner_text('.msg.assistant .tag')
    shot(pg, '06_answer_sources')
    pg.click('.sources a'); pg.wait_for_timeout(300)
    opened = pg.evaluate('(window.__events||[]).map(e=>e.p)'); assert opened and opened[0].startswith('https://de.wikipedia.org'), opened
    # Suche offline -> Hinweis, Chat läuft weiter
    urllib.request.urlopen(f'{BASE}/search?ok=0').read()
    pg.click('#input'); pg.keyboard.type('nochmal'); pg.keyboard.press('Enter')
    pg.wait_for_selector('.notice', timeout=6000); pg.wait_for_selector('.msg.assistant .md >> nth=1', timeout=6000)
    pg.wait_for_function("document.querySelector('#btnSend').getAttribute('aria-label')==='Senden'", timeout=8000)
    # Stopp-Button
    pg.click('#btnWeb'); pg.click('#input'); pg.keyboard.type('stopp mich'); pg.keyboard.press('Enter')
    pg.wait_for_selector('.think.live'); pg.click('#btnSend'); pg.wait_for_function("document.querySelector('#btnSend').getAttribute('aria-label')==='Senden'", timeout=5000)
    # ---------- 4) Dateien und Bilder ----------
    pg.set_input_files('#file', [{'name': 'notiz.txt', 'mimeType': 'text/plain', 'buffer': b'Hallo Datei'}])
    pg.wait_for_selector('.chip'); assert 'notiz.txt' in pg.inner_text('#chips')
    png = bytes([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]) + bytes(64)
    pg.set_input_files('#file', [{'name': 'bild.png', 'mimeType': 'image/png', 'buffer': png}])
    pg.wait_for_selector('.chip img'); pg.set_input_files('#file', [{'name': 'x.exe', 'mimeType': 'application/octet-stream', 'buffer': b'MZ\x00\x00'}])
    pg.wait_for_selector('.toast.err'); assert 'nicht unterstützt' in pg.inner_text('.toast.err')
    pg.click('#input'); pg.keyboard.type('Fasse zusammen'); pg.keyboard.press('Enter')
    pg.wait_for_function("document.querySelector('#btnSend').getAttribute('aria-label')==='Senden'", timeout=10000)
    # ---------- 5) Owner-Bereich, Step-up, Funktionen ----------
    pg.click('#btnOwner'); pg.wait_for_selector('.tbl'); assert 'chef' in pg.inner_text('.tbl') and 'geschützt' in pg.inner_text('.tbl'); shot(pg, '07_owner_users')
    pg.click('[data-tab=features]'); pg.wait_for_selector('[data-feat=voice]'); shot(pg, '08_owner_features')
    pg.uncheck('[data-feat=voice]'); pg.click('[data-oact=savepolicy]')
    pg.wait_for_selector('#modal2 input[name=password]'); shot(pg, '09_stepup')
    fill(pg, '#modal2 input[name=password]', 'falsches-passwort-1'); fill(pg, '#modal2 input[name=code]', totp(secret, 30000)); pg.click('#modal2 button[type=submit]')
    pg.wait_for_function("document.querySelector('#modal2 .auth-msg').textContent.length>0")
    fill(pg, '#modal2 input[name=password]', PW); fill(pg, '#modal2 input[name=code]', totp(secret, 30000)); pg.click('#modal2 button[type=submit]')
    pg.wait_for_selector('.toast:has-text("Gespeichert")'); pg.wait_for_selector('#modal2', state='hidden')
    assert pg.is_disabled('#btnMic'), 'Voice wurde vom Owner abgeschaltet'
    pg.click('[data-tab=audit]'); pg.wait_for_selector('.logline'); assert 'in Ordnung' in pg.inner_text('#owBody'); shot(pg, '10_audit')
    pg.click('[data-tab=model]'); pg.wait_for_selector('.model.on')
    pg.keyboard.press('Escape')
    # ---------- 6) Abmelden, Anmeldung mit 2FA (Wiederherstellungscode) ----------
    pg.click('#btnLogout'); pg.wait_for_selector('#authForm'); assert pg.is_hidden('#app')
    assert pg.evaluate("document.body.innerText.includes('Owner-Bereich')") is False or pg.is_hidden('#app')
    fill(pg, 'input[name=username]', 'chef'); fill(pg, 'input[name=password]', 'falsch-falsch-1'); pg.click('button[type=submit]')
    pg.wait_for_function("document.querySelector('.auth-msg').textContent.includes('falsch')")
    fill(pg, 'input[name=password]', PW); pg.click('button[type=submit]'); pg.wait_for_selector('input[name=code]'); shot(pg, '11_2fa')
    fill(pg, 'input[name=code]', codes[0]); pg.click('button[type=submit]'); pg.wait_for_selector('#app:not([hidden])')
    assert pg.evaluate('document.querySelectorAll(".chat-item").length') >= 1, 'Chat-Verlauf des Owners wurde geladen'
    # ---------- 7) Zweiter Nutzer: kein Owner-Zugriff ----------
    u = new_page(b); u.wait_for_selector('#authForm'); u.click('[data-go=register]'); u.wait_for_selector('input[name=email]')
    fill(u, 'input[name=username]', 'anna'); fill(u, 'input[name=email]', 'anna@example.com'); fill(u, 'input[name=password]', 'Sicheres-Geheimnis-77'); u.click('button[type=submit]')
    u.wait_for_selector('#app:not([hidden])'); assert u.is_hidden('#btnOwner')
    r = u.evaluate("window.zayriox.adminUsers()"); assert r['code'] == 'FORBIDDEN', r
    r = u.evaluate("window.zayriox.adminPolicySet({features:{uploads:true}})"); assert r['code'] == 'FORBIDDEN', r
    assert u.evaluate('document.querySelectorAll(".chat-item").length') == 0 or 'Noch keine Chats' in u.inner_text('#chatList'), 'Annas Chats sind getrennt'
    assert 'Noch keine Chats' in u.inner_text('#chatList')
    u.click('#input'); u.keyboard.type('Hallo'); u.keyboard.press('Enter'); u.wait_for_selector('.msg.assistant .md', timeout=6000)
    u.click('#btnSettings'); u.wait_for_selector('.card'); shot(u, '12_user_settings')
    u.click('[data-theme=light]'); shot(u, '13_light'); u.keyboard.press('Escape')
    # ---------- 8) Owner sperrt Anna -> sie fliegt sofort raus ----------
    time.sleep(31 - (time.time() % 30))  # nächstes 2FA-Zeitfenster abwarten: jeder Code gilt nur einmal
    pg.click('#btnOwner'); pg.wait_for_selector('.tbl'); pg.click('[data-uact=block]'); pg.click('#modal2 button[data-r="1"]')
    pg.wait_for_selector('#modal2 input[name=password]'); fill(pg, '#modal2 input[name=password]', PW); fill(pg, '#modal2 input[name=code]', totp(secret, 30000)); pg.click('#modal2 button[type=submit]')
    pg.wait_for_selector('.toast:has-text("gesperrt")'); pg.wait_for_selector('.pill.bad')
    u.wait_for_selector('#authForm', timeout=6000); assert u.is_hidden('#app'), 'gesperrter Nutzer wurde abgemeldet'
    # ---------- 8b) Passwortwechsel über die Oberfläche, Limit- und Wartungs-Fehlermeldungen ----------
    b2 = new_page(b); b2.wait_for_selector('#authForm'); b2.click('[data-go=register]'); b2.wait_for_selector('input[name=email]')
    fill(b2, 'input[name=username]', 'bert'); fill(b2, 'input[name=email]', 'bert@example.com'); fill(b2, 'input[name=password]', 'Sicheres-Geheimnis-77'); b2.click('button[type=submit]')
    b2.wait_for_selector('#app:not([hidden])')
    b2.click('#btnSettings'); b2.wait_for_selector('[data-act=pw]'); b2.click('[data-act=pw]'); b2.wait_for_selector('#modal2 input[name=current]')
    fill(b2, '#modal2 input[name=current]', 'falsches-Passwort-1'); fill(b2, '#modal2 input[name=next]', 'Neues-Geheimnis-4711'); b2.click('#modal2 button[type=submit]')
    b2.wait_for_function("document.querySelector('#modal2 .auth-msg').textContent.includes('falsch')")
    fill(b2, '#modal2 input[name=current]', 'Sicheres-Geheimnis-77'); b2.click('#modal2 button[type=submit]')
    b2.wait_for_selector('.toast:has-text("Passwort geändert")'); b2.keyboard.press('Escape'); b2.keyboard.press('Escape')
    b2.click('#btnLogout'); b2.wait_for_selector('#authForm')
    fill(b2, 'input[name=username]', 'bert'); fill(b2, 'input[name=password]', 'Sicheres-Geheimnis-77'); b2.click('button[type=submit]')
    b2.wait_for_function("document.querySelector('.auth-msg').textContent.includes('falsch')")
    fill(b2, 'input[name=password]', 'Neues-Geheimnis-4711'); b2.click('button[type=submit]'); b2.wait_for_selector('#app:not([hidden])')
    # Owner setzt Limit auf 1 (Step-up aus 8) -> zweite Nachricht zeigt verständliche Meldung
    pg.click('[data-close]') if pg.is_visible('[data-close]') else None
    pg.click('#btnOwner'); pg.click('[data-tab=features]'); pg.wait_for_selector('#limMsg'); fill(pg, '#limMsg', '1'); pg.click('[data-oact=savepolicy]'); pg.wait_for_selector('.toast:has-text("Gespeichert")')
    b2.click('#input'); b2.keyboard.type('Erste'); b2.keyboard.press('Enter'); b2.wait_for_selector('.msg.assistant .md', timeout=6000)
    b2.wait_for_function("document.querySelector('#btnSend').getAttribute('aria-label')==='Senden'", timeout=8000)
    b2.click('#input'); b2.keyboard.type('Zweite'); b2.keyboard.press('Enter'); b2.wait_for_selector('.msg.assistant .err', timeout=5000)
    assert 'Tageslimit' in b2.inner_text('.err'), b2.inner_text('.err'); shot(b2, '15_limit_fehler')
    # Wartungsmodus
    fill(pg, '#limMsg', '500'); pg.check('#mainOn'); fill(pg, '#mainMsg', 'Wir bauen gerade um.'); pg.click('[data-oact=savepolicy]'); pg.wait_for_selector('.toast:has-text("Gespeichert") >> nth=-1')
    b2.click('#input'); b2.keyboard.type('Dritte'); b2.keyboard.press('Enter'); b2.wait_for_function("document.querySelectorAll('.msg.assistant .err').length>=2", timeout=5000)
    assert 'Wir bauen gerade um' in b2.inner_text('.msg.assistant:last-child .err'); shot(b2, '16_wartung_fehler')
    # ---------- 9) Schmales Fenster ----------
    n = new_page(b, 700, 700); n.wait_for_selector('#authForm'); shot(n, '14_narrow_login')
    b.close()
finally:
    proc.terminate()
bad = [e for e in errors if 'Failed to load resource' not in e]
print('FEHLER IN DER KONSOLE:', bad if bad else 'keine')
print('UI-TEST OK' if not bad else 'UI-TEST MIT KONSOLENFEHLERN')
sys.exit(1 if bad else 0)
