"""Launcher script for AGI Assistant GUI application."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Launch the AGI Assistant GUI."""
    print("=" * 60)
    print("AGI Assistant - AI-Powered Workflow Automation")
    print("=" * 60)
    print()
    print("🚀 Starting GUI application...")
    print()

    try:
        # Check if wxPython is installed
        try:
            import wx
        except ImportError:
            print("❌ Error: wxPython is not installed")
            print()
            print("Please install required dependencies:")
            print("  pip install -r requirements.txt")
            print()
            input("Press Enter to exit...")
            sys.exit(1)

        # Check if wxasync is installed
        try:
            import wxasync
        except ImportError:
            print("❌ Error: wxasync is not installed")
            print()
            print("Please install required dependencies:")
            print("  pip install -r requirements.txt")
            print()
            input("Press Enter to exit...")
            sys.exit(1)

        # Import and run the GUI application
        from src.gui_main import main as gui_main

        print("✓ Dependencies loaded")
        print("✓ Initializing application...")
        print()
        print("📊 Dashboard Features:")
        print("  • Real-time activity monitoring")
        print("  • Pattern detection and workflow suggestions")
        print("  • Storage management")
        print("  • Privacy controls")
        print("  • Debug console")
        print()
        print("🔒 Privacy: All processing happens locally on your machine")
        print()
        print("-" * 60)
        print()

        # Run the application
        gui_main()

    except KeyboardInterrupt:
        print()
        print("⚠️  Application interrupted by user")
        print()

    except Exception as e:
        print()
        print("❌ Error starting application:")
        print(f"   {str(e)}")
        print()
        print("For help, please check:")
        print("  • SETUP_INSTRUCTIONS.md")
        print("  • USER_GUIDE.md")
        print("  • Log files in data/logs/")
        print()

        import traceback

        print("Technical details:")
        print("-" * 60)
        traceback.print_exc()
        print("-" * 60)
        print()

        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
