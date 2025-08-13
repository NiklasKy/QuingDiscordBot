#!/usr/bin/env python3
"""
Docker Test Script for Schedule Detection

This script tests the schedule detector module in a Docker container environment.
"""

import sys
import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import pytz

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from schedule_detector import ScheduleDetector

def test_tesseract_installation():
    """Deprecated: No longer using Tesseract."""
    print("=== Skipping Tesseract Installation Test (no longer required) ===")
    return True

def create_test_schedule_image():
    """Create a test schedule image for testing."""
    # Create a simple test image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Use default font (works in Docker)
    font = ImageFont.load_default()
    
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
                draw.text((50, y_position), line, fill='gray', font=font)
            else:
                draw.text((50, y_position), line, fill='black', font=font)
        y_position += 30
    
    return image

def test_opencv_installation():
    """Deprecated: No longer using OpenCV."""
    print("\n=== Skipping OpenCV Installation Test (no longer required) ===")
    return True

def test_schedule_detector():
    """Test the schedule detector functionality."""
    print("\n=== Testing Schedule Detector ===")
    
    # Initialize detector
    detector = ScheduleDetector(schedule_channel_id=123456789, emoji_id="987654321")
    
    # Create test image
    print("Creating test schedule image...")
    test_image = create_test_schedule_image()
    
    # Since GPT-4 Vision is used, skip legacy OCR pipeline tests
    print("Skipping legacy OCR pipeline tests (pytesseract/opencv)")
    
    # Test full processing
    print("\nTesting full processing...")
    result = detector.process_schedule_image(test_image)
    if result:
        print("✓ Full processing successful!")
        return True
    else:
        print("✗ Full processing failed!")
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
    
    success_count = 0
    for time_str in test_times:
        parsed = detector.parse_time(time_str)
        if parsed:
            print(f"✓ '{time_str}' -> {parsed}")
            success_count += 1
        else:
            print(f"✗ '{time_str}' -> Failed to parse")
    
    return success_count == len(test_times)

def main():
    """Main test function."""
    print("QuingCraft Bot - Docker Schedule Detection Test")
    print("=" * 60)
    
    # Test installations
    tesseract_ok = test_tesseract_installation()
    opencv_ok = test_opencv_installation()
    
    if not tesseract_ok or not opencv_ok:
        print("\n❌ Installation tests failed!")
        print("Make sure the Docker container is built with the latest Dockerfile")
        return
    
    # Test time parsing
    time_parsing_ok = test_time_parsing()
    
    # Test full schedule detection
    schedule_ok = test_schedule_detector()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    print(f"Tesseract Installation: skipped")
    print(f"OpenCV Installation: skipped")
    print(f"Time Parsing: {'✓' if time_parsing_ok else '✗'}")
    print(f"Schedule Detection: {'✓' if schedule_ok else '✗'}")
    
    if tesseract_ok and opencv_ok and time_parsing_ok and schedule_ok:
        print("\n✅ All tests passed!")
        print("\nSchedule Detection is ready to use!")
        print("\nNext steps:")
        print("1. Set SCHEDULE_CHANNEL_ID and SCHEDULE_EMOJI_ID in .env")
        print("2. Restart the Docker container")
        print("3. Post schedule images in the configured channel")
    else:
        print("\n❌ Some tests failed!")
        print("Check the Docker container logs for more details:")
        print("docker-compose logs quingcraft-bot")

if __name__ == "__main__":
    main() 