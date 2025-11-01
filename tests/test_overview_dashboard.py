"""Test overview dashboard - updated for wxPython migration."""
# Note: Dashboard panels are now in src/wxui/panels/dashboard.py
# These tests should be updated to test the wxPython dashboard panel

import pytest

pytestmark = pytest.mark.skip(reason="Original PyQt6 dashboard tests - needs update for wxPython panels")
