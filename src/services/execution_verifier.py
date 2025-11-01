"""Execution Verifier Service.

This module provides verification capabilities for automation execution:
- Screenshot capture before/after actions
- Action result verification
- Image comparison for detecting changes
- Confidence scoring for verification results
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
import uuid

from PIL import Image, ImageChops
import numpy as np

from src.config import get_config
from src.logger import get_app_logger


@dataclass
class VerificationResult:
    """
    Result of action verification.
    
    Contains information about whether an action completed successfully
    and evidence supporting the verification.
    """
    action_id: str
    action_type: str
    success: bool
    confidence: float  # 0.0 to 1.0
    before_screenshot: Optional[Path] = None
    after_screenshot: Optional[Path] = None
    differences: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    verification_method: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'action_id': self.action_id,
            'action_type': self.action_type,
            'success': self.success,
            'confidence': self.confidence,
            'before_screenshot': str(self.before_screenshot) if self.before_screenshot else None,
            'after_screenshot': str(self.after_screenshot) if self.after_screenshot else None,
            'differences': self.differences,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat(),
            'verification_method': self.verification_method,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VerificationResult':
        """Create VerificationResult from dictionary."""
        return cls(
            action_id=data['action_id'],
            action_type=data['action_type'],
            success=data['success'],
            confidence=data['confidence'],
            before_screenshot=Path(data['before_screenshot']) if data.get('before_screenshot') else None,
            after_screenshot=Path(data['after_screenshot']) if data.get('after_screenshot') else None,
            differences=data.get('differences', []),
            error_message=data.get('error_message'),
            timestamp=datetime.fromisoformat(data['timestamp']),
            verification_method=data.get('verification_method', ''),
            metadata=data.get('metadata', {}),
        )


class ExecutionVerifier:
    """
    Service for verifying automation execution results.
    
    Features:
    - Capture screenshots before/after actions
    - Compare images to detect changes
    - Verify specific action types (click, type, navigation)
    - Calculate confidence scores
    - Store verification results
    """
    
    def __init__(self):
        self.config = get_config()
        self.logger = get_app_logger()
        
        # Storage for screenshots and results
        self.verification_screenshots: Dict[str, Path] = {}
        self.verification_results: List[VerificationResult] = []
        
        # Verification settings
        self._change_threshold = 0.05  # 5% change to consider significant
        self._confidence_threshold = 0.7  # Minimum confidence for success
        
        # Screenshot capture
        self._screenshot_dir: Optional[Path] = None
        
        self.logger.info("Execution verifier initialized")
    
    async def initialize(self) -> None:
        """
        Initialize the execution verifier.
        
        Sets up directories and prepares for verification.
        """
        try:
            # Create verification screenshots directory
            paths = self.config.get_data_paths()
            self._screenshot_dir = paths['sessions'] / 'verification_screenshots'
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Verification directory created: {self._screenshot_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize execution verifier: {e}")
            raise
    
    async def capture_before_state(self, action: Dict[str, Any]) -> str:
        """
        Capture screenshot before action execution.
        
        Args:
            action: Action data dictionary
            
        Returns:
            Screenshot identifier (key for retrieval)
        """
        try:
            action_id = action.get('id', str(uuid.uuid4()))
            timestamp = datetime.now()
            
            # Generate unique filename
            filename = f"before_{action_id}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.png"
            filepath = self._screenshot_dir / filename
            
            # Capture screenshot
            screenshot = await self._capture_screenshot()
            screenshot.save(str(filepath), "PNG")
            
            # Store reference
            screenshot_key = f"before_{action_id}"
            self.verification_screenshots[screenshot_key] = filepath
            
            self.logger.debug(f"Captured before state: {filename}")
            return screenshot_key
            
        except Exception as e:
            self.logger.error(f"Failed to capture before state: {e}")
            return ""
    
    async def capture_after_state(self, action: Dict[str, Any]) -> str:
        """
        Capture screenshot after action execution.
        
        Args:
            action: Action data dictionary
            
        Returns:
            Screenshot identifier (key for retrieval)
        """
        try:
            action_id = action.get('id', str(uuid.uuid4()))
            timestamp = datetime.now()
            
            # Generate unique filename
            filename = f"after_{action_id}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.png"
            filepath = self._screenshot_dir / filename
            
            # Capture screenshot
            screenshot = await self._capture_screenshot()
            screenshot.save(str(filepath), "PNG")
            
            # Store reference
            screenshot_key = f"after_{action_id}"
            self.verification_screenshots[screenshot_key] = filepath
            
            self.logger.debug(f"Captured after state: {filename}")
            return screenshot_key
            
        except Exception as e:
            self.logger.error(f"Failed to capture after state: {e}")
            return ""
    
    async def verify_action(
        self,
        action: Dict[str, Any],
        before_state: str,
        after_state: str
    ) -> VerificationResult:
        """
        Verify that an action completed successfully.
        
        Dispatches to specific verification methods based on action type.
        
        Args:
            action: Action data dictionary
            before_state: Before screenshot key
            after_state: After screenshot key
            
        Returns:
            VerificationResult with success status and confidence
        """
        try:
            action_id = action.get('id', str(uuid.uuid4()))
            action_type = action.get('type', 'unknown')
            
            # Get screenshot paths
            before_path = self.verification_screenshots.get(before_state)
            after_path = self.verification_screenshots.get(after_state)
            
            if not before_path or not after_path:
                return VerificationResult(
                    action_id=action_id,
                    action_type=action_type,
                    success=False,
                    confidence=0.0,
                    error_message="Missing before/after screenshots",
                    verification_method="none"
                )
            
            # Dispatch to specific verifier based on action type
            if action_type in ['click', 'double_click', 'right_click', 'browser_click']:
                result = await self.verify_click(
                    action.get('x', 0),
                    action.get('y', 0),
                    str(before_path),
                    str(after_path)
                )
            elif action_type in ['type_text', 'type', 'browser_type', 'browser_fill']:
                result = await self.verify_type(
                    action.get('text', ''),
                    str(before_path),
                    str(after_path)
                )
            elif action_type in ['navigate', 'browser_navigate', 'window_focus']:
                result = await self.verify_navigation(
                    action.get('target', action.get('url', '')),
                    str(after_path)
                )
            else:
                # Generic verification using image comparison
                result = await self._verify_generic(
                    str(before_path),
                    str(after_path)
                )
            
            # Update result with action info
            result.action_id = action_id
            result.action_type = action_type
            result.before_screenshot = before_path
            result.after_screenshot = after_path
            
            # Store result
            self.verification_results.append(result)
            
            self.logger.info(
                f"Verification complete for {action_type}: "
                f"success={result.success}, confidence={result.confidence:.2f}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to verify action: {e}")
            return VerificationResult(
                action_id=action.get('id', str(uuid.uuid4())),
                action_type=action.get('type', 'unknown'),
                success=False,
                confidence=0.0,
                error_message=str(e),
                verification_method="error"
            )
    
    async def verify_click(
        self,
        x: int,
        y: int,
        before: str,
        after: str
    ) -> VerificationResult:
        """
        Verify click action by detecting UI changes at click location.
        
        Uses advanced region-based comparison to detect changes around
        the click point and identify specific difference regions.
        
        Args:
            x: Click X coordinate
            y: Click Y coordinate
            before: Path to before screenshot
            after: Path to after screenshot
            
        Returns:
            VerificationResult with detailed difference analysis
        """
        try:
            # Load images
            before_img = Image.open(before)
            after_img = Image.open(after)
            
            # Define region around click point (100x100 pixels for better detection)
            region_size = 100
            left = max(0, x - region_size // 2)
            top = max(0, y - region_size // 2)
            right = min(before_img.width, x + region_size // 2)
            bottom = min(before_img.height, y + region_size // 2)
            
            # Compare the click region using advanced comparison
            region_comparison = await self.compare_region(
                before_img,
                after_img,
                {'left': left, 'top': top, 'right': right, 'bottom': bottom},
                threshold=30
            )
            
            # Also check for changes in the full image to detect indirect effects
            full_comparison = await self._compare_images_advanced(
                before_img,
                after_img,
                threshold=30
            )
            
            # Determine success based on region changes
            # Click should cause some change in the region (similarity < 0.95)
            # but not too much change (similarity > 0.3)
            region_similarity = region_comparison.get('similarity', 1.0)
            success = 0.3 < region_similarity < 0.95
            
            # Calculate confidence based on:
            # 1. Region similarity (peak at 70%)
            # 2. Presence of localized changes
            # 3. Structural similarity
            region_confidence = 1.0 - abs(region_similarity - 0.7) / 0.7
            structural_confidence = region_comparison.get('structural_similarity', 0.5)
            
            # Weight region changes more heavily
            confidence = (region_confidence * 0.7 + structural_confidence * 0.3)
            
            # Boost confidence if we detected specific difference regions
            diff_regions = full_comparison.get('diff_regions', [])
            if diff_regions:
                # Check if any difference region is near the click point
                nearby_regions = [
                    r for r in diff_regions
                    if (r['left'] <= x <= r['right'] and r['top'] <= y <= r['bottom'])
                ]
                if nearby_regions:
                    confidence = min(1.0, confidence * 1.2)
            
            return VerificationResult(
                action_id="",  # Will be set by caller
                action_type="click",
                success=success,
                confidence=max(0.0, min(1.0, confidence)),
                verification_method="region_comparison_advanced",
                differences=[
                    {
                        'type': 'click_region',
                        'region': region_comparison.get('region', {}),
                        'similarity': region_similarity,
                        'diff_pixels': region_comparison.get('diff_pixels', 0),
                        'diff_percentage': region_comparison.get('diff_percentage', 0.0),
                        'mean_diff': region_comparison.get('mean_diff', 0.0),
                        'structural_similarity': region_comparison.get('structural_similarity', 0.0)
                    },
                    {
                        'type': 'full_image',
                        'similarity': full_comparison.get('similarity', 1.0),
                        'diff_pixels': full_comparison.get('diff_pixels', 0),
                        'diff_percentage': full_comparison.get('diff_percentage', 0.0),
                        'diff_regions': diff_regions[:10]  # Limit to first 10 regions
                    }
                ],
                metadata={
                    'click_location': {'x': x, 'y': y},
                    'region_size': region_size,
                    'nearby_changes': len([
                        r for r in diff_regions
                        if (r['left'] <= x <= r['right'] and r['top'] <= y <= r['bottom'])
                    ])
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to verify click: {e}")
            return VerificationResult(
                action_id="",
                action_type="click",
                success=False,
                confidence=0.0,
                error_message=str(e),
                verification_method="region_comparison_advanced"
            )
    
    async def verify_type(
        self,
        text: str,
        before: str,
        after: str
    ) -> VerificationResult:
        """
        Verify type action by checking if text appeared.
        
        Uses advanced image comparison to detect text changes and
        identify specific regions where text was added.
        
        Args:
            text: Text that was typed
            before: Path to before screenshot
            after: Path to after screenshot
            
        Returns:
            VerificationResult with detailed difference analysis
        """
        try:
            # Load images
            before_img = Image.open(before)
            after_img = Image.open(after)
            
            # Compare full images using advanced comparison
            comparison = await self._compare_images_advanced(
                before_img,
                after_img,
                threshold=20  # Lower threshold for text detection
            )
            
            # Typing should cause visible changes
            # More text = more changes expected
            # Estimate: ~0.1% change per character, max 10%
            expected_change = min(0.1, len(text) * 0.001)
            actual_change = 1.0 - comparison['similarity']
            
            # Success if actual change is at least 50% of expected
            success = actual_change >= expected_change * 0.5
            
            # Calculate confidence based on:
            # 1. How close actual change is to expected
            # 2. Structural similarity (text should maintain structure)
            # 3. Presence of localized change regions
            change_ratio = actual_change / expected_change if expected_change > 0 else 0.5
            change_confidence = min(1.0, change_ratio)
            structural_confidence = comparison.get('structural_similarity', 0.5)
            
            # Boost confidence if we have localized changes (typical for text input)
            diff_regions = comparison.get('diff_regions', [])
            region_confidence = min(1.0, len(diff_regions) * 0.1) if diff_regions else 0.3
            
            # Weighted average
            confidence = (
                change_confidence * 0.5 +
                structural_confidence * 0.3 +
                region_confidence * 0.2
            )
            
            return VerificationResult(
                action_id="",
                action_type="type",
                success=success,
                confidence=max(0.0, min(1.0, confidence)),
                verification_method="image_comparison_advanced",
                differences=[{
                    'similarity': comparison['similarity'],
                    'diff_pixels': comparison['diff_pixels'],
                    'diff_percentage': comparison['diff_percentage'],
                    'mean_diff': comparison['mean_diff'],
                    'max_diff': comparison['max_diff'],
                    'expected_change': expected_change,
                    'actual_change': actual_change,
                    'structural_similarity': comparison['structural_similarity'],
                    'diff_regions': diff_regions[:5]  # First 5 regions where text likely appeared
                }],
                metadata={
                    'text_length': len(text),
                    'text_preview': text[:50] if len(text) > 50 else text,
                    'num_change_regions': len(diff_regions)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to verify type: {e}")
            return VerificationResult(
                action_id="",
                action_type="type",
                success=False,
                confidence=0.0,
                error_message=str(e),
                verification_method="image_comparison_advanced"
            )
    
    async def verify_navigation(
        self,
        target: str,
        after: str
    ) -> VerificationResult:
        """
        Verify navigation action by checking window title or URL.
        
        Note: This is a simplified version. Full implementation would
        require window title detection or browser integration.
        
        Args:
            target: Target window/URL
            after: Path to after screenshot
            
        Returns:
            VerificationResult
        """
        try:
            # For now, we'll use a heuristic approach
            # In a full implementation, we would:
            # 1. Get actual window title using win32gui
            # 2. For browser, check URL from browser automation platform
            
            # Simplified: assume navigation succeeded if screenshot was captured
            after_img = Image.open(after)
            
            # Basic check: image should be valid and non-blank
            img_array = np.array(after_img)
            mean_brightness = img_array.mean()
            
            # If image is not completely black or white, assume success
            success = 10 < mean_brightness < 245
            confidence = 0.7 if success else 0.3
            
            return VerificationResult(
                action_id="",
                action_type="navigation",
                success=success,
                confidence=confidence,
                verification_method="screenshot_validity",
                metadata={
                    'target': target,
                    'mean_brightness': float(mean_brightness)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to verify navigation: {e}")
            return VerificationResult(
                action_id="",
                action_type="navigation",
                success=False,
                confidence=0.0,
                error_message=str(e),
                verification_method="screenshot_validity"
            )
    
    async def _verify_generic(
        self,
        before: str,
        after: str
    ) -> VerificationResult:
        """
        Generic verification using advanced image comparison.
        
        Provides comprehensive analysis for actions without specific
        verification methods.
        
        Args:
            before: Path to before screenshot
            after: Path to after screenshot
            
        Returns:
            VerificationResult with detailed analysis
        """
        try:
            # Load images
            before_img = Image.open(before)
            after_img = Image.open(after)
            
            # Compare images using advanced comparison
            comparison = await self._compare_images_advanced(
                before_img,
                after_img,
                threshold=30
            )
            
            # Generic action should cause some change
            # At least 2% change to be considered successful
            similarity = comparison['similarity']
            success = similarity < 0.98
            
            # Calculate confidence based on:
            # 1. Amount of change (more change = higher confidence)
            # 2. Structural similarity (should maintain some structure)
            # 3. Presence of localized changes
            change_amount = 1.0 - similarity
            change_confidence = min(1.0, change_amount * 10)  # Scale up small changes
            structural_confidence = comparison.get('structural_similarity', 0.5)
            
            diff_regions = comparison.get('diff_regions', [])
            region_confidence = min(1.0, len(diff_regions) * 0.1) if diff_regions else 0.3
            
            # Weighted confidence
            confidence = (
                change_confidence * 0.5 +
                structural_confidence * 0.3 +
                region_confidence * 0.2
            ) if success else 0.5
            
            return VerificationResult(
                action_id="",
                action_type="generic",
                success=success,
                confidence=max(0.0, min(1.0, confidence)),
                verification_method="full_image_comparison_advanced",
                differences=[{
                    'similarity': comparison['similarity'],
                    'diff_pixels': comparison['diff_pixels'],
                    'diff_percentage': comparison['diff_percentage'],
                    'mean_diff': comparison['mean_diff'],
                    'max_diff': comparison['max_diff'],
                    'structural_similarity': comparison['structural_similarity'],
                    'diff_regions': diff_regions[:10]  # First 10 significant regions
                }],
                metadata={
                    'num_change_regions': len(diff_regions),
                    'total_change_area': sum(r['area'] for r in diff_regions)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed generic verification: {e}")
            return VerificationResult(
                action_id="",
                action_type="generic",
                success=False,
                confidence=0.0,
                error_message=str(e),
                verification_method="full_image_comparison_advanced"
            )
    
    async def _capture_screenshot(self) -> Image.Image:
        """
        Capture current screen state.
        
        Returns:
            PIL Image of screen
        """
        try:
            import mss
            
            with mss.mss() as sct:
                # Capture primary monitor
                screenshot = sct.grab(sct.monitors[0])
                
                # Convert to PIL Image
                img = Image.frombytes(
                    "RGB",
                    screenshot.size,
                    screenshot.bgra,
                    "raw",
                    "BGRX"
                )
                
                return img
                
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            raise
    
    async def _compare_images(
        self,
        img1: Image.Image,
        img2: Image.Image
    ) -> Tuple[float, int]:
        """
        Compare two images and calculate similarity.
        
        Args:
            img1: First image
            img2: Second image
            
        Returns:
            Tuple of (similarity_score, diff_pixel_count)
            similarity_score: 0.0 (completely different) to 1.0 (identical)
        """
        try:
            # Ensure images are same size
            if img1.size != img2.size:
                img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
            
            # Calculate pixel difference
            diff = ImageChops.difference(img1, img2)
            
            # Convert to numpy array for analysis
            diff_array = np.array(diff)
            
            # Count different pixels (any channel differs by more than threshold)
            threshold = 30  # Ignore small differences (noise)
            diff_pixels = np.sum(np.any(diff_array > threshold, axis=2))
            
            # Calculate similarity (1.0 = identical, 0.0 = completely different)
            total_pixels = img1.width * img1.height
            similarity = 1.0 - (diff_pixels / total_pixels)
            
            return similarity, int(diff_pixels)
            
        except Exception as e:
            self.logger.error(f"Failed to compare images: {e}")
            return 0.0, 0
    
    async def _compare_images_advanced(
        self,
        img1: Image.Image,
        img2: Image.Image,
        threshold: int = 30
    ) -> Dict[str, Any]:
        """
        Advanced image comparison with detailed difference analysis.
        
        Provides comprehensive comparison metrics including:
        - Pixel-level differences
        - Structural similarity
        - Difference regions
        - Change heatmap data
        
        Args:
            img1: First image
            img2: Second image
            threshold: Pixel difference threshold (0-255)
            
        Returns:
            Dictionary containing:
                - similarity: Overall similarity score (0.0-1.0)
                - diff_pixels: Number of different pixels
                - diff_percentage: Percentage of different pixels
                - mean_diff: Average pixel difference magnitude
                - max_diff: Maximum pixel difference
                - diff_regions: List of bounding boxes for changed regions
                - structural_similarity: SSIM-like metric
        """
        try:
            # Ensure images are same size
            if img1.size != img2.size:
                img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
            
            # Convert to numpy arrays
            arr1 = np.array(img1, dtype=np.float32)
            arr2 = np.array(img2, dtype=np.float32)
            
            # Calculate absolute difference
            diff = np.abs(arr1 - arr2)
            
            # Calculate per-pixel difference magnitude (max across RGB channels)
            diff_magnitude = np.max(diff, axis=2)
            
            # Create binary mask of changed pixels
            changed_mask = diff_magnitude > threshold
            diff_pixels = np.sum(changed_mask)
            total_pixels = img1.width * img1.height
            
            # Calculate similarity metrics
            similarity = 1.0 - (diff_pixels / total_pixels)
            diff_percentage = (diff_pixels / total_pixels) * 100
            mean_diff = np.mean(diff_magnitude[changed_mask]) if diff_pixels > 0 else 0.0
            max_diff = np.max(diff_magnitude)
            
            # Find difference regions (connected components)
            diff_regions = self._find_difference_regions(changed_mask)
            
            # Calculate structural similarity (simplified SSIM)
            structural_similarity = self._calculate_structural_similarity(arr1, arr2)
            
            return {
                'similarity': float(similarity),
                'diff_pixels': int(diff_pixels),
                'diff_percentage': float(diff_percentage),
                'mean_diff': float(mean_diff),
                'max_diff': float(max_diff),
                'diff_regions': diff_regions,
                'structural_similarity': float(structural_similarity),
                'threshold_used': threshold
            }
            
        except Exception as e:
            self.logger.error(f"Failed advanced image comparison: {e}")
            return {
                'similarity': 0.0,
                'diff_pixels': 0,
                'diff_percentage': 0.0,
                'mean_diff': 0.0,
                'max_diff': 0.0,
                'diff_regions': [],
                'structural_similarity': 0.0,
                'threshold_used': threshold
            }
    
    def _find_difference_regions(
        self,
        mask: np.ndarray,
        min_region_size: int = 100
    ) -> List[Dict[str, int]]:
        """
        Find bounding boxes of difference regions in binary mask.
        
        Args:
            mask: Binary mask of changed pixels (True = changed)
            min_region_size: Minimum number of pixels for a region
            
        Returns:
            List of region dictionaries with keys: left, top, right, bottom, area
        """
        try:
            # Find connected components using simple flood fill approach
            # For production, could use scipy.ndimage.label or cv2.connectedComponents
            
            regions = []
            visited = np.zeros_like(mask, dtype=bool)
            height, width = mask.shape
            
            def flood_fill(start_y: int, start_x: int) -> Optional[Dict[str, int]]:
                """Flood fill to find connected region."""
                stack = [(start_y, start_x)]
                min_x, min_y = start_x, start_y
                max_x, max_y = start_x, start_y
                area = 0
                
                while stack and area < 10000:  # Limit to prevent infinite loops
                    y, x = stack.pop()
                    
                    if (y < 0 or y >= height or x < 0 or x >= width or
                        visited[y, x] or not mask[y, x]):
                        continue
                    
                    visited[y, x] = True
                    area += 1
                    
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
                    
                    # Add neighbors
                    stack.extend([(y-1, x), (y+1, x), (y, x-1), (y, x+1)])
                
                if area >= min_region_size:
                    return {
                        'left': int(min_x),
                        'top': int(min_y),
                        'right': int(max_x),
                        'bottom': int(max_y),
                        'area': int(area),
                        'width': int(max_x - min_x + 1),
                        'height': int(max_y - min_y + 1)
                    }
                return None
            
            # Find all regions
            for y in range(height):
                for x in range(width):
                    if mask[y, x] and not visited[y, x]:
                        region = flood_fill(y, x)
                        if region:
                            regions.append(region)
                            
                            # Limit number of regions to prevent excessive processing
                            if len(regions) >= 50:
                                return regions
            
            return regions
            
        except Exception as e:
            self.logger.error(f"Failed to find difference regions: {e}")
            return []
    
    def _calculate_structural_similarity(
        self,
        arr1: np.ndarray,
        arr2: np.ndarray,
        window_size: int = 11
    ) -> float:
        """
        Calculate structural similarity between two images.
        
        Simplified SSIM (Structural Similarity Index) implementation.
        
        Args:
            arr1: First image as numpy array
            arr2: Second image as numpy array
            window_size: Size of sliding window for local comparison
            
        Returns:
            Structural similarity score (0.0-1.0)
        """
        try:
            # Convert to grayscale for SSIM calculation
            if len(arr1.shape) == 3:
                gray1 = np.mean(arr1, axis=2)
                gray2 = np.mean(arr2, axis=2)
            else:
                gray1 = arr1
                gray2 = arr2
            
            # Constants for SSIM
            C1 = (0.01 * 255) ** 2
            C2 = (0.03 * 255) ** 2
            
            # Calculate means
            mu1 = gray1.mean()
            mu2 = gray2.mean()
            
            # Calculate variances and covariance
            sigma1_sq = np.var(gray1)
            sigma2_sq = np.var(gray2)
            sigma12 = np.cov(gray1.flatten(), gray2.flatten())[0, 1]
            
            # Calculate SSIM
            numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
            denominator = (mu1**2 + mu2**2 + C1) * (sigma1_sq + sigma2_sq + C2)
            
            ssim = numerator / denominator if denominator != 0 else 0.0
            
            # Normalize to 0-1 range (SSIM can be negative)
            ssim = max(0.0, min(1.0, (ssim + 1) / 2))
            
            return ssim
            
        except Exception as e:
            self.logger.error(f"Failed to calculate structural similarity: {e}")
            return 0.0
    
    async def compare_region(
        self,
        img1: Image.Image,
        img2: Image.Image,
        region: Dict[str, int],
        threshold: int = 30
    ) -> Dict[str, Any]:
        """
        Compare a specific region between two images.
        
        Useful for verifying changes at specific locations (e.g., click targets).
        
        Args:
            img1: First image
            img2: Second image
            region: Dictionary with keys: left, top, right, bottom
            threshold: Pixel difference threshold
            
        Returns:
            Dictionary with comparison results for the region
        """
        try:
            # Extract region coordinates
            left = region.get('left', 0)
            top = region.get('top', 0)
            right = region.get('right', img1.width)
            bottom = region.get('bottom', img1.height)
            
            # Validate coordinates
            left = max(0, min(left, img1.width - 1))
            top = max(0, min(top, img1.height - 1))
            right = max(left + 1, min(right, img1.width))
            bottom = max(top + 1, min(bottom, img1.height))
            
            # Crop regions
            region1 = img1.crop((left, top, right, bottom))
            region2 = img2.crop((left, top, right, bottom))
            
            # Compare cropped regions
            comparison = await self._compare_images_advanced(region1, region2, threshold)
            
            # Add region info
            comparison['region'] = {
                'left': left,
                'top': top,
                'right': right,
                'bottom': bottom,
                'width': right - left,
                'height': bottom - top
            }
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Failed to compare region: {e}")
            return {
                'similarity': 0.0,
                'diff_pixels': 0,
                'error': str(e)
            }
    
    def get_verification_results(self) -> List[VerificationResult]:
        """
        Get all verification results.
        
        Returns:
            List of VerificationResult objects
        """
        return self.verification_results.copy()
    
    def get_success_rate(self) -> float:
        """
        Calculate overall success rate of verifications.
        
        Returns:
            Success rate (0.0 to 1.0)
        """
        if not self.verification_results:
            return 0.0
        
        successful = sum(1 for r in self.verification_results if r.success)
        return successful / len(self.verification_results)
    
    def clear_results(self) -> None:
        """Clear all verification results and screenshots."""
        self.verification_results.clear()
        self.verification_screenshots.clear()
        self.logger.info("Verification results cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get verification statistics.
        
        Returns:
            Dictionary with verification stats
        """
        if not self.verification_results:
            return {
                'total_verifications': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'average_confidence': 0.0
            }
        
        successful = sum(1 for r in self.verification_results if r.success)
        failed = len(self.verification_results) - successful
        avg_confidence = sum(r.confidence for r in self.verification_results) / len(self.verification_results)
        
        return {
            'total_verifications': len(self.verification_results),
            'successful': successful,
            'failed': failed,
            'success_rate': successful / len(self.verification_results),
            'average_confidence': avg_confidence,
            'screenshots_stored': len(self.verification_screenshots)
        }
