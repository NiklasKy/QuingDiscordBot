# QuingCraft Discord Bot

A Discord bot for managing Minecraft server whitelist requests through RCON.

## Features

- Whitelist request system with Mojang username verification
- Moderation approval system
- PostgreSQL database integration
- RCON server command execution
- English language support

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Discord Bot Token
- Minecraft Server with RCON enabled
- Discord Server with appropriate permissions

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/quingcraft-bot.git
cd quingcraft-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your configuration:
```bash
cp .env.example .env
```

4. Edit the `.env` file with your credentials:
- Discord Bot Token
- Discord Guild ID
- Mod Channel ID
- RCON Host, Port, and Password
- Database credentials

5. Set up the PostgreSQL database:
```sql
CREATE DATABASE quingcraft;
```

## Usage

1. Start the bot:
```bash
python -m src.bot
```

2. Use the `/whitelist` command in your Discord server to start the whitelist process.

## Bot Commands

- `/whitelist` - Start the whitelist request process

## Moderation

Moderators can approve or reject whitelist requests by reacting with:
- ✅ - Approve request
- ❌ - Reject request

## License

MIT License 