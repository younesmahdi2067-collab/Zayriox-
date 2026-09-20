# Übergabe-Notiz für die Weiterarbeit (Stand des Zayriox-Projekts)

Zayriox = lokale KI-Desktop-App für Windows (Electron + node-llama-cpp + Qwen2.5, Konten/2FA/Owner-System). Sprache der Oberfläche: Deutsch.

## Wichtig
- **Es wurde noch NIE ein echter Windows-Build erzeugt und NIE eine `Zayriox_Setup.exe` getestet.** Die Entwicklungsumgebung hatte kein Windows, kein npm-/GitHub-/HuggingFace-Zugang.
- Nie behaupten, die App sei fertig, bevor der GitHub-Workflow `.github/workflows/build-windows.yml` auf `windows-latest` grün durchgelaufen ist.

## Was geprüft wurde (in der Sandbox)
- `npm test` (`scripts/test.mjs`): 105 Tests grün – Konten, scrypt, TOTP-2FA (RFC-Vektoren), Recovery-Codes, Sessions/Timeouts, Login-Sperre, Step-up, Owner-Schutz,
  Rechte-Fuzzing (Nutzer werden nie Owner), manipulierte Kontodatei, Audit-Hash-Kette, Limits/Wartungsmodus/Funktions-Schalter, Websuche-Parser + Wikipedia-Ausweichquelle (mit Fake-Netz),
  Upload-Prüfung, Fehlertexte, Secrets-/CSP-/localhost-Scan, echte Testdateien (PDF/PNG/WAV) als Generatoren.
- `scripts/ui/run.py` (Playwright/Chromium, nur Dev-Werkzeug): echte Oberfläche + echtes Backend mit **Fake-KI**: Owner-Setup mit 2FA, Recovery-Codes, Chat/Streaming/Stopp/Denkstufen,
  Quellen, Upload, Owner-Bereich mit Step-up, Sperren, Passwortwechsel, Limit-/Wartungs-Fehlermeldungen. (Ein Lauf war einmal wegen Timing rot, spätere Läufe grün – evtl. flaky.)
- Dabei gefundene und behobene Fehler: Owner-Button für Nutzer sichtbar (`[hidden]`), Einstellungs-Buttons reagierten nicht (`closest('[data-theme]')` traf `<html>`), zwei kleine Berechtigungs-Reihenfolgen.

## NICHT geprüft (nur Code vorhanden)
- Electron-Start, Installer (`electron-builder`/NSIS), Desktop-Verknüpfung, IPC-Absenderprüfung im echten Electron
- echte KI (`node-llama-cpp` + Modell), PDF-Parsing (`pdf-parse`), Bildanalyse (`@huggingface/transformers`, SmolVLM), Spracherkennung (Whisper), echte Websuche (DuckDuckGo/Wikipedia), Mikrofon, Vorlesen

## Selbsttest im echten Build
`src/selftest.js` (`Zayriox.exe --selftest --selftest-out=… [--selftest-model=…] [--selftest-full] [--selftest-wav=…]`) prüft in der echten App: Fenster lokal (file://), kein Node in der UI,
echte IPC, fremde Seite abgewiesen, UI-gesteuerte Owner-Einrichtung, Sicherheitsfälle, Secrets-Scan, echte KI (Streaming, Denkstufen, Stopp, Verlauf), mit `--selftest-full` zusätzlich
PDF/TXT/Code, Bild, Websuche, Voice, sowie „keine lauschenden Ports“.
**Noch offen:** Der Workflow ruft bisher nur `--selftest` (+ Modell) auf. Zu ergänzen: `--selftest-full` mit WAV-Datei (per Windows-SAPI erzeugt), Rauchtest mit normalem Start
(Prozesse/Ports/Fenstertitel), Workflow-Eingabe zum Überspringen der erweiterten Tests, Artifact-Freigabe nur bei allen grünen Tests.

## Noch nicht gebaut
Bezahlung/Tarife, Auto-Update, QR-Code für 2FA, Code-Signierung, Server-/Mehrgeräte-Betrieb.

## Neu in diesem Stand
- Der GitHub-Windows-Workflow führt nach dem Installer-Build jetzt den erweiterten Selbsttest mit `--selftest-full` aus.
- Der Workflow erzeugt auf Windows per SAPI eine echte WAV-Testdatei und prüft damit die Spracherkennung.
- Zusätzlich wird der installierte Build mit normalem Start als Rauchtest gestartet; ein Fenster mit `Zayriox` im Titel muss erscheinen.
- Der Installer/Artifact wird erst nach diesen Schritten hochgeladen; bei einem roten Pflichtschritt wird der Build nicht als erfolgreich abgeschlossen betrachtet.

## Ordner
src/ (Hauptprozess, API, Sicherheit, KI) · renderer/ (Oberfläche) · scripts/ (Tests) · .github/workflows/ (Windows-Build) · assets/icon.png

## Prüfung durch Claude (nach dem ChatGPT-Stand)
Gefunden und behoben:
1. `npm test` war rot (der neue Kanal `auth:qr` fehlte in der Test-Erlaubnisliste) -> der GitHub-Workflow wäre bei „Logik-Tests“ abgebrochen.
2. `import { autoUpdater } from 'electron-updater'` (CommonJS in ESM) kann den App-Start abstürzen lassen -> Default-Import + Destrukturierung.
3. `qrcode` wurde beim Start statisch importiert -> jetzt erst bei Bedarf geladen; fehlt es, zeigt die UI den Schlüssel zum Abtippen.
4. `npm run dist` ohne `--publish never` hätte bei Tag-Builds ohne GH_TOKEN versagt -> ergänzt.
Tests: 107 grün (`npm test`), UI-Test mit Chromium grün. Weiterhin NICHT geprüft: echter Windows-Build/Installer/KI/Bild/Web/Voice (erst durch den GitHub-Lauf).
Offene Punkte: SAPI-WAV-Format im Workflow evtl. anpassen (`$stream.Format`), Update-Status in der UI anzeigen, Signierung.

## Runde 3: Vorbereitung für den ersten grünen Windows-Lauf (ohne Ausführung möglich gewesen)
Gefunden durch Code-Durchsicht und behoben:
1. **`npm test` wäre unter Windows sofort gescheitert:** `import('C:\\…')` wird von Node abgelehnt -> Tests nutzen jetzt `file://`-URLs (20 Stellen).
2. **PowerShell `ExitCode` kann bei `Start-Process -PassThru` `$null` sein** -> `$null = $p.Handle` ergänzt (sonst falsches „rot“).
3. **Streaming-Test im Selbsttest:** In einem versteckten Fenster pausiert `requestAnimationFrame` -> Selbsttest nutzt sichtbares Fenster + `backgroundThrottling:false`.
4. Selbsttest-Timeouts von 10 auf 40 Minuten (Modell-/Bild-/Sprachmodell-Downloads + 3 Denkstufen auf CI-CPU).
5. Nach der stillen Installation wird eine evtl. automatisch gestartete App-Instanz beendet, bevor der Selbsttest der installierten App läuft.
6. Rauchtest prüft zusätzlich den Prozessbaum (kein cmd/conhost/Browser) und offene TCP-Ports.
7. Workflow-Eingabe **`skip_extended`**: Wenn Bild/Web/Voice-Tests an externen Diensten scheitern, lässt sich der Lauf mit „nur Kerntests“ starten; das Artifact heißt dann `Zayriox_Setup_NUR_KERNTESTS` (klar gekennzeichnet).
8. Diagnose: App-Logs (`st1/logs`, `st2/logs`) und Selbsttest-JSON werden immer hochgeladen (auch bei rotem Lauf).
9. `renameSync` mit Wiederholung bei EPERM/EBUSY (Windows-Virenscanner).
Weiterhin: **kein echter Windows-Lauf durchgeführt.** Erwartbare Stolpersteine beim ersten Lauf: `node-llama-cpp`/`onnxruntime`-Verpackung in `asarUnpack`, Bild-/Sprachmodell-API-Details (`src/ml.js`), DuckDuckGo-Blockade (Ausweichquelle Wikipedia vorhanden), SAPI-WAV-Format.
