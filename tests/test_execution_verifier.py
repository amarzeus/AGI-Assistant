"""Tests for execution verifier service."""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np

from src.services.execution_verifier import (
    ExecutionVerifier,
    VerificationResult
)


@pytest.fixture
async def verifier():
    """Create execution verifier for testing."""
    verifier = ExecutionVerifier()
    await verifier.initialize()
    yield verifier
    verifier.clear_results()


@pytest.fixture
def sample_action():
    """Create sample action data."""
    return {
        'id': 'test_action_001',
        'type': 'click',
        'x': 100,
        'y': 200
    }


@pytest.fixture
def create_test_image():
    """Factory for creating test images."""
    def _create_image(width=800, height=600, color=(255, 255, 255)):
        """Create a test image with specified dimensions and color."""
        img = Image.new('RGB', (width, height), color)
        return img
    return _create_image


@pytest.mark.asyncio
async def test_verifier_initialization(verifier):
    """Test verifier initialization."""
    assert verifier._screenshot_dir is not None
    assert verifier._screenshot_dir.exists()
    assert len(verifier.verification_results) == 0
    assert len(verifier.verification_screenshots) == 0


@pytest.mark.asyncio
async def test_capture_before_state(verifier, sample_action):
    """Test capturing before state screenshot."""
    before_key = await verifier.capture_before_state(sample_action)
    
    assert before_key != ""
    assert before_key.startswith("before_")
    assert before_key in verifier.verification_screenshots
    
    # Check screenshot file exists
    screenshot_path = verifier.verification_screenshots[before_key]
    assert screenshot_path.exists()


@pytest.mark.asyncio
async def test_capture_after_state(verifier, sample_action):
    """Test capturing after state screenshot."""
    after_key = await verifier.capture_after_state(sample_action)
    
    assert after_key != ""
    assert after_key.startswith("after_")
    assert after_key in verifier.verification_screenshots
    
    # Check screenshot file exists
    screenshot_path = verifier.verification_screenshots[after_key]
    assert screenshot_path.exists()


@pytest.mark.asyncio
async def test_verify_action_missing_screenshots(verifier, sample_action):
    """Test verification with missing screenshots."""
    result = await verifier.verify_action(
        sample_action,
        "nonexistent_before",
        "nonexistent_after"
    )
    
    assert isinstance(result, VerificationResult)
    assert result.success is False
    assert result.confidence == 0.0
    assert "Missing before/after screenshots" in result.error_message


@pytest.mark.asyncio
async def test_compare_images_identical(verifier, create_test_image):
    """Test image comparison with identical images."""
    img1 = create_test_image(color=(100, 150, 200))
    img2 = create_test_image(color=(100, 150, 200))
    
    similarity, diff_pixels = await verifier._compare_images(img1, img2)
    
    assert similarity == 1.0
    assert diff_pixels == 0


@pytest.mark.asyncio
async def test_compare_images_different(verifier, create_test_image):
    """Test image comparison with different images."""
    img1 = create_test_image(color=(100, 150, 200))
    img2 = create_test_image(color=(200, 100, 50))
    
    similarity, diff_pixels = await verifier._compare_images(img1, img2)
    
    assert similarity < 1.0
    assert diff_pixels > 0


@pytest.mark.asyncio
async def test_compare_images_different_sizes(verifier, create_test_image):
    """Test image comparison with different sized images."""
    img1 = create_test_image(width=800, height=600)
    img2 = create_test_image(width=1024, height=768)
    
    # Should resize and compare
    similarity, diff_pixels = await verifier._compare_images(img1, img2)
    
    assert 0.0 <= similarity <= 1.0
    assert diff_pixels >= 0


@pytest.mark.asyncio
async def test_verify_click_with_changes(verifier, create_test_image):
    """Test click verification with UI changes."""
    # Create before and after images with a change at click location
    before_img = create_test_image(color=(255, 255, 255))
    after_img = create_test_image(color=(255, 255, 255))
    
    # Add a change at click location (100, 200)
    pixels = after_img.load()
    for x in range(80, 120):
        for y in range(180, 220):
            pixels[x, y] = (200, 200, 200)
    
    # Save images temporarily
    before_path = verifier._screenshot_dir / "test_before.png"
    after_path = verifier._screenshot_dir / "test_after.png"
    before_img.save(str(before_path))
    after_img.save(str(after_path))
    
    result = await verifier.verify_click(100, 200, str(before_path), str(after_path))
    
    assert isinstance(result, VerificationResult)
    assert result.action_type == "click"
    assert result.verification_method == "region_comparison_advanced"
    assert len(result.differences) > 0
    
    # Cleanup
    before_path.unlink()
    after_path.unlink()


@pytest.mark.asyncio
async def test_verify_type_with_changes(verifier, create_test_image):
    """Test type verification with text changes."""
    # Create before and after images with changes
    before_img = create_test_image(color=(255, 255, 255))
    after_img = create_test_image(color=(250, 250, 250))  # Slight change
    
    # Save images temporarily
    before_path = verifier._screenshot_dir / "test_type_before.png"
    after_path = verifier._screenshot_dir / "test_type_after.png"
    before_img.save(str(before_path))
    after_img.save(str(after_path))
    
    result = await verifier.verify_type("Hello World", str(before_path), str(after_path))
    
    assert isinstance(result, VerificationResult)
    assert result.action_type == "type"
    assert result.verification_method == "image_comparison_advanced"
    assert 'text_length' in result.metadata
    assert result.metadata['text_length'] == 11
    
    # Cleanup
    before_path.unlink()
    after_path.unlink()


@pytest.mark.asyncio
async def test_verify_navigation(verifier, create_test_image):
    """Test navigation verification."""
    # Create valid after image
    after_img = create_test_image(color=(128, 128, 128))
    
    # Save image temporarily
    after_path = verifier._screenshot_dir / "test_nav_after.png"
    after_img.save(str(after_path))
    
    result = await verifier.verify_navigation("https://example.com", str(after_path))
    
    assert isinstance(result, VerificationResult)
    assert result.action_type == "navigation"
    assert result.verification_method == "screenshot_validity"
    assert 'target' in result.metadata
    assert 'mean_brightness' in result.metadata
    
    # Cleanup
    after_path.unlink()


@pytest.mark.asyncio
async def test_verify_generic_action(verifier, create_test_image):
    """Test generic action verification."""
    # Create before and after images with changes
    before_img = create_test_image(color=(255, 255, 255))
    after_img = create_test_image(color=(240, 240, 240))
    
    # Save images temporarily
    before_path = verifier._screenshot_dir / "test_generic_before.png"
    after_path = verifier._screenshot_dir / "test_generic_after.png"
    before_img.save(str(before_path))
    after_img.save(str(after_path))
    
    result = await verifier._verify_generic(str(before_path), str(after_path))
    
    assert isinstance(result, VerificationResult)
    assert result.action_type == "generic"
    assert result.verification_method == "full_image_comparison_advanced"
    
    # Cleanup
    before_path.unlink()
    after_path.unlink()


@pytest.mark.asyncio
async def test_verification_result_to_dict():
    """Test VerificationResult serialization."""
    result = VerificationResult(
        action_id="test_001",
        action_type="click",
        success=True,
        confidence=0.85,
        verification_method="region_comparison"
    )
    
    data = result.to_dict()
    
    assert data['action_id'] == "test_001"
    assert data['action_type'] == "click"
    assert data['success'] is True
    assert data['confidence'] == 0.85
    assert data['verification_method'] == "region_comparison"
    assert 'timestamp' in data


@pytest.mark.asyncio
async def test_verification_result_from_dict():
    """Test VerificationResult deserialization."""
    data = {
        'action_id': "test_002",
        'action_type': "type",
        'success': False,
        'confidence': 0.45,
        'verification_method': "image_comparison",
        'timestamp': datetime.now().isoformat(),
        'differences': [],
        'metadata': {}
    }
    
    result = VerificationResult.from_dict(data)
    
    assert result.action_id == "test_002"
    assert result.action_type == "type"
    assert result.success is False
    assert result.confidence == 0.45


@pytest.mark.asyncio
async def test_get_verification_results(verifier):
    """Test getting verification results."""
    # Add some results
    result1 = VerificationResult(
        action_id="test_001",
        action_type="click",
        success=True,
        confidence=0.9
    )
    result2 = VerificationResult(
        action_id="test_002",
        action_type="type",
        success=False,
        confidence=0.4
    )
    
    verifier.verification_results.append(result1)
    verifier.verification_results.append(result2)
    
    results = verifier.get_verification_results()
    
    assert len(results) == 2
    assert results[0].action_id == "test_001"
    assert results[1].action_id == "test_002"


@pytest.mark.asyncio
async def test_get_success_rate(verifier):
    """Test success rate calculation."""
    # Add results
    verifier.verification_results.append(
        VerificationResult(action_id="1", action_type="click", success=True, confidence=0.9)
    )
    verifier.verification_results.append(
        VerificationResult(action_id="2", action_type="type", success=True, confidence=0.8)
    )
    verifier.verification_results.append(
        VerificationResult(action_id="3", action_type="click", success=False, confidence=0.3)
    )
    
    success_rate = verifier.get_success_rate()
    
    assert success_rate == pytest.approx(2.0 / 3.0, rel=0.01)


@pytest.mark.asyncio
async def test_get_success_rate_empty(verifier):
    """Test success rate with no results."""
    success_rate = verifier.get_success_rate()
    assert success_rate == 0.0


@pytest.mark.asyncio
async def test_clear_results(verifier):
    """Test clearing verification results."""
    # Add some data
    verifier.verification_results.append(
        VerificationResult(action_id="1", action_type="click", success=True, confidence=0.9)
    )
    verifier.verification_screenshots["test_key"] = Path("test_path")
    
    assert len(verifier.verification_results) > 0
    assert len(verifier.verification_screenshots) > 0
    
    verifier.clear_results()
    
    assert len(verifier.verification_results) == 0
    assert len(verifier.verification_screenshots) == 0


@pytest.mark.asyncio
async def test_get_stats(verifier):
    """Test getting verification statistics."""
    # Add results
    verifier.verification_results.append(
        VerificationResult(action_id="1", action_type="click", success=True, confidence=0.9)
    )
    verifier.verification_results.append(
        VerificationResult(action_id="2", action_type="type", success=False, confidence=0.4)
    )
    
    stats = verifier.get_stats()
    
    assert stats['total_verifications'] == 2
    assert stats['successful'] == 1
    assert stats['failed'] == 1
    assert stats['success_rate'] == 0.5
    assert stats['average_confidence'] == pytest.approx(0.65, rel=0.01)


@pytest.mark.asyncio
async def test_get_stats_empty(verifier):
    """Test statistics with no results."""
    stats = verifier.get_stats()
    
    assert stats['total_verifications'] == 0
    assert stats['successful'] == 0
    assert stats['failed'] == 0
    assert stats['success_rate'] == 0.0
    assert stats['average_confidence'] == 0.0


@pytest.mark.asyncio
async def test_integration_with_executor(verifier, sample_action):
    """Test integration flow: capture before, execute, capture after, verify."""
    # Capture before state
    before_key = await verifier.capture_before_state(sample_action)
    assert before_key != ""
    
    # Simulate action execution (wait a bit)
    await asyncio.sleep(0.1)
    
    # Capture after state
    after_key = await verifier.capture_after_state(sample_action)
    assert after_key != ""
    
    # Verify action
    result = await verifier.verify_action(sample_action, before_key, after_key)
    
    assert isinstance(result, VerificationResult)
    assert result.action_id == sample_action['id']
    assert result.action_type == sample_action['type']
    assert result.before_screenshot is not None
    assert result.after_screenshot is not None
    
    # Check result was stored
    assert len(verifier.verification_results) == 1
    assert verifier.verification_results[0].action_id == sample_action['id']


@pytest.mark.asyncio
async def test_compare_images_advanced(verifier, create_test_image):
    """Test advanced image comparison with detailed metrics."""
    # Create images with known differences
    img1 = create_test_image(color=(255, 255, 255))
    img2 = create_test_image(color=(255, 255, 255))
    
    # Add a specific change region (100x100 pixels)
    pixels = img2.load()
    for x in range(100, 200):
        for y in range(100, 200):
            pixels[x, y] = (200, 200, 200)
    
    comparison = await verifier._compare_images_advanced(img1, img2, threshold=30)
    
    assert 'similarity' in comparison
    assert 'diff_pixels' in comparison
    assert 'diff_percentage' in comparison
    assert 'mean_diff' in comparison
    assert 'max_diff' in comparison
    assert 'diff_regions' in comparison
    assert 'structural_similarity' in comparison
    
    # Should detect the change
    assert comparison['similarity'] < 1.0
    assert comparison['diff_pixels'] > 0
    assert comparison['diff_percentage'] > 0
    
    # Should find at least one difference region
    assert len(comparison['diff_regions']) > 0


@pytest.mark.asyncio
async def test_compare_images_advanced_identical(verifier, create_test_image):
    """Test advanced comparison with identical images."""
    img1 = create_test_image(color=(128, 128, 128))
    img2 = create_test_image(color=(128, 128, 128))
    
    comparison = await verifier._compare_images_advanced(img1, img2)
    
    assert comparison['similarity'] == 1.0
    assert comparison['diff_pixels'] == 0
    assert comparison['diff_percentage'] == 0.0
    assert len(comparison['diff_regions']) == 0


@pytest.mark.asyncio
async def test_find_difference_regions(verifier):
    """Test finding difference regions in binary mask."""
    # Create a mask with two separate regions
    mask = np.zeros((600, 800), dtype=bool)
    
    # Region 1: 100x100 at (50, 50)
    mask[50:150, 50:150] = True
    
    # Region 2: 80x80 at (300, 300)
    mask[300:380, 300:380] = True
    
    regions = verifier._find_difference_regions(mask, min_region_size=100)
    
    # Should find both regions
    assert len(regions) >= 2
    
    # Check region properties
    for region in regions:
        assert 'left' in region
        assert 'top' in region
        assert 'right' in region
        assert 'bottom' in region
        assert 'area' in region
        assert 'width' in region
        assert 'height' in region
        assert region['area'] >= 100


@pytest.mark.asyncio
async def test_find_difference_regions_small_regions(verifier):
    """Test that small regions are filtered out."""
    # Create a mask with many small regions
    mask = np.zeros((600, 800), dtype=bool)
    
    # Add small scattered regions (< 100 pixels each)
    for i in range(10):
        x, y = i * 50, i * 50
        mask[y:y+5, x:x+5] = True
    
    regions = verifier._find_difference_regions(mask, min_region_size=100)
    
    # Should not find any regions (all too small)
    assert len(regions) == 0


@pytest.mark.asyncio
async def test_calculate_structural_similarity(verifier, create_test_image):
    """Test structural similarity calculation."""
    # Identical images should have high SSIM
    img1 = create_test_image(color=(128, 128, 128))
    img2 = create_test_image(color=(128, 128, 128))
    
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)
    
    ssim = verifier._calculate_structural_similarity(arr1, arr2)
    
    assert 0.0 <= ssim <= 1.0
    assert ssim > 0.9  # Should be very similar


@pytest.mark.asyncio
async def test_calculate_structural_similarity_different(verifier, create_test_image):
    """Test structural similarity with different images."""
    img1 = create_test_image(color=(50, 50, 50))
    img2 = create_test_image(color=(200, 200, 200))
    
    arr1 = np.array(img1, dtype=np.float32)
    arr2 = np.array(img2, dtype=np.float32)
    
    ssim = verifier._calculate_structural_similarity(arr1, arr2)
    
    assert 0.0 <= ssim <= 1.0
    # Different brightness but same structure, so SSIM should be moderate
    assert 0.3 < ssim < 0.9


@pytest.mark.asyncio
async def test_compare_region(verifier, create_test_image):
    """Test region-based comparison."""
    # Create images with change in specific region
    img1 = create_test_image(color=(255, 255, 255))
    img2 = create_test_image(color=(255, 255, 255))
    
    # Add change in region (100, 100) to (200, 200)
    pixels = img2.load()
    for x in range(100, 200):
        for y in range(100, 200):
            pixels[x, y] = (200, 200, 200)
    
    # Compare that specific region
    region = {'left': 100, 'top': 100, 'right': 200, 'bottom': 200}
    comparison = await verifier.compare_region(img1, img2, region)
    
    assert 'similarity' in comparison
    assert 'region' in comparison
    assert comparison['region']['left'] == 100
    assert comparison['region']['top'] == 100
    assert comparison['region']['right'] == 200
    assert comparison['region']['bottom'] == 200
    
    # Should detect change in this region
    assert comparison['similarity'] < 1.0


@pytest.mark.asyncio
async def test_compare_region_no_change(verifier, create_test_image):
    """Test region comparison with no changes."""
    img1 = create_test_image(color=(128, 128, 128))
    img2 = create_test_image(color=(128, 128, 128))
    
    region = {'left': 50, 'top': 50, 'right': 150, 'bottom': 150}
    comparison = await verifier.compare_region(img1, img2, region)
    
    # Should be identical
    assert comparison['similarity'] == 1.0
    assert comparison['diff_pixels'] == 0


@pytest.mark.asyncio
async def test_verify_click_enhanced(verifier, create_test_image):
    """Test enhanced click verification with detailed analysis."""
    # Create before and after images with change at click location
    before_img = create_test_image(color=(255, 255, 255))
    after_img = create_test_image(color=(255, 255, 255))
    
    # Add change at click location (150, 150)
    pixels = after_img.load()
    for x in range(120, 180):
        for y in range(120, 180):
            pixels[x, y] = (200, 200, 200)
    
    # Save images
    before_path = verifier._screenshot_dir / "test_click_before.png"
    after_path = verifier._screenshot_dir / "test_click_after.png"
    before_img.save(str(before_path))
    after_img.save(str(after_path))
    
    result = await verifier.verify_click(150, 150, str(before_path), str(after_path))
    
    assert result.verification_method == "region_comparison_advanced"
    assert len(result.differences) == 2  # Region and full image comparisons
    
    # Check region comparison
    region_diff = result.differences[0]
    assert region_diff['type'] == 'click_region'
    assert 'similarity' in region_diff
    assert 'diff_pixels' in region_diff
    assert 'structural_similarity' in region_diff
    
    # Check full image comparison
    full_diff = result.differences[1]
    assert full_diff['type'] == 'full_image'
    assert 'diff_regions' in full_diff
    
    # Cleanup
    before_path.unlink()
    after_path.unlink()


@pytest.mark.asyncio
async def test_verify_type_enhanced(verifier, create_test_image):
    """Test enhanced type verification with detailed analysis."""
    # Create images with text-like changes
    before_img = create_test_image(color=(255, 255, 255))
    after_img = create_test_image(color=(255, 255, 255))
    
    # Add several small regions (simulating text)
    pixels = after_img.load()
    for i in range(5):
        x_start = 100 + i * 30
        for x in range(x_start, x_start + 20):
            for y in range(100, 110):
                pixels[x, y] = (0, 0, 0)
    
    # Save images
    before_path = verifier._screenshot_dir / "test_type_before_enhanced.png"
    after_path = verifier._screenshot_dir / "test_type_after_enhanced.png"
    before_img.save(str(before_path))
    after_img.save(str(after_path))
    
    result = await verifier.verify_type("Hello", str(before_path), str(after_path))
    
    assert result.verification_method == "image_comparison_advanced"
    assert len(result.differences) > 0
    
    diff = result.differences[0]
    assert 'similarity' in diff
    assert 'diff_regions' in diff
    assert 'structural_similarity' in diff
    assert 'expected_change' in diff
    assert 'actual_change' in diff
    
    assert 'num_change_regions' in result.metadata
    
    # Cleanup
    before_path.unlink()
    after_path.unlink()


@pytest.mark.asyncio
async def test_verify_generic_enhanced(verifier, create_test_image):
    """Test enhanced generic verification."""
    # Create images with changes
    before_img = create_test_image(color=(255, 255, 255))
    after_img = create_test_image(color=(240, 240, 240))
    
    # Save images
    before_path = verifier._screenshot_dir / "test_generic_before_enhanced.png"
    after_path = verifier._screenshot_dir / "test_generic_after_enhanced.png"
    before_img.save(str(before_path))
    after_img.save(str(after_path))
    
    result = await verifier._verify_generic(str(before_path), str(after_path))
    
    assert result.verification_method == "full_image_comparison_advanced"
    assert len(result.differences) > 0
    
    diff = result.differences[0]
    assert 'similarity' in diff
    assert 'diff_percentage' in diff
    assert 'structural_similarity' in diff
    assert 'diff_regions' in diff
    
    assert 'num_change_regions' in result.metadata
    assert 'total_change_area' in result.metadata
    
    # Cleanup
    before_path.unlink()
    after_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
