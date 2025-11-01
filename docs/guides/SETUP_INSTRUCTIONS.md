# Setup Instructions for AGI Assistant

## Prerequisites Installation

### 1. Install Python 3.10 or higher

**Option A: Download from Python.org**
1. Go to https://www.python.org/downloads/
2. Download Python 3.10 or later (3.11 recommended)
3. Run the installer
4. ⚠️ **IMPORTANT**: Check "Add Python to PATH" during installation
5. Verify installation:
   ```cmd
   python --version
   ```

**Option B: Using Windows Store**
1. Open Microsoft Store
2. Search for "Python 3.11"
3. Click "Get" to install
4. Verify installation:
   ```cmd
   python --version
   ```

### 2. Install Tesseract OCR

1. Download Tesseract installer from:
   https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (tesseract-ocr-w64-setup-v5.x.x.exe)
3. Note the installation path (default: `C:\Program Files\Tesseract-OCR`)
4. Add to PATH:
   - Open "Environment Variables" in Windows
   - Add `C:\Program Files\Tesseract-OCR` to PATH
5. Verify installation:
   ```cmd
   tesseract --version
   ```

### 3. Install Ollama (for Local LLM)

1. Download Ollama from: https://ollama.ai/download
2. Run the installer
3. Open Command Prompt and pull the Phi-3 model:
   ```cmd
   ollama pull phi3:mini
   ```
4. Verify installation:
   ```cmd
   ollama list
   ```

### 4. Install PyAudio (for Audio Capture)

PyAudio requires additional setup on Windows:

**Option A: Using pip with pre-built wheel**
```cmd
pip install pipwin
pipwin install pyaudio
```

**Option B: Download pre-built wheel**
1. Go to: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
2. Download the appropriate `.whl` file for your Python version
3. Install:
   ```cmd
   pip install PyAudio-0.2.13-cp311-cp311-win_amd64.whl
   ```

## Project Setup

### 1. Create Virtual Environment

```cmd
cd path\to\agi-assistant-mvp
python -m venv venv
```

### 2. Activate Virtual Environment

```cmd
venv\Scripts\activate
```

You should see `(venv)` in your command prompt.

### 3. Upgrade pip

```cmd
python -m pip install --upgrade pip
```

### 4. Install Dependencies

```cmd
pip install -r requirements.txt
```

**Note**: If you encounter errors with specific packages:
- For PyAudio: Follow the PyAudio installation steps above
- For other packages: Try installing them individually

### 5. Verify Installation

```cmd
python -m src.main
```

You should see:
```
AGI Assistant - Development Mode
Data directory: C:\Users\YourName\agi-assistant-data
Log level: INFO

Press Ctrl+C to exit...
```

## Troubleshooting

### Python not found
- Ensure Python is added to PATH
- Restart your terminal/command prompt
- Try using `py` instead of `python`

### PyAudio installation fails
- Use the pipwin method or download pre-built wheel
- Ensure you have Visual C++ Build Tools if building from source

### Tesseract not found
- Verify Tesseract is in PATH
- Set environment variable: `TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata`

### Ollama connection error
- Ensure Ollama service is running
- Check if model is downloaded: `ollama list`
- Try pulling model again: `ollama pull phi3:mini`

### Permission errors
- Run Command Prompt as Administrator
- Check antivirus isn't blocking the application

## Next Steps

Once setup is complete:

1. **Configure the application**:
   - Edit `~/.agi-assistant/config.json` for custom settings
   - Add excluded applications for privacy

2. **Run tests**:
   ```cmd
   pytest
   ```

3. **Start development**:
   - Follow the tasks in `.kiro/specs/agi-assistant-mvp/tasks.md`
   - Implement services one by one

4. **Build executable** (when ready):
   ```cmd
   pyinstaller --name="AI-Dashcam" --windowed --onefile src/main.py
   ```

## System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 15GB free space
- **CPU**: Intel i5 or equivalent (i7 recommended for automation)
- **Python**: 3.10 or higher
- **Display**: 1920x1080 minimum (4K supported)
- **Network**: Internet for initial setup only (runs offline)

## Getting Help

If you encounter issues:
1. Check the error logs in `~/agi-assistant-data/logs/`
2. Review the requirements.md and design.md in `.kiro/specs/agi-assistant-mvp/`
3. Ensure all prerequisites are properly installed

## Development Workflow

1. Activate virtual environment: `venv\Scripts\activate`
2. Make changes to code
3. Run tests: `pytest`
4. Test manually: `python -m src.main`
5. Commit changes

Happy coding! 🚀
