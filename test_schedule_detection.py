#!/usr/bin/env python3
"""
Test script for schedule detection functionality.

This script tests the schedule detector module without requiring Discord.
"""

import sys
import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import pytz

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from schedule_detector import ScheduleDetector

def create_test_schedule_image():
    """Create a test schedule image for testing."""
    # Create a simple test image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Try to use a default font, fallback to basic if not available
    try:
        font = ImageFont.truetype("arial.ttf", 20)
        small_font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw schedule content
    content = [
        "Weekly Schedule",
        "30 June - 06 July",
        "",
        "Monday",
        "15:00 UTC The devil in me - with Jade",
        "",
        "Tuesday",
        "18:00 UTC PEAK Collab - with XYZ",
        "",
        "Wednesday",
        "Resting",
        "",
        "Thursday",
        "20:00 UTC Gaming Night - with ABC",
        "",
        "Friday",
        "16:00 UTC Stream Highlights",
        "",
        "Saturday",
        "14:00 UTC Community Day",
        "",
        "Sunday",
        "Resting"
    ]
    
    y_position = 50
    for line in content:
        if line.strip():
            if "Weekly Schedule" in line:
                draw.text((50, y_position), line, fill='black', font=font)
            elif "30 June - 06 July" in line:
                draw.text((50, y_position), line, fill='blue', font=font)
            elif any(day in line for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']):
                draw.text((50, y_position), line, fill='green', font=font)
            elif 'Resting' in line:
                draw.text((50, y_position), line, fill='gray', font=small_font)
            else:
                draw.text((50, y_position), line, fill='black', font=small_font)
        y_position += 30
    
    return image

def test_schedule_detector():
    """Test the schedule detector functionality."""
    print("=== Testing Schedule Detector ===")
    
    # Initialize detector
    detector = ScheduleDetector(schedule_channel_id=123456789, emoji_id="987654321")
    
    # Create test image
    print("Creating test schedule image...")
    test_image = create_test_schedule_image()
    
    # Save test image
    test_image_path = "test_schedule.png"
    test_image.save(test_image_path)
    print(f"Test image saved as: {test_image_path}")
    
    # Legacy OCR pipeline not used anymore; skipping to full processing
    print("\nSkipping legacy OCR pipeline tests (pytesseract/opencv)")
    
    # Test full processing
    print("\nTesting full processing...")
    result = detector.process_schedule_image(test_image)
    if result:
        print("Full processing successful!")
        return True
    else:
        print("Full processing failed!")
        return False

def test_time_parsing():
    """Test time parsing functionality."""
    print("\n=== Testing Time Parsing ===")
    
    detector = ScheduleDetector(schedule_channel_id=123456789, emoji_id="987654321")
    
    test_times = [
        "15:00 UTC",
        "18:00 CET",
        "20:00 CEST",
        "14:00",
        "16:30 UTC"
    ]
    
    for time_str in test_times:
        parsed = detector.parse_time(time_str)
        if parsed:
            print(f"✓ '{time_str}' -> {parsed}")
        else:
            print(f"✗ '{time_str}' -> Failed to parse")

def main():
    """Main test function."""
    print("QuingCraft Bot - Schedule Detection Test")
    print("=" * 50)
    
    # Test time parsing
    test_time_parsing()
    
    # Test full schedule detection
    success = test_schedule_detector()
    
    if success:
        print("\n✅ All tests passed!")
        print("\nTo use this feature:")
        print("1. Set SCHEDULE_CHANNEL_ID and SCHEDULE_EMOJI_ID in .env")
        print("2. Restart the bot")
        print("3. Post schedule images in the configured channel")
    else:
        print("\n❌ Some tests failed!")
        print("Check configuration and OpenAI API availability.")
    
    # Clean up test file
    if os.path.exists("test_schedule.png"):
        os.remove("test_schedule.png")
        print("\nCleaned up test files.")

if __name__ == "__main__":
    main() 