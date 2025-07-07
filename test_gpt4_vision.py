#!/usr/bin/env python3
"""
Test script for GPT-4 Vision schedule detection
"""

import os
import sys
from dotenv import load_dotenv
from PIL import Image
import requests
from io import BytesIO

# Add src to path
sys.path.append('src')

from schedule_detector import ScheduleDetector

def test_gpt4_vision():
    """Test GPT-4 Vision schedule detection"""
    
    # Load environment variables
    load_dotenv()
    
    # Check if OpenAI API key is set
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables!")
        print("Please add your OpenAI API key to the .env file")
        return False
    
    # Initialize schedule detector
    try:
        detector = ScheduleDetector(
            schedule_channel_id=123456789,  # Dummy ID for testing
            emoji_id="1234567890123456789"
        )
        print("✅ Schedule detector initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize schedule detector: {e}")
        return False
    
    # Test with a sample image URL (you can replace this with your own)
    test_image_url = "https://via.placeholder.com/800x600/ffffff/000000?text=Test+Schedule+Image"
    
    try:
        print("📥 Downloading test image...")
        response = requests.get(test_image_url)
        response.raise_for_status()
        
        # Convert to PIL Image
        image = Image.open(BytesIO(response.content))
        print(f"✅ Test image loaded: {image.size}")
        
        # Test GPT-4 Vision processing
        print("🤖 Processing image with GPT-4 Vision...")
        result = detector.process_schedule_image(image)
        
        if result:
            print("✅ GPT-4 Vision processing successful!")
            print("\n📋 Generated message:")
            print("-" * 50)
            print(result)
            print("-" * 50)
            return True
        else:
            print("❌ GPT-4 Vision processing failed - no result returned")
            return False
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

def test_xml_parsing():
    """Test XML parsing functionality"""
    
    print("\n🧪 Testing XML parsing...")
    
    # Sample XML (what GPT-4 Vision would return)
    sample_xml = """<schedule>
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
    <event>
      <day>Wednesday</day>
      <date>2024-01-17</date>
      <time>20:00</time>
      <timezone>UTC</timezone>
      <title>Gaming Stream</title>
    </event>
  </events>
</schedule>"""
    
    try:
        detector = ScheduleDetector(
            schedule_channel_id=123456789,
            emoji_id="1234567890123456789"
        )
        
        result = detector.parse_xml_schedule(sample_xml)
        
        if result:
            start_date, end_date, events = result
            print(f"✅ XML parsing successful!")
            print(f"📅 Date range: {start_date.date()} to {end_date.date()}")
            print(f"📋 Events found: {len(events)}")
            
            for event in events:
                print(f"  - {event.get('day')} {event.get('time')}: {event.get('title')}")
            
            return True
        else:
            print("❌ XML parsing failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during XML parsing test: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Testing GPT-4 Vision Schedule Detection")
    print("=" * 50)
    
    # Test XML parsing first (doesn't require API calls)
    xml_success = test_xml_parsing()
    
    # Test full GPT-4 Vision integration
    vision_success = test_gpt4_vision()
    
    print("\n" + "=" * 50)
    if xml_success and vision_success:
        print("🎉 All tests passed! GPT-4 Vision integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
    
    print("\n💡 To test with a real schedule image:")
    print("1. Replace the test_image_url in the script with your actual image URL")
    print("2. Run the script again")
    print("3. Check the generated Discord message format") 