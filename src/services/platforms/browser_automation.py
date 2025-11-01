"""
Browser Automation Platform using Playwright.

This module provides browser automation capabilities for web interactions,
form filling, navigation, and data extraction.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None
    Playwright = None


class BrowserAutomationPlatform:
    """
    Browser automation platform using Playwright.
    
    Features:
    - Browser launch and management
    - Page navigation
    - Element interaction (click, type, select)
    - Form filling and submission
    - Data extraction
    - Screenshot capture
    - Multi-tab support
    """
    
    def __init__(self):
        """Initialize browser automation platform."""
        self.logger = logging.getLogger(__name__)
        self.enabled = PLAYWRIGHT_AVAILABLE
        
        # Playwright instances
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._context = None
        
        # State
        self._initialized = False
        self._browser_type = 'chromium'  # chromium, firefox, webkit
        
        if not self.enabled:
            self.logger.warning("Playwright not available - browser automation disabled")
        else:
            self.logger.info("Browser automation platform initialized")
    
    async def initialize(self, headless: bool = False, browser_type: str = 'chromium') -> None:
        """
        Initialize browser and create page.
        
        Args:
            headless: Run browser in headless mode
            browser_type: Browser type (chromium, firefox, webkit)
        """
        if not self.enabled:
            raise RuntimeError("Playwright not available")
        
        if self._initialized:
            self.logger.warning("Browser already initialized")
            return
        
        try:
            self.logger.info(f"Launching {browser_type} browser (headless={headless})...")
            
            # Start Playwright
            self._playwright = await async_playwright().start()
            
            # Launch browser
            self._browser_type = browser_type
            if browser_type == 'chromium':
                self._browser = await self._playwright.chromium.launch(headless=headless)
            elif browser_type == 'firefox':
                self._browser = await self._playwright.firefox.launch(headless=headless)
            elif browser_type == 'webkit':
                self._browser = await self._playwright.webkit.launch(headless=headless)
            else:
                raise ValueError(f"Unknown browser type: {browser_type}")
            
            # Create context and page
            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self._page = await self._context.new_page()
            
            self._initialized = True
            self.logger.info(f"Browser initialized successfully: {browser_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {e}")
            raise
    
    async def close(self) -> None:
        """Close browser and cleanup."""
        if not self._initialized:
            return
        
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._initialized = False
            
            self.logger.info("Browser closed")
            
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
    
    def _ensure_initialized(self) -> None:
        """Ensure browser is initialized."""
        if not self._initialized or not self._page:
            raise RuntimeError("Browser not initialized - call initialize() first")
    
    # Navigation Actions
    
    async def navigate(self, url: str, wait_until: str = 'load') -> None:
        """
        Navigate to URL.
        
        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
                       ('load', 'domcontentloaded', 'networkidle')
        """
        self._ensure_initialized()
        
        try:
            self.logger.info(f"Navigating to: {url}")
            await self._page.goto(url, wait_until=wait_until, timeout=30000)
            self.logger.debug(f"Navigation complete: {url}")
            
        except Exception as e:
            self.logger.error(f"Navigation failed: {e}")
            raise
    
    async def go_back(self) -> None:
        """Navigate back in history."""
        self._ensure_initialized()
        await self._page.go_back()
        self.logger.debug("Navigated back")
    
    async def go_forward(self) -> None:
        """Navigate forward in history."""
        self._ensure_initialized()
        await self._page.go_forward()
        self.logger.debug("Navigated forward")
    
    async def reload(self) -> None:
        """Reload current page."""
        self._ensure_initialized()
        await self._page.reload()
        self.logger.debug("Page reloaded")
    
    # Element Interaction
    
    async def click(self, selector: str, timeout: float = 30000) -> None:
        """
        Click element by selector.
        
        Args:
            selector: CSS selector for element
            timeout: Timeout in milliseconds
        """
        self._ensure_initialized()
        
        try:
            self.logger.debug(f"Clicking element: {selector}")
            await self._page.click(selector, timeout=timeout)
            await asyncio.sleep(0.2)  # Small delay after click
            
        except Exception as e:
            self.logger.error(f"Click failed for {selector}: {e}")
            raise
    
    async def type_text(self, selector: str, text: str, delay: float = 50) -> None:
        """
        Type text into element.
        
        Args:
            selector: CSS selector for element
            text: Text to type
            delay: Delay between keystrokes in milliseconds
        """
        self._ensure_initialized()
        
        try:
            self.logger.debug(f"Typing into {selector}: {text[:50]}...")
            await self._page.fill(selector, '')  # Clear first
            await self._page.type(selector, text, delay=delay)
            
        except Exception as e:
            self.logger.error(f"Type failed for {selector}: {e}")
            raise
    
    async def fill(self, selector: str, text: str) -> None:
        """
        Fill element with text (faster than type).
        
        Args:
            selector: CSS selector for element
            text: Text to fill
        """
        self._ensure_initialized()
        
        try:
            self.logger.debug(f"Filling {selector}: {text[:50]}...")
            await self._page.fill(selector, text)
            
        except Exception as e:
            self.logger.error(f"Fill failed for {selector}: {e}")
            raise
    
    async def select_option(self, selector: str, value: str) -> None:
        """
        Select option from dropdown.
        
        Args:
            selector: CSS selector for select element
            value: Option value to select
        """
        self._ensure_initialized()
        
        try:
            self.logger.debug(f"Selecting option {value} in {selector}")
            await self._page.select_option(selector, value)
            
        except Exception as e:
            self.logger.error(f"Select failed for {selector}: {e}")
            raise
    
    async def check(self, selector: str) -> None:
        """Check checkbox or radio button."""
        self._ensure_initialized()
        await self._page.check(selector)
        self.logger.debug(f"Checked: {selector}")
    
    async def uncheck(self, selector: str) -> None:
        """Uncheck checkbox."""
        self._ensure_initialized()
        await self._page.uncheck(selector)
        self.logger.debug(f"Unchecked: {selector}")
    
    async def press_key(self, key: str) -> None:
        """
        Press keyboard key.
        
        Args:
            key: Key name (e.g., 'Enter', 'Tab', 'Escape')
        """
        self._ensure_initialized()
        await self._page.keyboard.press(key)
        self.logger.debug(f"Pressed key: {key}")
    
    async def hotkey(self, *keys: str) -> None:
        """
        Press key combination.
        
        Args:
            keys: Keys to press together (e.g., 'Control', 'c')
        """
        self._ensure_initialized()
        
        # Press all keys down
        for key in keys:
            await self._page.keyboard.down(key)
        
        # Release all keys
        for key in reversed(keys):
            await self._page.keyboard.up(key)
        
        self.logger.debug(f"Pressed hotkey: {'+'.join(keys)}")
    
    # Data Extraction
    
    async def get_text(self, selector: str) -> str:
        """
        Get text content of element.
        
        Args:
            selector: CSS selector for element
            
        Returns:
            Text content
        """
        self._ensure_initialized()
        
        try:
            text = await self._page.text_content(selector)
            return text or ""
            
        except Exception as e:
            self.logger.error(f"Get text failed for {selector}: {e}")
            raise
    
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """
        Get attribute value of element.
        
        Args:
            selector: CSS selector for element
            attribute: Attribute name
            
        Returns:
            Attribute value or None
        """
        self._ensure_initialized()
        
        try:
            value = await self._page.get_attribute(selector, attribute)
            return value
            
        except Exception as e:
            self.logger.error(f"Get attribute failed for {selector}.{attribute}: {e}")
            raise
    
    async def get_all_text(self, selector: str) -> List[str]:
        """
        Get text from all matching elements.
        
        Args:
            selector: CSS selector for elements
            
        Returns:
            List of text content
        """
        self._ensure_initialized()
        
        try:
            elements = await self._page.query_selector_all(selector)
            texts = []
            for element in elements:
                text = await element.text_content()
                if text:
                    texts.append(text)
            return texts
            
        except Exception as e:
            self.logger.error(f"Get all text failed for {selector}: {e}")
            raise
    
    async def extract_table(self, selector: str) -> List[List[str]]:
        """
        Extract table data.
        
        Args:
            selector: CSS selector for table element
            
        Returns:
            2D list of table data
        """
        self._ensure_initialized()
        
        try:
            rows = await self._page.query_selector_all(f"{selector} tr")
            table_data = []
            
            for row in rows:
                cells = await row.query_selector_all("td, th")
                row_data = []
                for cell in cells:
                    text = await cell.text_content()
                    row_data.append(text.strip() if text else "")
                table_data.append(row_data)
            
            return table_data
            
        except Exception as e:
            self.logger.error(f"Extract table failed for {selector}: {e}")
            raise
    
    # Waiting and Verification
    
    async def wait_for_selector(self, selector: str, timeout: float = 30000) -> None:
        """
        Wait for element to appear.
        
        Args:
            selector: CSS selector for element
            timeout: Timeout in milliseconds
        """
        self._ensure_initialized()
        
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            self.logger.debug(f"Element appeared: {selector}")
            
        except Exception as e:
            self.logger.error(f"Wait for selector failed: {selector}")
            raise
    
    async def wait_for_url(self, url_pattern: str, timeout: float = 30000) -> None:
        """
        Wait for URL to match pattern.
        
        Args:
            url_pattern: URL pattern (can use wildcards)
            timeout: Timeout in milliseconds
        """
        self._ensure_initialized()
        
        try:
            await self._page.wait_for_url(url_pattern, timeout=timeout)
            self.logger.debug(f"URL matched: {url_pattern}")
            
        except Exception as e:
            self.logger.error(f"Wait for URL failed: {url_pattern}")
            raise
    
    async def wait(self, duration: float) -> None:
        """
        Wait for specified duration.
        
        Args:
            duration: Duration in seconds
        """
        await asyncio.sleep(duration)
    
    # Screenshot and Utilities
    
    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> str:
        """
        Take screenshot of page.
        
        Args:
            path: Path to save screenshot (auto-generated if None)
            full_page: Capture full scrollable page
            
        Returns:
            Path to screenshot file
        """
        self._ensure_initialized()
        
        try:
            if path is None:
                screenshots_dir = Path("~/agi-assistant-data/screenshots/browser").expanduser()
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                path = str(screenshots_dir / f"browser_{timestamp}.png")
            
            await self._page.screenshot(path=path, full_page=full_page)
            self.logger.debug(f"Screenshot saved: {path}")
            return path
            
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            raise
    
    async def get_url(self) -> str:
        """Get current page URL."""
        self._ensure_initialized()
        return self._page.url
    
    async def get_title(self) -> str:
        """Get current page title."""
        self._ensure_initialized()
        return await self._page.title()
    
    async def evaluate(self, script: str) -> Any:
        """
        Execute JavaScript in page context.
        
        Args:
            script: JavaScript code to execute
            
        Returns:
            Result of script execution
        """
        self._ensure_initialized()
        return await self._page.evaluate(script)
    
    # Form Handling
    
    async def fill_form(self, form_data: Dict[str, str]) -> None:
        """
        Fill form with data.
        
        Args:
            form_data: Dictionary mapping selectors to values
        """
        self._ensure_initialized()
        
        for selector, value in form_data.items():
            try:
                await self.fill(selector, value)
            except Exception as e:
                self.logger.error(f"Failed to fill {selector}: {e}")
                raise
        
        self.logger.info(f"Form filled with {len(form_data)} fields")
    
    async def submit_form(self, form_selector: str) -> None:
        """
        Submit form.
        
        Args:
            form_selector: CSS selector for form element
        """
        self._ensure_initialized()
        
        try:
            # Try to find submit button
            submit_button = await self._page.query_selector(f"{form_selector} button[type='submit']")
            if submit_button:
                await submit_button.click()
            else:
                # Fallback: press Enter on form
                await self._page.press(form_selector, 'Enter')
            
            self.logger.info("Form submitted")
            
        except Exception as e:
            self.logger.error(f"Form submission failed: {e}")
            raise
    
    # Alert Handling
    
    async def handle_alert(self, action: str = 'accept', prompt_text: Optional[str] = None) -> None:
        """
        Handle browser alert/confirm/prompt.
        
        Args:
            action: 'accept' or 'dismiss'
            prompt_text: Text to enter in prompt dialog
        """
        self._ensure_initialized()
        
        def handle_dialog(dialog):
            if prompt_text and dialog.type == 'prompt':
                dialog.accept(prompt_text)
            elif action == 'accept':
                dialog.accept()
            else:
                dialog.dismiss()
        
        self._page.on('dialog', handle_dialog)
        self.logger.debug(f"Alert handler registered: {action}")
    
    # Multi-tab Support
    
    async def new_tab(self, url: Optional[str] = None) -> None:
        """
        Open new tab.
        
        Args:
            url: URL to navigate to in new tab
        """
        self._ensure_initialized()
        
        new_page = await self._context.new_page()
        self._page = new_page
        
        if url:
            await self.navigate(url)
        
        self.logger.info("New tab opened")
    
    async def close_tab(self) -> None:
        """Close current tab."""
        self._ensure_initialized()
        
        pages = self._context.pages
        if len(pages) > 1:
            await self._page.close()
            self._page = pages[0]  # Switch to first tab
            self.logger.info("Tab closed")
        else:
            self.logger.warning("Cannot close last tab")
    
    def get_screen_size(self) -> Tuple[int, int]:
        """
        Get browser viewport size.
        
        Returns:
            Tuple of (width, height)
        """
        if self._page:
            viewport = self._page.viewport_size
            return (viewport['width'], viewport['height'])
        return (1920, 1080)  # Default
