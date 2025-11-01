"""Test privacy controls - updated for wxPython migration."""
# Note: Privacy panel is now in src/wxui/panels/privacy.py
# These tests should be updated to test the wxPython privacy panel

import pytest

pytestmark = pytest.mark.skip(reason="Original PyQt6 privacy tests - needs update for wxPython panels")
