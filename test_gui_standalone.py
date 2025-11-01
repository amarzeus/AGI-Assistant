"""Standalone GUI test - Shows the wxPython GUI without requiring all dependencies."""

import sys
import wx

# Add src to path
sys.path.insert(0, '.')

from src.wxui.main_frame import MainFrame


def main():
    """Run a standalone GUI test."""
    print("=" * 60)
    print("AGI Assistant - wxPython GUI Test")
    print("=" * 60)
    print()
    print("Testing native Windows GUI...")
    print()
    
    # Create wx application
    app = wx.App(False)
    app.SetAppDisplayName("AGI Assistant")
    
    try:
        # Create and show main frame
        frame = MainFrame(None)
        frame.Show()
        
        print("✓ Main window created")
        print("✓ System tray icon initialized")
        print("✓ All panels loaded")
        print()
        print("Window should be visible now!")
        print("You can:")
        print("  - Click buttons (they'll work in demo mode)")
        print("  - Switch between tabs")
        print("  - Right-click system tray icon")
        print("  - Try keyboard shortcuts (Ctrl+Shift+R, Ctrl+P)")
        print()
        print("Close the window or press Ctrl+C to exit")
        print("=" * 60)
        
        # Run event loop
        app.MainLoop()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

