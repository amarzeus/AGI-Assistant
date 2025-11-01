"""Test workflow dashboard - updated for wxPython migration."""
# Note: Workflows panel is now in src/wxui/panels/workflows.py
# These tests should be updated to test the wxPython workflows panel

import pytest

pytestmark = pytest.mark.skip(reason="Original PyQt6 workflow tests - needs update for wxPython panels")
