# Publishing yt-dl-manager to PyPI

## Prerequisites

1. Install twine for uploading packages:
```bash
pip install twine
```

2. Create accounts on:
   - [TestPyPI](https://test.pypi.org/account/register/) (for testing)
   - [PyPI](https://pypi.org/account/register/) (for production)

## Publishing Process

### 1. Test on TestPyPI First

1. Build the package:
```bash
python -m build
```

2. Upload to TestPyPI:
```bash
python -m twine upload --repository testpypi dist/*
```

3. Test installation from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ yt-dl-manager
```

### 2. Publish to PyPI

1. Clean and rebuild:
```bash
rm -rf dist/ build/ *.egg-info/
python -m build
```

2. Upload to PyPI:
```bash
python -m twine upload dist/*
```

3. Verify installation:
```bash
pip install yt-dl-manager
```

## Version Management

Update version in:
- `pyproject.toml` - project version
- `yt_dl_manager/__init__.py` - __version__ variable

## Security

- Use API tokens instead of passwords
- Store credentials in `~/.pypirc` or use keyring
- Never commit credentials to version control

## Notes

- TestPyPI is isolated from PyPI - packages need to be uploaded to both
- Version numbers must be unique and cannot be reused
- Follow [semantic versioning](https://semver.org/) (MAJOR.MINOR.PATCH)
