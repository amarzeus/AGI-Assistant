"""
Tests for browser automation platform.
"""

import pytest
import asyncio
from src.services.platforms.browser_automation import BrowserAutomationPlatform, PLAYWRIGHT_AVAILABLE


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestBrowserAutomation:
    """Test browser automation platform."""
    
    @pytest.fixture
    async def browser(self):
        """Create browser instance."""
        platform = BrowserAutomationPlatform()
        await platform.initialize(headless=True)
        yield platform
        await platform.close()
    
    @pytest.mark.asyncio
    async def test_browser_initialization(self):
        """Test browser initialization."""
        platform = BrowserAutomationPlatform()
        assert platform.enabled == PLAYWRIGHT_AVAILABLE
        
        if platform.enabled:
            await platform.initialize(headless=True)
            assert platform._initialized
            await platform.close()
    
    @pytest.mark.asyncio
    async def test_navigation(self, browser):
        """Test page navigation."""
        await browser.navigate("https://example.com")
        url = await browser.get_url()
        assert "example.com" in url
        
        title = await browser.get_title()
        assert len(title) > 0
    
    @pytest.mark.asyncio
    async def test_element_interaction(self, browser):
        """Test element interaction."""
        # Navigate to a test page
        await browser.navigate("https://example.com")
        
        # Get text from page
        text = await browser.get_text("h1")
        assert len(text) > 0
    
    @pytest.mark.asyncio
    async def test_screenshot(self, browser):
        """Test screenshot capture."""
        await browser.navigate("https://example.com")
        screenshot_path = await browser.screenshot()
        
        assert screenshot_path is not None
        assert screenshot_path.endswith(".png")
    
    @pytest.mark.asyncio
    async def test_wait_for_selector(self, browser):
        """Test waiting for selector."""
        await browser.navigate("https://example.com")
        
        # Wait for body element
        await browser.wait_for_selector("body", timeout=5000)
    
    @pytest.mark.asyncio
    async def test_javascript_evaluation(self, browser):
        """Test JavaScript execution."""
        await browser.navigate("https://example.com")
        
        # Execute JavaScript
        result = await browser.evaluate("document.title")
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_form_filling(self, browser):
        """Test form filling."""
        # This would need a test page with a form
        # For now, just test the method exists
        assert hasattr(browser, 'fill_form')
        assert hasattr(browser, 'submit_form')
    
    @pytest.mark.asyncio
    async def test_multiple_tabs(self, browser):
        """Test multi-tab support."""
        await browser.navigate("https://example.com")
        
        # Open new tab
        await browser.new_tab("https://example.org")
        url = await browser.get_url()
        assert "example.org" in url
        
        # Close tab
        await browser.close_tab()
        url = await browser.get_url()
        assert "example.com" in url


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="Playwright not installed")
class TestBrowserActions:
    """Test specific browser actions."""
    
    @pytest.fixture
    async def browser(self):
        """Create browser instance."""
        platform = BrowserAutomationPlatform()
        await platform.initialize(headless=True)
        yield platform
        await platform.close()
    
    @pytest.mark.asyncio
    async def test_click_action(self, browser):
        """Test click action."""
        await browser.navigate("https://example.com")
        # Would need a clickable element to test properly
        assert hasattr(browser, 'click')
    
    @pytest.mark.asyncio
    async def test_type_action(self, browser):
        """Test type action."""
        await browser.navigate("https://example.com")
        # Would need an input field to test properly
        assert hasattr(browser, 'type_text')
        assert hasattr(browser, 'fill')
    
    @pytest.mark.asyncio
    async def test_keyboard_actions(self, browser):
        """Test keyboard actions."""
        await browser.navigate("https://example.com")
        
        # Test key press
        await browser.press_key("Enter")
        
        # Test hotkey
        await browser.hotkey("Control", "a")
    
    @pytest.mark.asyncio
    async def test_data_extraction(self, browser):
        """Test data extraction."""
        await browser.navigate("https://example.com")
        
        # Get text
        text = await browser.get_text("body")
        assert len(text) > 0
        
        # Get all text
        texts = await browser.get_all_text("p")
        assert isinstance(texts, list)


def test_browser_platform_availability():
    """Test browser platform availability check."""
    platform = BrowserAutomationPlatform()
    assert platform.enabled == PLAYWRIGHT_AVAILABLE
    
    if not PLAYWRIGHT_AVAILABLE:
        assert platform._playwright is None
        assert platform._browser is None
        assert platform._page is None


@pytest.mark.asyncio
async def test_browser_error_handling():
    """Test error handling when browser not initialized."""
    platform = BrowserAutomationPlatform()
    
    if platform.enabled:
        # Should raise error when not initialized
        with pytest.raises(RuntimeError, match="not initialized"):
            await platform.navigate("https://example.com")
