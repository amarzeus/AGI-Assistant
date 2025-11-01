# Contributing to AGI Assistant

Thank you for your interest in contributing to AGI Assistant! This document provides guidelines and information for contributors.

## 🎯 Project Overview

AGI Assistant is a privacy-first desktop application that observes user workflows, detects patterns, and suggests automations. Everything runs locally with no cloud dependencies.

**Current Status:**
- ✅ Round 1 (Observe & Understand): 100% Complete
- 🚧 Round 2 (Act & Automate): 30% Complete
- 🎯 Production Ready with working automation

## 🤝 How to Contribute

### 1. Types of Contributions

We welcome:
- 🐛 **Bug Reports** - Help us identify and fix issues
- 💡 **Feature Requests** - Suggest new functionality
- 📝 **Documentation** - Improve guides and references
- 🧪 **Testing** - Add test cases and improve coverage
- 🎨 **UI/UX** - Enhance the user interface
- 🔧 **Code** - Fix bugs and implement features

### 2. Getting Started

**Prerequisites:**
- Python 3.10+
- Windows 10/11 (primary platform)
- Git for version control

**Setup Development Environment:**
```bash
# Clone the repository
git clone https://github.com/yourusername/agi-assistant.git
cd agi-assistant

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov black flake8 mypy

# Verify setup
python -c "from src.config import get_config; print('✓ Setup complete')"
```

### 3. Development Workflow

**Before Making Changes:**
1. Create an issue to discuss the change
2. Fork the repository
3. Create a feature branch: `git checkout -b feature/your-feature`

**While Developing:**
1. Follow the coding standards (see below)
2. Write tests for new functionality
3. Update documentation as needed
4. Test your changes thoroughly

**Before Submitting:**
1. Run the test suite: `pytest`
2. Check code formatting: `black src/ tests/`
3. Run linting: `flake8 src/ tests/`
4. Check type hints: `mypy src/`
5. Update CHANGELOG.md if applicable

**Submitting Changes:**
1. Push to your fork: `git push origin feature/your-feature`
2. Create a Pull Request with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots for UI changes
   - Test results

## 📋 Coding Standards

### Python Code Style

We follow PEP 8 with some modifications:

```python
# Use type hints
def process_action(action: Action) -> Optional[Pattern]:
    """Process an action and return detected pattern."""
    pass

# Use descriptive variable names
screenshot_timestamp = datetime.now()
confidence_threshold = 0.85

# Use docstrings for classes and functions
class PatternDetector:
    """
    Detects repetitive patterns in user actions.
    
    This class analyzes sequences of user actions to identify
    workflows that could be automated.
    """
    
    def detect_patterns(self, actions: List[Action]) -> List[Pattern]:
        """
        Detect patterns in a list of actions.
        
        Args:
            actions: List of user actions to analyze
            
        Returns:
            List of detected patterns with confidence scores
        """
        pass
```

### UI Development Standards

```python
# Use the theme system for consistent styling
from src.ui.theme import get_theme

theme = get_theme()
button.setStyleSheet(theme.get_button_style())

# Follow accessibility guidelines
button.setAccessibleName("Start Recording")
button.setToolTip("Begin capturing screen and audio")

# Use proper signal/slot connections
self.start_button.clicked.connect(self.on_start_recording)
```

### Database Standards

```python
# Use async database operations
async def save_action(self, action: Action) -> None:
    """Save action to database."""
    async with aiosqlite.connect(self.db_path) as db:
        await db.execute(
            "INSERT INTO actions (timestamp, type, data) VALUES (?, ?, ?)",
            (action.timestamp, action.type, action.data)
        )
        await db.commit()
```

## 🧪 Testing Guidelines

### Test Structure

```python
import pytest
from src.models.action import Action
from src.services.pattern_detector import PatternDetector

class TestPatternDetector:
    """Test pattern detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create pattern detector instance."""
        return PatternDetector()
    
    @pytest.fixture
    def sample_actions(self):
        """Create sample actions for testing."""
        return [
            Action(type="click", data={"x": 100, "y": 200}),
            Action(type="type", data={"text": "hello"}),
        ]
    
    def test_detect_simple_pattern(self, detector, sample_actions):
        """Test detection of simple repetitive pattern."""
        # Repeat actions to create pattern
        repeated_actions = sample_actions * 3
        
        patterns = detector.detect_patterns(repeated_actions)
        
        assert len(patterns) > 0
        assert patterns[0].confidence > 0.8
```

### Test Categories

1. **Unit Tests** - Test individual functions and classes
2. **Integration Tests** - Test service interactions
3. **UI Tests** - Test user interface components
4. **End-to-End Tests** - Test complete workflows

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_pattern_detector.py

# Run tests with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_pattern"
```

## 📚 Documentation Standards

### Code Documentation

- Use docstrings for all public functions and classes
- Include type hints for all function parameters and returns
- Add inline comments for complex logic
- Update README.md for significant changes

### User Documentation

- Keep language clear and non-technical where possible
- Include screenshots for UI changes
- Provide step-by-step instructions
- Test instructions with fresh users

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment Information:**
   - Operating System and version
   - Python version
   - AGI Assistant version
   - Relevant hardware specs

2. **Steps to Reproduce:**
   - Detailed steps to trigger the bug
   - Expected behavior
   - Actual behavior

3. **Additional Information:**
   - Screenshots or videos
   - Log files (from `~/agi-assistant-data/logs/`)
   - Error messages
   - Configuration files (remove sensitive data)

**Example Bug Report:**
```markdown
## Bug: Screen capture fails on high-DPI displays

**Environment:**
- Windows 11 Pro 22H2
- Python 3.11.5
- AGI Assistant v1.0.0
- 4K monitor (3840x2160, 150% scaling)

**Steps to Reproduce:**
1. Launch AGI Assistant
2. Click "Start Recording"
3. Observe error in logs

**Expected:** Screen capture should work normally
**Actual:** Error: "Screenshot dimensions invalid"

**Logs:**
```
ERROR: Screenshot capture failed: Invalid dimensions (5760, 3240)
```

**Additional Info:**
- Works fine on 1080p monitor
- Issue appears related to Windows display scaling
```

## 💡 Feature Requests

When requesting features, please include:

1. **Use Case:** Describe the problem you're trying to solve
2. **Proposed Solution:** How you envision the feature working
3. **Alternatives:** Other ways to solve the problem
4. **Priority:** How important is this feature to you?

## 🎨 UI/UX Contributions

For UI/UX improvements:

1. **Follow Design System:** Use the existing theme and components
2. **Accessibility First:** Ensure WCAG AA compliance
3. **Test on Different Sizes:** Verify responsive behavior
4. **Include Screenshots:** Show before/after comparisons
5. **Consider Dark Mode:** Ensure changes work in both themes

## 🔧 Architecture Guidelines

### Service Layer

```python
class BaseService:
    """Base class for all services."""
    
    async def start(self) -> None:
        """Start the service."""
        pass
    
    async def stop(self) -> None:
        """Stop the service."""
        pass
    
    def get_status(self) -> ServiceStatus:
        """Get current service status."""
        pass
```

### Event System

```python
# Publishing events
event_bus = get_event_bus()
await event_bus.publish(
    Event(
        type=EventType.ACTION_DETECTED,
        data={"action": action, "confidence": 0.95}
    )
)

# Subscribing to events
@event_bus.subscribe(EventType.ACTION_DETECTED)
async def handle_action(event: Event) -> None:
    """Handle detected action."""
    action = event.data["action"]
    # Process action...
```

### Database Layer

```python
# Use the storage manager for all database operations
storage_manager = StorageManager()
await storage_manager.save_action(action)
patterns = await storage_manager.get_patterns(session_id)
```

## 📋 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] Tests are written and passing
- [ ] Documentation is updated
- [ ] Type hints are included
- [ ] Accessibility is maintained
- [ ] Performance impact is considered
- [ ] Security implications are reviewed
- [ ] Backwards compatibility is maintained

## 🏆 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributors page
- Special thanks in documentation

## 📞 Getting Help

- **GitHub Issues:** For bugs and feature requests
- **GitHub Discussions:** For questions and general discussion
- **Documentation:** Check existing guides first
- **Code Review:** Maintainers will provide feedback on PRs

## 📄 License

By contributing to AGI Assistant, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to AGI Assistant! Together, we're building the future of personal automation. 🚀