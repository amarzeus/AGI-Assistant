"""Computer vision and OCR processing service for screenshot analysis."""

import asyncio
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

from src.config import get_config
from src.logger import get_app_logger
from src.services.event_system import (
    get_event_bus, EventType, Event
)


class VisionProcessor:
    """
    Computer vision and OCR processor for analyzing screenshots.
    
    Features:
    - Text extraction using Tesseract OCR
    - UI element detection using OpenCV
    - Window title and application name extraction
    - Structured data extraction from screenshots
    - Image preprocessing for better OCR accuracy
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # OCR configuration
        self.ocr_enabled = TESSERACT_AVAILABLE
        self.ocr_config = '--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
        
        # Vision processing settings
        self.min_contour_area = 100  # Minimum area for UI elements
        self.text_confidence_threshold = 30  # Minimum confidence for OCR text
        
        # Event system
        self.event_bus = get_event_bus()
        
        # Statistics
        self._images_processed = 0
        self._text_extractions = 0
        self._ui_elements_detected = 0
        
        if not self.ocr_enabled:
            self.logger.warning("Tesseract OCR not available - text extraction disabled")
        
        self.logger.info("Vision processor initialized")
    
    async def process_screenshot(self, image_path: Path, 
                               extract_text: bool = True,
                               detect_ui_elements: bool = True,
                               get_window_info: bool = True) -> Dict[str, Any]:
        """
        Process a screenshot and extract structured information.
        
        Args:
            image_path: Path to screenshot image
            extract_text: Whether to perform OCR text extraction
            detect_ui_elements: Whether to detect UI elements
            get_window_info: Whether to extract window information
            
        Returns:
            Dictionary with extracted information
        """
        try:
            if not image_path.exists():
                self.logger.error(f"Screenshot not found: {image_path}")
                return {"error": "Screenshot file not found"}
            
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                self.logger.error(f"Failed to load image: {image_path}")
                return {"error": "Failed to load image"}
            
            self._images_processed += 1
            
            # Initialize results
            results = {
                "image_path": str(image_path),
                "timestamp": datetime.now().isoformat(),
                "image_size": {
                    "width": image.shape[1],
                    "height": image.shape[0]
                },
                "processing_results": {}
            }
            
            # Extract text using OCR
            if extract_text and self.ocr_enabled:
                text_data = await self._extract_text_ocr(image)
                results["processing_results"]["text_extraction"] = text_data
                if text_data.get("text_found"):
                    self._text_extractions += 1
            
            # Detect UI elements
            if detect_ui_elements:
                ui_elements = await self._detect_ui_elements(image)
                results["processing_results"]["ui_elements"] = ui_elements
                self._ui_elements_detected += len(ui_elements.get("elements", []))
            
            # Extract window information
            if get_window_info:
                window_info = await self._extract_window_info(image)
                results["processing_results"]["window_info"] = window_info
            
            # Calculate overall confidence
            results["confidence"] = self._calculate_overall_confidence(results)
            
            self.logger.debug(f"Processed screenshot: {image_path.name}")
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing screenshot {image_path}: {e}")
            return {"error": str(e)}
    
    async def _extract_text_ocr(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract text from image using Tesseract OCR."""
        try:
            if not self.ocr_enabled:
                return {"error": "OCR not available"}
            
            # Preprocess image for better OCR
            processed_image = await self._preprocess_for_ocr(image)
            
            # Run OCR in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            ocr_result = await loop.run_in_executor(
                None,
                self._run_tesseract_ocr,
                processed_image
            )
            
            return ocr_result
            
        except Exception as e:
            self.logger.error(f"Error in OCR text extraction: {e}")
            return {"error": str(e)}
    
    def _run_tesseract_ocr(self, image: np.ndarray) -> Dict[str, Any]:
        """Run Tesseract OCR in thread pool."""
        try:
            # Get detailed OCR data
            ocr_data = pytesseract.image_to_data(
                image, 
                config=self.ocr_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extract text with confidence scores
            text_blocks = []
            full_text_parts = []
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                if text and confidence > self.text_confidence_threshold:
                    text_block = {
                        "text": text,
                        "confidence": confidence,
                        "bbox": {
                            "x": ocr_data['left'][i],
                            "y": ocr_data['top'][i],
                            "width": ocr_data['width'][i],
                            "height": ocr_data['height'][i]
                        },
                        "level": ocr_data['level'][i]
                    }
                    text_blocks.append(text_block)
                    full_text_parts.append(text)
            
            # Combine all text
            full_text = ' '.join(full_text_parts)
            
            return {
                "text_found": len(text_blocks) > 0,
                "full_text": full_text,
                "text_blocks": text_blocks,
                "total_blocks": len(text_blocks),
                "average_confidence": sum(block["confidence"] for block in text_blocks) / len(text_blocks) if text_blocks else 0
            }
            
        except Exception as e:
            self.logger.error(f"Tesseract OCR error: {e}")
            return {"error": str(e)}
    
    async def _preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better OCR accuracy."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((2, 2), np.uint8)
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            self.logger.error(f"Error preprocessing image for OCR: {e}")
            return image
    
    async def _detect_ui_elements(self, image: np.ndarray) -> Dict[str, Any]:
        """Detect UI elements using OpenCV contour detection."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter and classify contours
            ui_elements = []
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if area > self.min_contour_area:
                    # Get bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    
                    # Calculate aspect ratio
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # Classify element type based on shape
                    element_type = self._classify_ui_element(w, h, aspect_ratio, area)
                    
                    ui_element = {
                        "type": element_type,
                        "bbox": {"x": x, "y": y, "width": w, "height": h},
                        "area": area,
                        "aspect_ratio": aspect_ratio,
                        "confidence": self._calculate_element_confidence(element_type, aspect_ratio, area)
                    }
                    
                    ui_elements.append(ui_element)
            
            # Sort by area (largest first)
            ui_elements.sort(key=lambda x: x["area"], reverse=True)
            
            return {
                "elements_found": len(ui_elements),
                "elements": ui_elements[:20],  # Limit to top 20 elements
                "total_contours": len(contours)
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting UI elements: {e}")
            return {"error": str(e)}
    
    def _classify_ui_element(self, width: int, height: int, aspect_ratio: float, area: int) -> str:
        """Classify UI element type based on dimensions."""
        # Button-like elements
        if 0.2 <= aspect_ratio <= 5.0 and 1000 <= area <= 50000:
            return "button"
        
        # Text field-like elements
        elif aspect_ratio > 3.0 and height < 50:
            return "text_field"
        
        # Window/panel-like elements
        elif area > 50000:
            return "window"
        
        # Icon-like elements
        elif 0.8 <= aspect_ratio <= 1.2 and area < 5000:
            return "icon"
        
        # Menu/list-like elements
        elif aspect_ratio > 2.0 and height > 100:
            return "menu"
        
        else:
            return "unknown"
    
    def _calculate_element_confidence(self, element_type: str, aspect_ratio: float, area: int) -> float:
        """Calculate confidence score for UI element classification."""
        base_confidence = 0.5
        
        # Adjust confidence based on element type and characteristics
        if element_type == "button":
            if 0.5 <= aspect_ratio <= 3.0 and 2000 <= area <= 20000:
                base_confidence = 0.8
        elif element_type == "text_field":
            if aspect_ratio > 4.0:
                base_confidence = 0.7
        elif element_type == "window":
            if area > 100000:
                base_confidence = 0.9
        elif element_type == "icon":
            if 0.9 <= aspect_ratio <= 1.1:
                base_confidence = 0.7
        
        return min(1.0, base_confidence)
    
    async def _extract_window_info(self, image: np.ndarray) -> Dict[str, Any]:
        """Extract window information from screenshot."""
        try:
            # This is a simplified implementation
            # In a real scenario, you'd use platform-specific APIs
            
            # Try to detect window title bar
            title_bar = await self._detect_title_bar(image)
            
            # Try to detect application type from UI patterns
            app_type = await self._detect_application_type(image)
            
            return {
                "title_bar_detected": title_bar is not None,
                "title_bar": title_bar,
                "application_type": app_type,
                "window_detected": title_bar is not None or app_type != "unknown"
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting window info: {e}")
            return {"error": str(e)}
    
    async def _detect_title_bar(self, image: np.ndarray) -> Optional[Dict[str, Any]]:
        """Detect window title bar in screenshot."""
        try:
            # Look for horizontal rectangles at the top of the image
            height, width = image.shape[:2]
            top_region = image[:int(height * 0.1), :]  # Top 10% of image
            
            gray = cv2.cvtColor(top_region, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Title bars are typically wide and short
                if aspect_ratio > 5.0 and w > width * 0.3:
                    return {
                        "bbox": {"x": x, "y": y, "width": w, "height": h},
                        "confidence": 0.6
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error detecting title bar: {e}")
            return None
    
    async def _detect_application_type(self, image: np.ndarray) -> str:
        """Detect application type from UI patterns."""
        try:
            # This is a simplified heuristic-based approach
            # In practice, you'd use more sophisticated pattern recognition
            
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Look for common UI patterns
            height, width = gray.shape
            
            # Check for browser-like patterns (address bar, tabs)
            top_region = gray[:int(height * 0.15), :]
            if self._has_browser_patterns(top_region):
                return "browser"
            
            # Check for office application patterns (ribbons, toolbars)
            if self._has_office_patterns(gray):
                return "office"
            
            # Check for file manager patterns
            if self._has_file_manager_patterns(gray):
                return "file_manager"
            
            # Check for terminal/console patterns
            if self._has_terminal_patterns(gray):
                return "terminal"
            
            return "unknown"
            
        except Exception as e:
            self.logger.error(f"Error detecting application type: {e}")
            return "unknown"
    
    def _has_browser_patterns(self, top_region: np.ndarray) -> bool:
        """Check for browser-specific UI patterns."""
        # Look for horizontal lines that might indicate tabs or address bar
        edges = cv2.Canny(top_region, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, minLineLength=100, maxLineGap=10)
        
        return lines is not None and len(lines) > 2
    
    def _has_office_patterns(self, image: np.ndarray) -> bool:
        """Check for office application patterns."""
        # Look for ribbon-like structures (many small rectangles in rows)
        height, width = image.shape
        ribbon_region = image[int(height * 0.1):int(height * 0.3), :]
        
        edges = cv2.Canny(ribbon_region, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Count small rectangular contours
        small_rects = 0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if 20 <= w <= 100 and 20 <= h <= 60:
                small_rects += 1
        
        return small_rects > 10
    
    def _has_file_manager_patterns(self, image: np.ndarray) -> bool:
        """Check for file manager patterns."""
        # Look for grid-like patterns or list structures
        edges = cv2.Canny(image, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=50, maxLineGap=5)
        
        if lines is not None:
            # Count vertical and horizontal lines
            vertical_lines = 0
            horizontal_lines = 0
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
                
                if abs(angle) < 10 or abs(angle) > 170:  # Horizontal
                    horizontal_lines += 1
                elif 80 < abs(angle) < 100:  # Vertical
                    vertical_lines += 1
            
            return vertical_lines > 3 and horizontal_lines > 3
        
        return False
    
    def _has_terminal_patterns(self, image: np.ndarray) -> bool:
        """Check for terminal/console patterns."""
        # Terminals typically have uniform background and monospace text
        # Check for uniform color regions
        mean_color = np.mean(image)
        std_color = np.std(image)
        
        # Dark terminals have low mean and low std
        # Light terminals have high mean and low std
        return std_color < 30 and (mean_color < 50 or mean_color > 200)
    
    def _calculate_overall_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the processing results."""
        confidences = []
        
        # Text extraction confidence
        text_results = results.get("processing_results", {}).get("text_extraction", {})
        if text_results.get("text_found"):
            confidences.append(text_results.get("average_confidence", 0) / 100.0)
        
        # UI elements confidence
        ui_results = results.get("processing_results", {}).get("ui_elements", {})
        if ui_results.get("elements_found", 0) > 0:
            element_confidences = [elem.get("confidence", 0) for elem in ui_results.get("elements", [])]
            if element_confidences:
                confidences.append(sum(element_confidences) / len(element_confidences))
        
        # Window info confidence
        window_results = results.get("processing_results", {}).get("window_info", {})
        if window_results.get("window_detected"):
            confidences.append(0.7)  # Base confidence for window detection
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vision processor statistics."""
        return {
            "ocr_enabled": self.ocr_enabled,
            "images_processed": self._images_processed,
            "text_extractions": self._text_extractions,
            "ui_elements_detected": self._ui_elements_detected,
            "ocr_config": self.ocr_config,
            "min_contour_area": self.min_contour_area,
            "text_confidence_threshold": self.text_confidence_threshold
        }
    
    def is_available(self) -> bool:
        """Check if vision processor is available."""
        return True  # OpenCV is always available, OCR is optional