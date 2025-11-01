"""Test storage dashboard - updated for wxPython migration."""
# Note: Storage panel is now in src/wxui/panels/storage.py
# These tests should be updated to test the wxPython storage panel

import pytest

pytestmark = pytest.mark.skip(reason="Original PyQt6 storage tests - needs update for wxPython panels")
