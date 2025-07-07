# AI-Powered Streaming Schedule Detection

This feature automatically detects and formats streaming schedules from images posted in Discord channels using GPT-4 Vision AI.

## Overview

The bot monitors a designated channel for images containing weekly streaming schedules. When an image is posted, the bot:

1. Downloads and processes the image using GPT-4 Vision AI
2. Extracts structured data (dates, times, events) and converts to XML
3. Parses the XML to extract schedule information
4. Posts a formatted message with the schedule
5. Provides interactive approval workflow for staff

## Features

### 🤖 AI-Powered Processing
- **GPT-4 Vision**: Uses OpenAI's latest vision model for image analysis
- **Structured Output**: AI returns data in consistent XML format
- **Robust Recognition**: Handles complex layouts and various image styles
- **Automatic Timezone**: Converts all times to UTC automatically

### 📥 Input Processing
- **Image Recognition**: Automatically detects images posted in the schedule channel
- **AI Analysis**: Uses GPT-4 Vision for intelligent text and layout recognition
- **Multiple Formats**: Supports various image formats (PNG, JPG, etc.)
- **High Accuracy**: Much more reliable than traditional OCR

### 🎯 Output Format
The bot generates formatted Discord messages like:

```
📅 **Streaming Schedule: 30 June - 06 July 2024**

**Monday**
🕐 **18:00** - The devil in me - with Jade

**Wednesday**
🕐 **20:00** - PEAK Collab - with XYZ
   Building a new castle

**Friday**
🕐 **19:00** - Gaming Stream
```

### 🔧 Technical Requirements

#### Dependencies
- `openai` - GPT-4 Vision API integration
- `Pillow` - Image manipulation
- `python-dateutil` - Date parsing
- `pytz` - Timezone handling
- `xml.etree.ElementTree` - XML parsing

#### API Requirements
- **OpenAI API Key**: Required for GPT-4 Vision access
  - Get from: https://platform.openai.com/api-keys
  - Add to `.env` as `OPENAI_API_KEY`

## Configuration

### Environment Variables

Add these to your `.env` file:

```env
# Schedule Detection Configuration
SCHEDULE_CHANNEL_ID=your_schedule_channel_id_here
SCHEDULE_EMOJI_ID=your_emoji_id_here
ANNOUNCEMENT_CHANNEL_ID=your_announcement_channel_id_here

# OpenAI Configuration (required for AI-powered detection)
OPENAI_API_KEY=your_openai_api_key_here
```

### Channel Setup

1. Create a Discord channel for schedule posts
2. Create a Discord channel for announcements
3. Get the channel IDs (right-click → Copy ID)
4. Set `SCHEDULE_CHANNEL_ID` and `ANNOUNCEMENT_CHANNEL_ID` in your environment variables
5. Ensure the bot has permissions to:
   - Read messages
   - Send messages
   - Add reactions
   - Attach files

### Emoji Configuration

1. Upload a custom emoji to your Discord server
2. Get the emoji ID (right-click → Copy ID)
3. Set `SCHEDULE_EMOJI_ID` in your environment variables

## Usage

### Interactive Workflow

1. **Image Submission**: Post an image containing a weekly schedule in the configured channel
2. **AI Processing**: Bot uses GPT-4 Vision to analyze the image and extract structured data
3. **Review Message**: Bot posts the original image + formatted schedule for staff review
4. **Staff Approval**: Staff can approve (✅) or reject (❌) the schedule
5. **Final Action**: Approved schedules are posted to the announcement channel

### Manual Testing

Use the `/schedule_test` command to test with an image URL:

```
/schedule_test image_url:https://example.com/schedule.png
```

### Configuration Reload

Use the `/schedule_reload` command to reload configuration:

```
/schedule_reload
```

## AI Processing Details

### GPT-4 Vision Prompt
The AI receives a detailed prompt that instructs it to:
- Extract date ranges (start and end dates)
- Identify all events with day, date, time, timezone, title, and description
- Convert all times to UTC
- Return data in structured XML format
- Handle various layouts and formats

### XML Output Format
The AI returns data in this XML structure:

```xml
<schedule>
  <date_range>
    <start_date>2024-01-15</start_date>
    <end_date>2024-01-21</end_date>
  </date_range>
  <events>
    <event>
      <day>Monday</day>
      <date>2024-01-15</date>
      <time>18:00</time>
      <timezone>UTC</timezone>
      <title>Minecraft Stream</title>
      <description>Building a new castle</description>
    </event>
  </events>
</schedule>
```

### Supported Formats

The AI can recognize various formats:

#### Date Ranges
- `30 June - 06 July`
- `30/06 - 06/07`
- `30-06 - 06-07`
- `January 15-21, 2024`

#### Time Formats
- `15:00 UTC`
- `15:00 CET`
- `15:00 CEST`
- `15:00` (assumes UTC)
- `3:00 PM` (12-hour format)

#### Event Titles
- `The devil in me - with Jade`
- `PEAK Collab - with XYZ`
- Any text describing the event

#### Day Recognition
- Monday/Mon
- Tuesday/Tue/Tues
- Wednesday/Wed
- Thursday/Thu/Thurs
- Friday/Fri
- Saturday/Sat
- Sunday/Sun

## Image Requirements

GPT-4 Vision is much more flexible than OCR, but for best results:

1. **Clear Text**: Ensure text is readable
2. **Good Resolution**: Higher quality images work better
3. **Structured Layout**: Clear organization helps with parsing
4. **Contrast**: Good contrast between text and background
5. **Format**: PNG, JPG, or other common formats

## Troubleshooting

### Common Issues

1. **API Key Missing**
   - Ensure `OPENAI_API_KEY` is set in `.env`
   - Verify the API key is valid and has credits

2. **No Events Extracted**
   - Check if the image contains clear schedule information
   - Verify the layout is recognizable
   - Try with a different image

3. **Incorrect Data**
   - The AI might misinterpret complex layouts
   - Check the generated XML in the logs
   - Adjust the prompt if needed

4. **API Rate Limits**
   - OpenAI has rate limits on API calls
   - Check your OpenAI account usage
   - Consider upgrading your plan if needed

### Debug Commands

- `/schedule_test` - Test with image URL
- `/schedule_reload` - Reload configuration
- Check bot logs for detailed error messages and XML output

## Testing

### Test Script
Use the included test script to verify the integration:

```bash
python test_gpt4_vision.py
```

This script will:
1. Test XML parsing functionality
2. Test full GPT-4 Vision integration
3. Show generated Discord messages

### Manual Testing
1. Replace the test image URL in `test_gpt4_vision.py`
2. Run the script with your actual schedule image
3. Check the generated output format

## Development

### Customizing the AI Prompt

To modify how the AI processes images, edit the prompt in `schedule_detector.py`:

```python
prompt = """Your custom prompt here...
"""
```

### Adding New XML Fields

To support additional data fields, modify both the prompt and XML parsing:

1. Update the prompt to request new fields
2. Modify `parse_xml_schedule` to handle new XML elements
3. Update `generate_discord_message` to display new fields

### Customizing Output Format

Modify the `generate_discord_message` method in `schedule_detector.py` to change the output format.

## Security Considerations

- The bot only processes images in the designated schedule channel
- Staff permissions are required for test commands
- Images are sent to OpenAI's servers for processing
- No image data is stored permanently
- API keys should be kept secure

## Performance Notes

- GPT-4 Vision API calls take 2-5 seconds typically
- API costs depend on image size and complexity
- Rate limits apply based on your OpenAI plan
- Consider caching results for repeated images

## Cost Considerations

- GPT-4 Vision has usage costs
- Costs depend on image size and API usage
- Monitor your OpenAI account usage
- Consider setting up usage alerts 