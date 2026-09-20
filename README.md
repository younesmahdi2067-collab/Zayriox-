# Zayriox – lokale KI-Desktop-App für Windows

Echte Desktop-App (Electron). **Kein Browser, kein localhost, kein CMD-Fenster.** Die Oberfläche spricht über eine interne
Electron-Brücke (IPC) mit dem Hauptprozess; es gibt keinen Webserver. Die KI (Qwen2.5, Apache-2.0) läuft direkt in der App (llama.cpp).

> **Dies ist der Quellcode. `Zayriox_Setup.exe` entsteht erst durch den Windows-Build (unten).**
> In der Entwicklungsumgebung, in der dieses Projekt geschrieben wurde, war kein Windows-Build möglich (kein Windows/Wine/NSIS, kein npm-Zugang).

## Die echte `Zayriox_Setup.exe` erzeugen

**Weg A – ohne Vorkenntnisse (GitHub):** (Handstart mit Haken „skip_extended“ = nur Kerntests; Artifact heißt dann `Zayriox_Setup_NUR_KERNTESTS`)
1. Kostenloses GitHub-Konto → neues, **privates** Repository → diesen Ordner hochladen.
2. Reiter **Actions → „Zayriox Windows-Build“ → Run workflow**.
3. Der Workflow läuft auf einem echten Windows-Rechner und macht: `npm install` → Tests → **Installer bauen** → **Selbsttest der App mit echtem Fenster,
   Konten/2FA und echter KI-Antwort** → **Installer wirklich still installieren** und Desktop-Verknüpfung prüfen → Selbsttest der installierten App.
4. Nur wenn alles grün ist, erscheint unter **Artifacts** die `Zayriox_Setup.exe`. Bei rotem Haken steht im Protokoll, was schiefging – dann melde dich mit dem Text.

**Weg B – eigener Windows-PC:** Node.js 20 installieren, dann `npm install`, `npm test`, `npm run dist` → `dist\Zayriox_Setup.exe`.
Selbsttest: `npm run selftest`.

## Nutzung
Doppelklick auf `Zayriox_Setup.exe` → installiert ohne Rückfragen (ohne Admin-Rechte), legt die Desktop-Verknüpfung an und startet Zayriox.
Erster Start: Loading-Screen → **Owner-Konto anlegen** (Pflicht-2FA mit Authenticator-App) → KI-Modell einmalig herunterladen (ca. 400 MB) → chatten.
Windows-SmartScreen warnt bei unsignierten Installern („Weitere Informationen → Trotzdem ausführen“). Ein Signatur-Zertifikat kostet Geld.

## Funktionen
- Loading-Screen, dunkles ChatGPT-ähnliches Design (auch Hell), Chat mit Streaming/Stopp, Markdown + Code, Verlauf/Suche/Umbenennen/Löschen
- Denkstufen Auto · Schnell · Mittel · Hoch · Pro Max (Hoch/Pro Max: sichtbares Nachdenken, Entwurf, Selbstkorrektur)
- Dateien: TXT, Code, PDF (Textebene) · Bilder: lokales Bildmodell (SmolVLM-256M) beschreibt das Bild, das Textmodell antwortet
- Websuche AN/AUS mit Quellen unter der Antwort (DuckDuckGo ohne Schlüssel oder Brave-API mit verschlüsseltem Schlüssel)
- Voice: Mikrofon → lokale Spracherkennung (Whisper-base), Vorlesen über Windows-Stimmen
- Konten: Registrierung, Login, Logout, Passwortwechsel, 2FA, Konto löschen; Chats getrennt pro Konto
- Owner-Bereich: Benutzer sperren/entsperren/löschen, Funktionen an/aus, Denkstufen an/aus, Tageslimits, Wartungsmodus, Modelle, Suchanbieter/-schlüssel, Sicherheitsprotokoll

## Sicherheitsmodell (ehrlich)
Die Oberfläche gilt als **nicht vertrauenswürdig**. Jede Aktion wird im Hauptprozess geprüft (`src/api.js`, `src/auth.js`, `src/admin.js`).
- Passwörter: scrypt mit Salt, nie im Klartext. Login-Sperre mit steigender Wartezeit, gleiche Fehlermeldung für „Nutzer unbekannt“/„Passwort falsch“.
- 2FA (TOTP, RFC 6238) ist für den Owner **Pflicht**; Codes gelten nur einmal (Replay-Schutz); Wiederherstellungscodes einmalig; 2FA-Geheimnisse verschlüsselt (Windows DPAPI).
- Sitzungen leben nur im Hauptprozess (die Oberfläche kennt keinen Token), Leerlauf-Timeout (Owner 10 min, Nutzer 30 min), sofortiges Ende bei Sperre/Passwortwechsel.
- Owner-Rolle: genau einer, entsteht nur bei der Ersteinrichtung; keine Funktion befördert oder erstellt einen weiteren Owner. Rolle wird bei jedem Aufruf aus der Kontodatei gelesen, nie von der Oberfläche.
- Kritische Owner-Aktionen verlangen erneut Passwort + frischen 2FA-Code (Step-up, 5 min gültig).
- Kontodatei ist per HMAC signiert (Schlüssel im Windows-Tresor). Manuelle Änderung (z. B. Rolle → owner) wird erkannt, Anmeldungen werden gesperrt.
- Audit-Log als Hash-Kette (Manipulation erkennbar); enthält nie Passwörter, Codes oder Chat-Inhalte.
- API-Schlüssel nur im Hauptprozess, verschlüsselt, nie zurück an die Oberfläche. Strikte CSP, Sandbox, kein Node in der Oberfläche, IPC nur aus eigenen App-Dateien, Uploads/Bilder/Audio werden geprüft.

**Grenze:** Zayriox läuft lokal. Wer Administrator-Rechte auf dem Windows-Konto hat oder Schadsoftware unter demselben Windows-Benutzer laufen lässt, kann
lokale Daten grundsätzlich angreifen. Für echte Mehrbenutzer-Sicherheit über mehrere Geräte bräuchte es einen Server.

## Neu in diesem Stand
- QR-Code für die 2FA-Einrichtung (Schlüssel bleibt als Ausweichlösung zum Abtippen sichtbar)
- Auto-Update über GitHub-Releases (`electron-updater`): Die Oberfläche zeigt den Update-Status noch nicht an (`onUpdate` ist in der Brücke, aber nicht verdrahtet).
  **Sicherheitshinweis:** Solange der Installer nicht signiert ist, sollte Auto-Update nur mit einem vertrauenswürdigen, privaten/abgesicherten Release-Prozess genutzt werden.
- Tarifkatalog (`src/tariffs.js`): reine Anzeige-/Konfigurationsdaten. Es gibt **keine** Bezahlung und keine Durchsetzung von Tarifen.

## Nicht enthalten
Echte Bezahlung/Tarif-Durchsetzung, Anzeige des Update-Status in der Oberfläche, Server-/Mehrgeräte-Betrieb, Code-Signierung des Installers.

## Ordner
```
src/       main.js (Fenster, IPC) · api.js (alle erlaubten Aktionen) · auth.js/admin.js/accounts.js/totp.js/vault.js/audit.js/policy.js (Sicherheit)
           engine.js/pipeline.js/modes.js/models.js (KI) · search.js/ml.js/media.js (Web, Bild, Sprache) · selftest.js · preload.cjs
renderer/  index.html · styles.css · core.js/auth.js/app.js/owner.js · markdown.js · splash.html
scripts/   test.mjs (npm test) · ui/ (Oberflächen-Test mit Chromium, nur Entwicklung)
```
