# Modular Bot Setup

Der Quing Corporation Bot ist jetzt modular aufgebaut und kann verschiedene Features einfach aktivieren/deaktivieren.

## 🎛️ Feature-Kontrolle

### Aktivierte Features (Standard)
- **Schedule Detection** - Automatische Erkennung von Streaming-Schedules aus Bildern
- **Debug Tools** - Debug-Befehle für Staff-Mitglieder

### Deaktivierte Features (Standard)
- **Whitelist Management** - Minecraft Whitelist-Verwaltung
- **Role Management** - Discord-Rollen-Verwaltung

## 🔧 Konfiguration

### 1. Basis-Konfiguration (immer erforderlich)
```env
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_discord_guild_id_here
ADMIN_ROLE_ID=admin_role_id_here
MOD_ROLE_ID=mod_role_id_here
```

### 2. Schedule Detection (Standard aktiviert)
```env
SCHEDULE_CHANNEL_ID=schedule_channel_id_here
SCHEDULE_EMOJI_ID=your_emoji_id_here
ANNOUNCEMENT_CHANNEL_ID=announcement_channel_id_here
```

### 3. Minecraft Features (Standard deaktiviert)
Um Minecraft-Features zu aktivieren, kommentiere diese Zeilen aus:
```env
WHITELIST_CHANNEL_ID=whitelist_channel_id_here
MOD_CHANNEL_ID=mod_channel_id_here
WHITELIST_ROLE_ID=your_whitelist_role_id_here
RCON_HOST=host.docker.internal
RCON_PORT=25575
RCON_PASSWORD=your_rcon_password_here
```

## 🚀 Verwendung

### Nur Schedule Detection (Empfohlen)
```env
# Basis-Konfiguration
DISCORD_TOKEN=your_token
DISCORD_GUILD_ID=your_guild_id
ADMIN_ROLE_ID=admin_role_id
MOD_ROLE_ID=mod_role_id

# Schedule Detection
SCHEDULE_CHANNEL_ID=schedule_channel_id
SCHEDULE_EMOJI_ID=emoji_id
ANNOUNCEMENT_CHANNEL_ID=announcement_channel_id

# Minecraft Features auskommentiert = deaktiviert
# WHITELIST_CHANNEL_ID=...
# MOD_CHANNEL_ID=...
```

### Vollständige Konfiguration (mit Minecraft)
```env
# Basis-Konfiguration
DISCORD_TOKEN=your_token
DISCORD_GUILD_ID=your_guild_id
ADMIN_ROLE_ID=admin_role_id
MOD_ROLE_ID=mod_role_id

# Schedule Detection
SCHEDULE_CHANNEL_ID=schedule_channel_id
SCHEDULE_EMOJI_ID=emoji_id
ANNOUNCEMENT_CHANNEL_ID=announcement_channel_id

# Minecraft Features aktiviert
WHITELIST_CHANNEL_ID=whitelist_channel_id
MOD_CHANNEL_ID=mod_channel_id
WHITELIST_ROLE_ID=whitelist_role_id
RCON_HOST=host.docker.internal
RCON_PORT=25575
RCON_PASSWORD=rcon_password
```

## 📦 Container Setup

### Nur Bot (Schedule Detection)
```bash
# Container neu bauen
docker-compose build --no-cache

# Container starten
docker-compose up -d
```

### Mit Datenbank (Minecraft Features)
```bash
# Alle Services starten
docker-compose up -d quingcorporation-db quingcorporation-bot
```

## 🔍 Logs prüfen

```bash
# Bot-Logs anzeigen
docker-compose logs -f quingcorporation-bot

# Geladene Cogs prüfen
# Suche nach: "✅ Schedule detection cog loaded"
# Suche nach: "⏭️ Whitelist management disabled"
```

## ✅ Verfügbare Befehle

### Schedule Detection
- Automatische Bildverarbeitung im Schedule-Channel
- `/schedule_test` - Test mit Bild-URL
- `/schedule_reload` - Konfiguration neu laden

### Debug Tools
- `/debug` - Bot-Status prüfen
- `/debug_info` - Detaillierte Bot-Informationen (Staff only)

### Minecraft Features (nur wenn aktiviert)
- `/whitelist` - Whitelist beantragen
- `/role` - Rollen verwalten

## 🎯 Vorteile der modularen Struktur

1. **Flexibilität** - Features können einfach aktiviert/deaktiviert werden
2. **Performance** - Nur benötigte Features werden geladen
3. **Wartbarkeit** - Klare Trennung der Funktionalitäten
4. **Skalierbarkeit** - Neue Features können einfach hinzugefügt werden
5. **Rate Limiting** - Weniger Discord API-Aufrufe durch deaktivierte Features

## 🔧 Troubleshooting

### Feature wird nicht geladen
- Prüfe Umgebungsvariablen in `.env`
- Prüfe Bot-Logs auf Fehlermeldungen
- Stelle sicher, dass die entsprechenden Channel-IDs korrekt sind

### Bot startet nicht
- Prüfe `DISCORD_TOKEN` und `DISCORD_GUILD_ID`
- Stelle sicher, dass alle erforderlichen Umgebungsvariablen gesetzt sind
- Prüfe Container-Logs: `docker-compose logs quingcorporation-bot` 