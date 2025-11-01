"""Test activity feed - updated for wxPython migration."""
# Note: Activity panel is now in src/wxui/panels/activity.py
# These tests should be updated to test the wxPython activity panel

import pytest

pytestmark = pytest.mark.skip(reason="Original PyQt6 activity feed tests - needs update for wxPython panels")
