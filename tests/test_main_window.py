"""Test main window UI with wxPython."""

import sys
import pytest

try:
    import wx
    from src.wxui.main_frame import MainFrame
    WX_AVAILABLE = True
except ImportError:
    WX_AVAILABLE = False


@pytest.mark.skipif(not WX_AVAILABLE, reason="wxPython not available")
def test_main_frame_creation():
    """Test that MainFrame can be created."""
    app = wx.App(False)
    frame = MainFrame(None)
    assert frame is not None
    assert frame.GetTitle() == "AGI Assistant"
    frame.Destroy()
    app.Destroy()


@pytest.mark.skipif(not WX_AVAILABLE, reason="wxPython not available")
def test_main_frame_guiport_interface():
    """Test that MainFrame implements GuiPort interface."""
    app = wx.App(False)
    frame = MainFrame(None)
    
    # Test GuiPort methods exist
    assert hasattr(frame, 'get_recording_state')
    assert hasattr(frame, 'update_recording_state')
    assert hasattr(frame, 'add_action_to_feed')
    assert hasattr(frame, 'set_patterns')
    
    # Test initial state
    state = frame.get_recording_state()
    assert isinstance(state, dict)
    assert 'is_recording' in state
    assert 'is_paused' in state
    
    frame.Destroy()
    app.Destroy()
