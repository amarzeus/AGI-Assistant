#!/usr/bin/env python3
"""
Test script for vision processor and OCR functionality.
"""

import asyncio
import sys
from pathlib import Path
import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from src.services.vision_processor import VisionProcessor
    from src.config import get_config
    print("✓ Successfully imported vision processor")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)


def create_test_image() -> Path:
    """Create a test image with text and UI elements."""
    # Create a test image
    img = np.ones((600, 800, 3), dtype=np.uint8) * 255  # White background
    
    # Add some text
    cv2.putText(img, "Sample Application", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "File Edit View Help", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)
    cv2.putText(img, "Welcome to the test application", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Click here to continue", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    
    # Add some UI elements (rectangles to simulate buttons, text fields, etc.)
    # Button 1
    cv2.rectangle(img, (50, 350), (150, 390), (200, 200, 200), -1)
    cv2.rectangle(img, (50, 350), (150, 390), (0, 0, 0), 2)
    cv2.putText(img, "OK", (85, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Button 2
    cv2.rectangle(img, (170, 350), (270, 390), (200, 200, 200), -1)
    cv2.rectangle(img, (170, 350), (270, 390), (0, 0, 0), 2)
    cv2.putText(img, "Cancel", (190, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Text field
    cv2.rectangle(img, (50, 250), (400, 280), (255, 255, 255), -1)
    cv2.rectangle(img, (50, 250), (400, 280), (0, 0, 0), 1)
    cv2.putText(img, "Enter your name here", (60, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
    
    # Window title bar simulation
    cv2.rectangle(img, (0, 0), (800, 30), (100, 100, 100), -1)
    cv2.putText(img, "Test Application - Document1", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    # Save test image
    test_image_path = Path("test_screenshot.png")
    cv2.imwrite(str(test_image_path), img)
    
    return test_image_path


async def test_vision_processor():
    """Test vision processor functionality."""
    print("🔍 Testing Vision Processor")
    print("=" * 40)
    
    try:
        # Create vision processor
        processor = VisionProcessor()
        print("✓ Vision processor created")
        
        # Check availability
        print(f"✓ Processor available: {processor.is_available()}")
        
        # Get stats
        stats = processor.get_stats()
        print(f"📊 OCR enabled: {stats['ocr_enabled']}")
        print(f"📊 Images processed: {stats['images_processed']}")
        print(f"📊 Text extractions: {stats['text_extractions']}")
        print(f"📊 UI elements detected: {stats['ui_elements_detected']}")
        
        # Create test image
        print("\n📸 Creating test image...")
        test_image_path = create_test_image()
        print(f"✓ Test image created: {test_image_path}")
        
        # Process the test image
        print("\n🔬 Processing test image...")
        results = await processor.process_screenshot(
            test_image_path,
            extract_text=True,
            detect_ui_elements=True,
            get_window_info=True
        )
        
        if "error" in results:
            print(f"✗ Processing failed: {results['error']}")
            return False
        
        print("✓ Image processing successful!")
        
        # Display results
        print(f"\n📋 Processing Results:")
        print(f"  - Image size: {results['image_size']['width']}x{results['image_size']['height']}")
        print(f"  - Overall confidence: {results['confidence']:.2f}")
        
        # Text extraction results
        text_results = results.get("processing_results", {}).get("text_extraction", {})
        if text_results:
            print(f"\n📝 Text Extraction:")
            print(f"  - Text found: {text_results.get('text_found', False)}")
            if text_results.get('text_found'):
                print(f"  - Full text: '{text_results.get('full_text', '')}'")
                print(f"  - Text blocks: {text_results.get('total_blocks', 0)}")
                print(f"  - Average confidence: {text_results.get('average_confidence', 0):.1f}%")
                
                # Show some text blocks
                text_blocks = text_results.get('text_blocks', [])[:5]  # First 5 blocks
                for i, block in enumerate(text_blocks, 1):
                    print(f"    Block {i}: '{block['text']}' (conf: {block['confidence']}%)")
        
        # UI elements results
        ui_results = results.get("processing_results", {}).get("ui_elements", {})
        if ui_results:
            print(f"\n🎛️  UI Elements:")
            print(f"  - Elements found: {ui_results.get('elements_found', 0)}")
            print(f"  - Total contours: {ui_results.get('total_contours', 0)}")
            
            elements = ui_results.get('elements', [])[:5]  # First 5 elements
            for i, element in enumerate(elements, 1):
                bbox = element['bbox']
                print(f"    Element {i}: {element['type']} at ({bbox['x']}, {bbox['y']}) "
                      f"size {bbox['width']}x{bbox['height']} (conf: {element['confidence']:.2f})")
        
        # Window info results
        window_results = results.get("processing_results", {}).get("window_info", {})
        if window_results:
            print(f"\n🪟 Window Information:")
            print(f"  - Window detected: {window_results.get('window_detected', False)}")
            print(f"  - Title bar detected: {window_results.get('title_bar_detected', False)}")
            print(f"  - Application type: {window_results.get('application_type', 'unknown')}")
            
            if window_results.get('title_bar'):
                title_bar = window_results['title_bar']
                bbox = title_bar['bbox']
                print(f"  - Title bar: {bbox['width']}x{bbox['height']} at ({bbox['x']}, {bbox['y']})")
        
        # Clean up test image
        test_image_path.unlink()
        print(f"\n🧹 Cleaned up test image")
        
        return True
        
    except Exception as e:
        print(f"✗ Vision processor test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_real_screenshot():
    """Test with a real screenshot if available."""
    print("\n\n📸 Testing with Real Screenshot")
    print("=" * 40)
    
    try:
        # Look for existing screenshots
        screenshot_paths = list(Path(".").glob("screenshot_*.png"))
        
        if not screenshot_paths:
            print("ℹ️  No existing screenshots found, skipping real screenshot test")
            return True
        
        # Use the first screenshot found
        screenshot_path = screenshot_paths[0]
        print(f"📁 Found screenshot: {screenshot_path}")
        
        # Create vision processor
        processor = VisionProcessor()
        
        # Process the real screenshot
        print("🔬 Processing real screenshot...")
        results = await processor.process_screenshot(screenshot_path)
        
        if "error" in results:
            print(f"✗ Processing failed: {results['error']}")
            return False
        
        print("✓ Real screenshot processing successful!")
        
        # Show summary
        text_results = results.get("processing_results", {}).get("text_extraction", {})
        ui_results = results.get("processing_results", {}).get("ui_elements", {})
        
        print(f"📊 Summary:")
        print(f"  - Text blocks found: {text_results.get('total_blocks', 0)}")
        print(f"  - UI elements found: {ui_results.get('elements_found', 0)}")
        print(f"  - Overall confidence: {results['confidence']:.2f}")
        
        if text_results.get('full_text'):
            preview = text_results['full_text'][:100]
            print(f"  - Text preview: '{preview}{'...' if len(text_results['full_text']) > 100 else ''}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Real screenshot test failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 Vision Processor Test")
    print("=" * 50)
    
    # Test vision processor
    processor_success = await test_vision_processor()
    
    # Test with real screenshot
    real_screenshot_success = await test_real_screenshot()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"  - Vision Processor: {'✓ PASS' if processor_success else '✗ FAIL'}")
    print(f"  - Real Screenshot: {'✓ PASS' if real_screenshot_success else '✗ FAIL'}")
    
    if processor_success:
        print("\n🎉 Vision processor is working correctly!")
        print("\n💡 Features available:")
        print("  - Text extraction using OpenCV preprocessing")
        if VisionProcessor().get_stats()['ocr_enabled']:
            print("  - OCR using Tesseract (installed)")
        else:
            print("  - OCR using Tesseract (not installed - install with: pip install pytesseract)")
        print("  - UI element detection using contour analysis")
        print("  - Window information extraction")
        print("  - Application type detection")
    else:
        print("\n❌ Vision processor has issues.")
    
    print("\n🔧 Next steps:")
    print("1. Install Tesseract OCR for better text extraction")
    print("2. Test with real screenshots from screen capture")
    print("3. Integrate with workflow analyzer for action detection")


if __name__ == "__main__":
    asyncio.run(main())