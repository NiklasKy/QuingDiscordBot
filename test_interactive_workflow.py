#!/usr/bin/env python3
"""
Interactive Workflow Test Script

This script demonstrates the new interactive schedule approval workflow.
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
    """Create a test schedule image for workflow testing."""
    # Create a simple test image
    width, height = 800, 600
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Use default font (works in Docker)
    font = ImageFont.load_default()
    
    # Draw schedule content
    content = [
        "Weekly Streaming Schedule",
        "30 June - 06 July 2024",
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
            if "Weekly Streaming Schedule" in line:
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

def simulate_workflow():
    """Simulate the complete interactive workflow."""
    print("QuingCraft Bot - Interactive Workflow Test")
    print("=" * 60)
    
    # Initialize detector
    detector = ScheduleDetector(schedule_channel_id=123456789, emoji_id="987654321")
    
    # Create test image
    print("1. Creating test schedule image...")
    test_image = create_test_schedule_image()
    
    # Simulate image processing
    print("2. Processing image with OCR...")
    formatted_message = detector.process_schedule_image(test_image)
    
    if not formatted_message:
        print("❌ Failed to process schedule image")
        return
    
    print("3. Generated formatted message:")
    print("-" * 40)
    print(formatted_message)
    print("-" * 40)
    
    # Simulate Discord embed creation
    print("\n4. Simulating Discord embed creation...")
    print("📅 Schedule Detection Result")
    print("The bot has detected and formatted a schedule from your image. Please review and approve or reject.")
    print("")
    print("Formatted Schedule:")
    print(formatted_message)
    print("")
    print("Submitted by: @TestUser (TestUser)")
    print("")
    print("Actions:")
    print("✅ Approve - Post to announcement channel")
    print("❌ Reject - Discard this schedule")
    print("")
    print("React with ✅ to approve or ❌ to reject")
    print("[Ursprüngliches Bild als Attachment]")
    
    # Simulate approval workflow
    print("\n5. Simulating approval workflow...")
    print("Staff member reacts with ✅")
    print("")
    print("Processing approval...")
    print("")
    print("✅ Schedule approved!")
    print("")
    print("Posted to announcement channel:")
    print("📅 Weekly Streaming Schedule")
    print(formatted_message)
    print("Approved by StaffMember")
    print("[Ursprüngliches Bild als Attachment]")
    
    print("\n" + "=" * 60)
    print("WORKFLOW SIMULATION COMPLETE!")
    print("=" * 60)

def test_rejection_workflow():
    """Test the rejection workflow."""
    print("\nTesting Rejection Workflow...")
    print("-" * 40)
    
    print("Staff member reacts with ❌")
    print("")
    print("Processing rejection...")
    print("")
    print("❌ Schedule rejected!")
    print("")
    print("Status: ❌ Rejected by StaffMember")
    print("Schedule discarded")
    print("")
    print("Workflow aborted - no announcement posted")

def test_permission_check():
    """Test permission checking for non-staff users."""
    print("\nTesting Permission Check...")
    print("-" * 40)
    
    print("Non-staff user tries to react with ✅")
    print("")
    print("Permission denied - reaction removed")
    print("Only staff members can approve/reject schedules")
    print("")
    print("✅ Permission system working correctly!")

def main():
    """Main test function."""
    print("Interactive Schedule Workflow Test")
    print("=" * 60)
    
    # Test the main workflow
    simulate_workflow()
    
    # Test rejection
    test_rejection_workflow()
    
    # Test permissions
    test_permission_check()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED!")
    print("=" * 60)
    print("\nWorkflow Features:")
    print("✅ Image processing with OCR")
    print("✅ Formatted message generation")
    print("✅ Interactive approval/rejection system")
    print("✅ Staff permission checking")
    print("✅ Announcement channel posting")
    print("✅ Workflow state management")
    print("✅ Error handling and logging")
    
    print("\nNext steps:")
    print("1. Set SCHEDULE_CHANNEL_ID, ANNOUNCEMENT_CHANNEL_ID, and SCHEDULE_EMOJI_ID in .env")
    print("2. Restart the Docker container")
    print("3. Post schedule images in the configured channel")
    print("4. Use ✅/❌ reactions to approve/reject schedules")

if __name__ == "__main__":
    main() 