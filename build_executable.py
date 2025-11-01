"""Build script for creating AGI Assistant Windows executable.

This script automates the build process using PyInstaller and prepares
the distribution package.

Usage:
    python build_executable.py [--clean] [--onefile]

Options:
    --clean     Clean previous build artifacts before building
    --onefile   Create a single executable file (slower startup, easier distribution)
"""

import sys
import shutil
import subprocess
import argparse
from pathlib import Path
import os


class BuildScript:
    """Automated build script for AGI Assistant."""

    def __init__(self, clean=False, onefile=False):
        """Initialize build script."""
        self.root_dir = Path(__file__).parent
        self.build_dir = self.root_dir / "build"
        self.dist_dir = self.root_dir / "dist"
        self.spec_file = self.root_dir / "agi_assistant.spec"
        self.clean = clean
        self.onefile = onefile

        # Output directories
        self.output_name = "AGI_Assistant"
        self.output_dir = self.dist_dir / self.output_name

    def print_header(self, message):
        """Print a formatted header."""
        print("\n" + "=" * 70)
        print(f"  {message}")
        print("=" * 70)

    def print_step(self, message):
        """Print a build step."""
        print(f"\n>>> {message}")

    def print_success(self, message):
        """Print a success message."""
        print(f"✓ {message}")

    def print_error(self, message):
        """Print an error message."""
        print(f"✗ ERROR: {message}", file=sys.stderr)

    def print_warning(self, message):
        """Print a warning message."""
        print(f"⚠ WARNING: {message}")

    def check_dependencies(self):
        """Check if required dependencies are installed."""
        self.print_step("Checking dependencies...")

        required_packages = [
            "PyInstaller",
            "wxPython",
            "wxasync",
            "pydantic",
            "aiosqlite",
            "mss",
            "opencv-python",
        ]

        missing_packages = []

        for package in required_packages:
            try:
                __import__(package.lower().replace("-", "_"))
                self.print_success(f"{package} is installed")
            except ImportError:
                missing_packages.append(package)
                self.print_error(f"{package} is NOT installed")

        if missing_packages:
            self.print_error("Missing required packages!")
            print("\nPlease install missing packages:")
            print(f"  pip install {' '.join(missing_packages)}")
            print("\nOr install all requirements:")
            print("  pip install -r requirements.txt")
            return False

        self.print_success("All dependencies are installed")
        return True

    def check_pyinstaller(self):
        """Check if PyInstaller is available."""
        self.print_step("Checking PyInstaller...")

        try:
            result = subprocess.run(
                ["pyinstaller", "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            version = result.stdout.strip()
            self.print_success(f"PyInstaller version: {version}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("PyInstaller not found or not working")
            print("\nPlease install PyInstaller:")
            print("  pip install pyinstaller")
            return False

    def clean_build(self):
        """Clean previous build artifacts."""
        self.print_step("Cleaning previous build artifacts...")

        dirs_to_clean = [self.build_dir, self.dist_dir]

        for dir_path in dirs_to_clean:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    self.print_success(f"Removed: {dir_path}")
                except Exception as e:
                    self.print_error(f"Failed to remove {dir_path}: {e}")
                    return False

        # Clean __pycache__ directories
        for pycache in self.root_dir.rglob("__pycache__"):
            try:
                shutil.rmtree(pycache)
            except Exception:
                pass

        self.print_success("Build artifacts cleaned")
        return True

    def check_spec_file(self):
        """Check if spec file exists."""
        self.print_step("Checking spec file...")

        if not self.spec_file.exists():
            self.print_error(f"Spec file not found: {self.spec_file}")
            print("\nPlease ensure agi_assistant.spec exists in the project root.")
            return False

        self.print_success(f"Found spec file: {self.spec_file}")
        return True

    def run_pyinstaller(self):
        """Run PyInstaller to build the executable."""
        self.print_step("Running PyInstaller...")

        cmd = ["pyinstaller", str(self.spec_file), "--noconfirm"]

        print(f"\nCommand: {' '.join(cmd)}")
        print("\nThis may take several minutes...\n")

        try:
            # Run PyInstaller with real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Print output in real-time
            for line in process.stdout:
                print(line, end="")

            process.wait()

            if process.returncode != 0:
                self.print_error(f"PyInstaller failed with code {process.returncode}")
                return False

            self.print_success("PyInstaller completed successfully")
            return True

        except Exception as e:
            self.print_error(f"Failed to run PyInstaller: {e}")
            return False

    def copy_resources(self):
        """Copy additional resources to the distribution folder."""
        self.print_step("Copying additional resources...")

        if not self.output_dir.exists():
            self.print_error(f"Output directory not found: {self.output_dir}")
            return False

        # Resources to copy
        resources = [
            ("README.md", "README.md"),
            ("USER_GUIDE.md", "USER_GUIDE.md"),
            ("SETUP_INSTRUCTIONS.md", "SETUP_INSTRUCTIONS.md"),
            ("DEMO_SCRIPT.md", "DEMO_SCRIPT.md"),
        ]

        for src_name, dst_name in resources:
            src_path = self.root_dir / src_name
            dst_path = self.output_dir / dst_name

            if src_path.exists():
                try:
                    shutil.copy2(src_path, dst_path)
                    self.print_success(f"Copied: {src_name}")
                except Exception as e:
                    self.print_warning(f"Failed to copy {src_name}: {e}")
            else:
                self.print_warning(f"Resource not found: {src_name}")

        # Create data directory structure
        data_dir = self.output_dir / "data"
        try:
            data_dir.mkdir(exist_ok=True)
            (data_dir / "logs").mkdir(exist_ok=True)
            (data_dir / "captures").mkdir(exist_ok=True)
            (data_dir / "database").mkdir(exist_ok=True)
            (data_dir / "models").mkdir(exist_ok=True)
            self.print_success("Created data directory structure")
        except Exception as e:
            self.print_warning(f"Failed to create data directories: {e}")

        # Create a .env.example file
        env_example = self.output_dir / ".env.example"
        try:
            with open(env_example, "w") as f:
                f.write("# AGI Assistant Configuration\n")
                f.write("# Copy this file to .env and customize as needed\n\n")
                f.write("# Data directory (relative or absolute path)\n")
                f.write("DATA_DIR=./data\n\n")
                f.write("# Log level (DEBUG, INFO, WARNING, ERROR)\n")
                f.write("LOG_LEVEL=INFO\n\n")
                f.write("# Storage limit in GB\n")
                f.write("STORAGE_LIMIT_GB=10\n\n")
                f.write("# Screenshot interval in seconds\n")
                f.write("SCREENSHOT_INTERVAL=3\n")
            self.print_success("Created .env.example")
        except Exception as e:
            self.print_warning(f"Failed to create .env.example: {e}")

        return True

    def create_batch_file(self):
        """Create a convenient batch file to run the application."""
        self.print_step("Creating launcher batch file...")

        batch_content = """@echo off
REM AGI Assistant Launcher

echo ====================================
echo AGI Assistant
echo AI-Powered Workflow Automation
echo ====================================
echo.

REM Check if executable exists
if not exist "AGI_Assistant.exe" (
    echo ERROR: AGI_Assistant.exe not found!
    echo Please ensure you're running this from the correct directory.
    pause
    exit /b 1
)

REM Launch the application
echo Starting AGI Assistant...
echo.
start "" "AGI_Assistant.exe"

REM Wait a moment and check if it's running
timeout /t 2 /nobreak >nul

tasklist /FI "IMAGENAME eq AGI_Assistant.exe" 2>NUL | find /I /N "AGI_Assistant.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Application started successfully!
) else (
    echo WARNING: Application may have failed to start.
    echo Check the logs in data/logs/ for details.
    pause
)
"""

        batch_file = self.output_dir / "Start_AGI_Assistant.bat"
        try:
            with open(batch_file, "w") as f:
                f.write(batch_content)
            self.print_success("Created Start_AGI_Assistant.bat")
        except Exception as e:
            self.print_warning(f"Failed to create batch file: {e}")

        return True

    def verify_build(self):
        """Verify that the build was successful."""
        self.print_step("Verifying build...")

        exe_path = self.output_dir / "AGI_Assistant.exe"

        if not exe_path.exists():
            self.print_error(f"Executable not found: {exe_path}")
            return False

        exe_size = exe_path.stat().st_size / (1024 * 1024)  # Size in MB
        self.print_success(f"Executable created: AGI_Assistant.exe ({exe_size:.2f} MB)")

        # Check for essential files
        essential_files = [
            "AGI_Assistant.exe",
            "README.md",
        ]

        missing_files = []
        for file_name in essential_files:
            file_path = self.output_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            self.print_warning(f"Missing files: {', '.join(missing_files)}")

        return True

    def create_distribution_info(self):
        """Create a distribution information file."""
        self.print_step("Creating distribution info...")

        info_file = self.output_dir / "DISTRIBUTION_INFO.txt"
        try:
            with open(info_file, "w") as f:
                f.write("AGI Assistant - Windows Distribution\n")
                f.write("=" * 50 + "\n\n")
                f.write("APPLICATION INFORMATION\n")
                f.write("-" * 50 + "\n")
                f.write("Name: AGI Assistant\n")
                f.write("Version: MVP Round 1\n")
                f.write("Platform: Windows 10/11 (64-bit)\n")
                f.write(
                    "Build Date: "
                    + subprocess.check_output(
                        ["date", "/t"], shell=True, text=True
                    ).strip()
                    + "\n\n"
                )
                f.write("SYSTEM REQUIREMENTS\n")
                f.write("-" * 50 + "\n")
                f.write("- Windows 10 or later (64-bit)\n")
                f.write("- 4 GB RAM minimum (8 GB recommended)\n")
                f.write("- 10 GB free disk space\n")
                f.write("- Screen resolution: 1280x720 or higher\n\n")
                f.write("INSTALLATION\n")
                f.write("-" * 50 + "\n")
                f.write("1. Extract all files to a folder\n")
                f.write("2. Run AGI_Assistant.exe or Start_AGI_Assistant.bat\n")
                f.write("3. Grant screen capture permissions when prompted\n")
                f.write("4. (Optional) Grant microphone permissions for audio\n\n")
                f.write("IMPORTANT NOTES\n")
                f.write("-" * 50 + "\n")
                f.write("- All processing is done locally (no internet required)\n")
                f.write("- First run may take longer to initialize\n")
                f.write("- Check USER_GUIDE.md for detailed instructions\n")
                f.write("- Logs are stored in data/logs/\n\n")
                f.write("SUPPORT\n")
                f.write("-" * 50 + "\n")
                f.write("For issues and questions, check:\n")
                f.write("- USER_GUIDE.md\n")
                f.write("- SETUP_INSTRUCTIONS.md\n")
                f.write("- Log files in data/logs/\n")

            self.print_success("Created DISTRIBUTION_INFO.txt")
        except Exception as e:
            self.print_warning(f"Failed to create distribution info: {e}")

        return True

    def build(self):
        """Execute the full build process."""
        self.print_header("AGI Assistant Build Script")

        print(f"\nRoot directory: {self.root_dir}")
        print(f"Build mode: {'One-file' if self.onefile else 'One-folder'}")
        print(f"Clean build: {'Yes' if self.clean else 'No'}")

        # Step 1: Check dependencies
        if not self.check_dependencies():
            return False

        # Step 2: Check PyInstaller
        if not self.check_pyinstaller():
            return False

        # Step 3: Clean previous builds (if requested)
        if self.clean:
            if not self.clean_build():
                return False

        # Step 4: Check spec file
        if not self.check_spec_file():
            return False

        # Step 5: Run PyInstaller
        if not self.run_pyinstaller():
            return False

        # Step 6: Copy additional resources
        if not self.copy_resources():
            self.print_warning("Some resources were not copied")

        # Step 7: Create batch file
        self.create_batch_file()

        # Step 8: Create distribution info
        self.create_distribution_info()

        # Step 9: Verify build
        if not self.verify_build():
            return False

        # Success!
        self.print_header("Build Completed Successfully!")

        print(f"\nOutput directory: {self.output_dir}")
        print(f"Executable: {self.output_dir / 'AGI_Assistant.exe'}")
        print("\nNext steps:")
        print("1. Test the executable on this machine")
        print("2. Test on a clean Windows system (if possible)")
        print("3. Create installer with Inno Setup or NSIS (optional)")
        print("4. Distribute the entire folder or create a ZIP archive")
        print("\nTo create a ZIP for distribution:")
        print(f"  - Right-click on: {self.output_dir}")
        print("  - Select: Send to > Compressed (zipped) folder")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build AGI Assistant Windows executable"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean previous build artifacts before building",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create a single executable file (not yet implemented)",
    )

    args = parser.parse_args()

    if args.onefile:
        print("⚠ One-file build is not yet configured in the spec file.")
        print("Using one-folder build instead.\n")

    # Create and run build script
    builder = BuildScript(clean=args.clean, onefile=args.onefile)

    try:
        success = builder.build()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
