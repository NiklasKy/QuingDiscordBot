"""
Streaming Schedule Detector Module

This module provides functionality to detect and parse streaming schedules
from images posted in Discord channels using GPT-4 Vision API.
"""

import os
import re
import io
import base64
from datetime import datetime, timedelta
import pytz
from dateutil import parser
from typing import List, Dict, Optional, Tuple
import logging
import xml.etree.ElementTree as ET
from PIL import Image
import openai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScheduleDetector:
    """Detects and parses streaming schedules from images using GPT-4 Vision."""
    
    def __init__(self, schedule_channel_id: int, emoji_id: str = "1234567890123456789", emoji_name: str = "cassia_kurukuru", emoji_animated: bool = False):
        """
        Initialize the schedule detector.
        
        Args:
            schedule_channel_id: Discord channel ID where schedules are posted
            emoji_id: Discord emoji ID to use for schedule items
            emoji_name: Discord emoji name to use for schedule items
            emoji_animated: Whether the emoji is animated (True/False)
        """
        self.schedule_channel_id = schedule_channel_id
        self.emoji_id = emoji_id
        self.emoji_name = emoji_name
        self.emoji_animated = emoji_animated
        self.utc_tz = pytz.UTC
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not found in environment variables!")
            raise ValueError("OPENAI_API_KEY is required for GPT-4 Vision")
        
        self.client = openai.OpenAI(api_key=api_key)
        logger.info("Schedule detector initialized with GPT-4 Vision API")
    
    def image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string for GPT-4 Vision API.
        """
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return image_base64
    
    def extract_schedule_xml(self, image: Image.Image) -> Optional[str]:
        """
        Extract schedule information from image using GPT-4 Vision and return as XML.
        """
        try:
            # Convert image to base64
            image_base64 = self.image_to_base64(image)
            
            # Create the prompt for GPT-4 Vision
            prompt = """Analyze this streaming schedule image and extract all events. Return the data as XML in the following format:

<schedule>
  <date_range>
    <start_date>YYYY-MM-DD</start_date>
    <end_date>YYYY-MM-DD</end_date>
  </date_range>
  <events>
    <event>
      <day>Monday</day>
      <date>YYYY-MM-DD</date>
      <time>HH:MM</time>
      <timezone>UTC</timezone>
      <title>Event Title</title>
      <description>Optional description</description>
    </event>
    <!-- Add more events as needed -->
  </events>
</schedule>

Important:
- Extract the date range (start and end dates) from the image
- For each event, extract day, date, time, timezone, title, and optional description
- Use UTC timezone if not specified
- If time is in a different timezone, convert to UTC
- Only include events that have a clear time and title
- If no events are found, return empty <events></events>"""

            # Call GPT-4 Vision API
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            xml_content = response.choices[0].message.content.strip()
            logger.info(f"[GPT-4 Vision] Extracted XML:\n{xml_content}")
            
            # Clean XML content - remove markdown code blocks if present
            if xml_content.startswith('```'):
                # Remove opening ```xml or ``` and closing ```
                lines = xml_content.split('\n')
                cleaned_lines = []
                in_xml = False
                for line in lines:
                    if line.strip().startswith('```'):
                        if not in_xml:
                            in_xml = True
                        else:
                            break
                    elif in_xml:
                        cleaned_lines.append(line)
                xml_content = '\n'.join(cleaned_lines).strip()
            
            return xml_content
            
        except Exception as e:
            logger.error(f"Error extracting schedule with GPT-4 Vision: {e}")
            return None
    
    def parse_xml_schedule(self, xml_content: str, week_offset: int = 0) -> Optional[Tuple[datetime, datetime, List[Dict]]]:
        """
        Parse the XML content from GPT-4 Vision and extract schedule data.
        Nach dem Parsen: Setze Date-Range und alle Event-Daten auf die aktuelle Woche (Montag–Sonntag) im aktuellen Jahr.
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Calculate selected week's Monday and Sunday (week_offset: 0=current, 1=next, ...)
            today = datetime.now(self.utc_tz)
            current_monday = today - timedelta(days=today.weekday())
            base_monday = current_monday + timedelta(days=7 * week_offset)
            base_sunday = base_monday + timedelta(days=6)
            
            # Mapping for weekday names to offset
            weekday_map = {
                'monday': 0, 'mon': 0,
                'tuesday': 1, 'tue': 1, 'tues': 1,
                'wednesday': 2, 'wed': 2,
                'thursday': 3, 'thu': 3, 'thurs': 3,
                'friday': 4, 'fri': 4,
                'saturday': 5, 'sat': 5,
                'sunday': 6, 'sun': 6,
            }
            
            # Set date range to selected week (ignore what GPT-4o says)
            start_date = base_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = base_sunday.replace(hour=23, minute=59, second=59, microsecond=0)
            
            # Extract events
            events = []
            events_elem = root.find('events')
            if events_elem is not None:
                for event_elem in events_elem.findall('event'):
                    event = {}
                    # Extract event data
                    day_elem = event_elem.find('day')
                    time_elem = event_elem.find('time')
                    timezone_elem = event_elem.find('timezone')
                    title_elem = event_elem.find('title')
                    desc_elem = event_elem.find('description')
                    if day_elem is not None:
                        event['day'] = day_elem.text
                    if time_elem is not None:
                        event['time'] = time_elem.text
                    if timezone_elem is not None:
                        event['timezone'] = timezone_elem.text
                    if title_elem is not None:
                        event['title'] = title_elem.text
                    if desc_elem is not None:
                        event['description'] = desc_elem.text
                    # Set event date: base Monday + offset for weekday
                    if 'day' in event and event['day']:
                        day_lc = event['day'].strip().lower()
                        offset = weekday_map.get(day_lc, None)
                        if offset is not None:
                            event_date = (base_monday + timedelta(days=offset)).date()
                            event['date'] = event_date
                    # Create full datetime
                    if 'date' in event and 'time' in event:
                        try:
                            event_datetime = datetime.combine(
                                event['date'],
                                datetime.strptime(event['time'], '%H:%M').time()
                            )
                            # Apply timezone
                            if 'timezone' in event and event['timezone'] != 'UTC':
                                try:
                                    tz = pytz.timezone(event['timezone'])
                                    event_datetime = tz.localize(event_datetime)
                                    event_datetime = event_datetime.astimezone(self.utc_tz)
                                except:
                                    event_datetime = self.utc_tz.localize(event_datetime)
                            else:
                                event_datetime = self.utc_tz.localize(event_datetime)
                            event['datetime'] = event_datetime
                        except Exception as e:
                            logger.warning(f"Could not parse datetime for event: {event} ({e})")
                    events.append(event)
            logger.info(f"Parsed {len(events)} events from XML (dates set with week_offset={week_offset})")
            return start_date, end_date, events
        except Exception as e:
            logger.error(f"Error parsing XML schedule: {e}")
            return None

    def rebuild_event_datetime(self, event: Dict) -> None:
        """
        Rebuild the UTC datetime for a single event in-place using its 'date', 'time', and optional 'timezone'.
        Expects 'date' (date object) and 'time' (HH:MM) to be present.
        """
        try:
            if 'date' in event and 'time' in event and event['date'] and event['time']:
                event_datetime = datetime.combine(
                    event['date'],
                    datetime.strptime(event['time'], '%H:%M').time()
                )
                if 'timezone' in event and event['timezone'] and event['timezone'] != 'UTC':
                    try:
                        tz = pytz.timezone(event['timezone'])
                        event_datetime = tz.localize(event_datetime)
                        event_datetime = event_datetime.astimezone(self.utc_tz)
                    except Exception:
                        event_datetime = self.utc_tz.localize(event_datetime)
                else:
                    event_datetime = self.utc_tz.localize(event_datetime)
                event['datetime'] = event_datetime
        except Exception as e:
            logger.warning(f"Failed to rebuild datetime for event {event}: {e}")
    
    def generate_discord_message(self, date_range: Tuple[datetime, datetime], events: List[Dict]) -> str:
        """
        Generate Discord message in the format:
        💜 [30 June - 06 July] 💚
        <a:emoji:id> Event Title
        <t:UNIX_TIMESTAMP>
        ...
        """
        start_date, end_date = date_range
        # Format date range
        date_range_str = f"{start_date.strftime('%d %B')} - {end_date.strftime('%d %B')}"
        message = f"💜 [{date_range_str}] 💚\n\n"
        if not events:
            message += "❌ No events found in this schedule.\n"
            return message
        # Sort events by datetime
        events = sorted([e for e in events if e.get('datetime')], key=lambda x: x['datetime'])
        if self.emoji_animated:
            emoji_tag = f"<a:{self.emoji_name}:{self.emoji_id}>"
        else:
            emoji_tag = f"<:{self.emoji_name}:{self.emoji_id}>"
        for event in events:
            title = event.get('title', 'Untitled Event')
            unix_timestamp = int(event['datetime'].timestamp())
            message += f"{emoji_tag} {title}\n<t:{unix_timestamp}>\n\n"
        return message.strip()
    
    def process_schedule_image(self, image: Image.Image) -> Optional[str]:
        """
        Main method to process a schedule image and return Discord message.
        """
        try:
            logger.info("Processing schedule image with GPT-4 Vision...")
            
            # Extract XML from image
            xml_content = self.extract_schedule_xml(image)
            if not xml_content:
                logger.error("Failed to extract XML from image")
                return None
            
            # Parse XML to get schedule data
            schedule_data = self.parse_xml_schedule(xml_content)
            if not schedule_data:
                logger.error("Failed to parse XML schedule data")
                return None
            
            start_date, end_date, events = schedule_data
            
            # Generate Discord message
            message = self.generate_discord_message((start_date, end_date), events)
            
            logger.info(f"Successfully processed schedule with {len(events)} events")
            return message
            
        except Exception as e:
            logger.error(f"Error processing schedule image: {e}")
            return None 