# Contributing to EV Tracker Home Assistant Integration

Thank you for your interest in contributing!

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/evtracker/homeassistant-evtracker.git
   cd homeassistant-evtracker
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements_test.txt
   pip install pre-commit ruff
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=custom_components/evtracker --cov-report=html

# Run specific test file
pytest tests/test_api.py -v
```

## Code Quality

We use Ruff for linting and formatting:

```bash
# Check for issues
ruff check custom_components/evtracker tests

# Auto-fix issues
ruff check --fix custom_components/evtracker tests

# Format code
ruff format custom_components/evtracker tests
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting
5. Commit your changes using conventional commits:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation changes
   - `test:` for test changes
   - `chore:` for maintenance tasks
6. Push to your fork and create a Pull Request

## Releasing

Releases are automated via GitHub Actions. To create a new release:

1. Update the version in `custom_components/evtracker/manifest.json`
2. Update the version in `custom_components/evtracker/const.py`
3. Create and push a tag:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```
4. The release workflow will automatically create a GitHub release

## Testing with Home Assistant

To test the integration locally with Home Assistant:

1. Copy the `custom_components/evtracker` folder to your Home Assistant's `config/custom_components/` directory
2. Restart Home Assistant
3. Add the integration via Settings > Devices & Services > Add Integration > EV Tracker
