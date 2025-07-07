# Quing Corporation Discord Bot

A Discord bot for managing Minecraft server whitelist requests through RCON and automatic streaming schedule detection with interactive approval workflow using GPT-4 Vision AI.

## Features

- Whitelist request system with Mojang username verification
- Moderation approval system
- PostgreSQL database integration
- RCON server command execution
- **NEW: AI-powered streaming schedule detection from images using GPT-4 Vision**
- **NEW: Staff approval workflow for schedule posts**
- **NEW: Automatic posting to announcement channel**
- English language support

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Discord Bot Token
- Minecraft Server with RCON enabled
- Discord Server with appropriate permissions
- **NEW: OpenAI API Key (for GPT-4 Vision schedule detection)**

## Installation

### Docker Installation (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/quingcorporation-bot.git
cd quingcorporation-bot
```

2. **AI-powered Schedule Detection is automatically included in Docker!**
   - GPT-4 Vision API integration ist bereits konfiguriert
   - Alle Dependencies sind bereits installiert

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
- **NEW: OpenAI API Key (required for schedule detection)**
- **NEW: Schedule Channel ID, Emoji ID, and Announcement Channel ID**

5. Build and start the containers:
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/quingcorporation-bot.git
cd quingcorporation-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. **Get OpenAI API Key (for AI-powered schedule detection):**
   - Visit [OpenAI Platform](https://platform.openai.com/api-keys)
   - Create a new API key
   - Add it to your `.env` file as `OPENAI_API_KEY`

4. Copy `.env.example` to `.env` and fill in your configuration:
```bash
cp .env.example .env
```

5. Edit the `.env` file with your credentials:
- Discord Bot Token
- Discord Guild ID
- Mod Channel ID
- RCON Host, Port, and Password
- Database credentials
- **NEW: OpenAI API Key (required for schedule detection)**
- **NEW: Schedule Channel ID, Emoji ID, and Announcement Channel ID**

## Usage

1. Start the bot:
```bash
# Docker
docker-compose up -d

# Manual
python -m src.bot
```

2. Use the `/whitelist` command in your Discord server to start the whitelist process.

3. **NEW: AI-Powered Schedule Workflow:**
   - Post schedule images in the configured schedule channel
   - Bot uses GPT-4 Vision to analyze image and extract structured data
   - Bot creates formatted message with extracted events
   - Staff can approve (✅) or reject (❌) the schedule
   - Approved schedules are automatically posted to announcement channel

## Bot Commands

- `/whitelist` - Start the whitelist request process
- **NEW: `/schedule_test` - Test schedule detection with image URL**
- **NEW: `/schedule_reload` - Reload schedule detector configuration**

## Moderation

Moderators can approve or reject whitelist requests by reacting with:
- ✅ - Approve request
- ❌ - Reject request

## AI-Powered Schedule Detection Workflow

The bot provides an interactive workflow for schedule management using GPT-4 Vision AI:

### 1. Image Submission
- **Post an image** with a weekly schedule in the configured schedule channel
- **Bot automatically processes** the image using GPT-4 Vision AI
- **AI extracts structured data** (dates, times, events) and converts to XML
- **Review message is posted** with original image + formatted text

### 2. Staff Review
- **Staff members can review** the AI-generated schedule
- **React with ✅** to approve and post to announcement channel
- **React with ❌** to reject and discard the schedule

### 3. Final Action
- **Approved schedules** are posted to the announcement channel with the original image
- **Rejected schedules** are discarded and the workflow ends

### AI Processing Details
- **GPT-4 Vision** analyzes the image and extracts all schedule information
- **Structured XML output** ensures consistent data format
- **Automatic timezone handling** (converts to UTC)
- **Robust event detection** even with complex layouts

### Status Indicators
- **⏳ Processing** - Image is being processed by AI
- **✅ Approve** - Schedule approved and posted
- **❌ Reject** - Schedule rejected and discarded
- **⚠️ Error** - Processing error occurred

For detailed information, see:
- [SCHEDULE_DETECTION.md](SCHEDULE_DETECTION.md) - General documentation
- [DOCKER_SCHEDULE_SETUP.md](DOCKER_SCHEDULE_SETUP.md) - Docker-specific setup

## License

MIT License 