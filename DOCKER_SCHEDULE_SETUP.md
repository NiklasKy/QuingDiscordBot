# Docker Setup für Schedule Detection

Diese Anleitung erklärt, wie du die Schedule Detection Funktionalität in deinem Docker-Container einrichtest.

## 🐳 Docker-Container Setup

### Automatische Installation

Die Schedule Detection ist bereits vollständig in das Dockerfile integriert. Der Container installiert automatisch:

- **Tesseract OCR** (Hauptprogramm)
- **Tesseract OCR Eng** (Englische Sprachpakete)
- **Tesseract OCR Deu** (Deutsche Sprachpakete)
- **OpenCV Dependencies** (für Bildverarbeitung)
- **Python Dependencies** (pytesseract, opencv-python, etc.)

### Container neu bauen

Nach dem Update musst du den Container neu bauen:

```bash
# Container stoppen
docker-compose down

# Container neu bauen
docker-compose build --no-cache

# Container starten
docker-compose up -d
```

## 🔧 Konfiguration

### 1. Environment Variables

Füge diese Variablen zu deiner `.env` Datei hinzu:

```env
# Schedule Detection Configuration
SCHEDULE_CHANNEL_ID=your_schedule_channel_id_here
SCHEDULE_EMOJI_ID=your_emoji_id_here
ANNOUNCEMENT_CHANNEL_ID=your_announcement_channel_id_here
```

### 2. Discord Channel Setup

#### Schedule Channel
1. Erstelle einen Discord-Channel für Schedule-Posts
2. Hole dir die Channel-ID (Rechtsklick → ID kopieren)
3. Setze `SCHEDULE_CHANNEL_ID` in deiner `.env` Datei
4. Stelle sicher, dass der Bot folgende Berechtigungen hat:
   - Nachrichten lesen
   - Nachrichten senden
   - Reaktionen hinzufügen
   - Dateien anhängen

#### Announcement Channel
1. Erstelle einen Discord-Channel für Ankündigungen
2. Hole dir die Channel-ID (Rechtsklick → ID kopieren)
3. Setze `ANNOUNCEMENT_CHANNEL_ID` in deiner `.env` Datei
4. Stelle sicher, dass der Bot folgende Berechtigungen hat:
   - Nachrichten senden
   - Dateien anhängen
   - Embeds senden

### 3. Emoji Setup

1. Lade ein Custom-Emoji auf deinen Discord-Server hoch
2. Hole dir die Emoji-ID (Rechtsklick → ID kopieren)
3. Setze `SCHEDULE_EMOJI_ID` in deiner `.env` Datei

## 🚀 Verwendung

### Interaktiver Workflow

1. **Bild posten**: Poste ein Bild mit einem Wochenplan in den konfigurierten Schedule-Channel
2. **Automatische Verarbeitung**: Der Bot verarbeitet das Bild und erstellt eine formatierte Nachricht
3. **Review & Approval**: Der Bot postet das ursprüngliche Bild + formatierte Nachricht mit Reaktions-Buttons
4. **Staff-Entscheidung**: Staff-Mitglieder können mit ✅ (Approve) oder ❌ (Reject) reagieren
5. **Finale Aktion**:
   - **✅ Approve**: Nachricht wird in den Ankündigungskanal gepostet
   - **❌ Reject**: Workflow wird abgebrochen, Nachricht wird verworfen

### Reaktions-Status

- **⏳ Processing**: Bild wird verarbeitet
- **✅ Approve**: Nachricht genehmigen und in Ankündigungskanal posten
- **❌ Reject**: Nachricht ablehnen und verwerfen
- **⚠️ Error**: Fehler bei der Verarbeitung

### Test Commands

- `/schedule_test` - Test mit Bild-URL
- `/schedule_reload` - Konfiguration neu laden

## 🔍 Troubleshooting

### Container-Logs prüfen

```bash
# Logs des Bot-Containers anzeigen
docker-compose logs -f quingcorporation-bot

# Oder spezifisch nach Schedule-Fehlern suchen
docker-compose logs quingcorporation-bot | grep -i schedule
```

### Tesseract im Container testen

```bash
# Container betreten
docker-compose exec quingcorporation-bot bash

# Tesseract testen
tesseract --version

# Python-Integration testen
python -c "import pytesseract; print('Tesseract verfügbar')"
```

### Häufige Probleme

1. **"Tesseract not found"**
   - Container neu bauen: `docker-compose build --no-cache`
   - Prüfe Container-Logs auf Installationsfehler

2. **"No text extracted"**
   - Prüfe Bildqualität und Kontrast
   - Stelle sicher, dass das Bild im richtigen Channel gepostet wurde

3. **"Could not parse date range"**
   - Prüfe das Datumsformat im Bild
   - Unterstützte Formate: "30 June - 06 July", "30/06 - 06/07"

4. **"Announcement channel not found"**
   - Prüfe ANNOUNCEMENT_CHANNEL_ID in .env
   - Stelle sicher, dass der Bot Zugriff auf den Channel hat

## 📋 Unterstützte Formate

### Datumsbereiche
- `30 June - 06 July`
- `30/06 - 06/07`
- `30-06 - 06-07`

### Zeitformate
- `15:00 UTC`
- `15:00 CET`
- `15:00 CEST`
- `15:00` (nimmt UTC an)

### Event-Titel
- `The devil in me - with Jade`
- `PEAK Collab - with XYZ`
- Beliebiger Text nach der Zeit

### Tageserkennung
- Monday/Mon
- Tuesday/Tue/Tues
- Wednesday/Wed
- Thursday/Thu/Thurs
- Friday/Fri
- Saturday/Sat
- Sunday/Sun

## 🎯 Workflow-Beispiel

### 1. Benutzer postet Bild
```
[Benutzer postet Schedule-Bild im Schedule-Channel]
```

### 2. Bot erstellt Review-Nachricht
```
📅 Schedule Detection Result
The bot has detected and formatted a schedule from your image. Please review and approve or reject.

Formatted Schedule:
💜 [30 June - 06 July] 💚

<a:emoji_name:emoji_id> The devil in me - with Jade
<t:1751295600>

Submitted by: @User (Username)

Actions:
✅ Approve - Post to announcement channel
❌ Reject - Discard this schedule

React with ✅ to approve or ❌ to reject
[Ursprüngliches Bild als Attachment]
```

### 3. Staff reagiert
```
[Staff-Mitglied reagiert mit ✅ oder ❌]
```

### 4. Finale Aktion
**Bei ✅ Approve:**
```
📅 Weekly Streaming Schedule
💜 [30 June - 06 July] 💚

<a:emoji_name:emoji_id> The devil in me - with Jade
<t:1751295600>

Approved by StaffMember
[Ursprüngliches Bild als Attachment]
```
**Wird im Ankündigungskanal gepostet**

**Bei ❌ Reject:**
```
Status: ❌ Rejected by StaffMember
Schedule discarded
```
**Workflow wird abgebrochen**

## 🔒 Sicherheit

- Der Bot verarbeitet nur Bilder im konfigurierten Schedule-Channel
- Nur Staff-Mitglieder können Schedule genehmigen/ablehnen
- Bildverarbeitung erfolgt lokal im Container
- Temporäre Bilddaten werden nicht permanent gespeichert
- Reaktionen werden nach der Entscheidung entfernt

## 📈 Performance

- OCR-Verarbeitung dauert 2-5 Sekunden pro Bild
- Große Bilder werden automatisch für die Verarbeitung angepasst
- Mehrere Bilder in einer Nachricht werden sequenziell verarbeitet
- Fehlgeschlagene Verarbeitungsversuche werden für Debugging protokolliert
- Pending Schedules werden im Speicher gehalten bis zur Entscheidung 