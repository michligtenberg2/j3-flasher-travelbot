# Contributing to J3 Flasher Travelbot

Thank you for your interest in contributing to the J3 Flasher Travelbot project! This document provides guidelines for contributing to the project.

## How to Contribute

### Reporting Bugs

1. **Search existing issues** first to avoid duplicates
2. **Create a detailed bug report** including:
   - Your operating system and version
   - Python version
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Any error messages or logs

### Suggesting Features

1. **Check existing feature requests** to avoid duplicates
2. **Open an issue** with the "enhancement" label
3. **Describe the feature** in detail:
   - What problem does it solve?
   - How should it work?
   - Any implementation ideas?

### Code Contributions

#### Setting Up Development Environment

1. **Clone the repository**:
   ```bash
   git clone https://github.com/michligtenberg2/j3-flasher-travelbot.git
   cd j3-flasher-travelbot
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

#### Making Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the coding standards:
   - Follow PEP 8 style guidelines
   - Add docstrings to new functions
   - Use type hints where appropriate
   - Keep functions focused and small

3. **Test your changes**:
   - Ensure the application still runs correctly
   - Test both GUI and command-line functionality
   - Check for any new warnings or errors

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add descriptive commit message"
   ```

#### Pull Request Process

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** with:
   - Clear title and description
   - Reference any related issues
   - Screenshots for UI changes
   - List of changes made

3. **Respond to feedback** and make necessary adjustments

## Coding Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Add docstrings to public functions and classes
- Prefer explicit imports over wildcard imports
- Use type hints for function parameters and return values

### Documentation

- Update README.md for significant feature changes
- Add comments for complex logic
- Keep docstrings up to date
- Update help text and user instructions as needed

### Error Handling

- Use specific exception types rather than bare `except:`
- Provide meaningful error messages to users
- Log errors appropriately for debugging
- Handle edge cases gracefully

## Testing

- Test the application on different operating systems when possible
- Verify functionality with different device states
- Check that new features work as expected
- Ensure existing functionality is not broken

## Security Considerations

- Never commit sensitive information (API keys, passwords, etc.)
- Validate user inputs appropriately
- Follow secure coding practices
- Report security vulnerabilities privately

## Getting Help

- **Documentation**: Check the `docs/` directory for additional help
- **Issues**: Browse existing issues for similar problems
- **Discussions**: Use GitHub discussions for questions

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment
- Follow GitHub's community guidelines

Thank you for contributing to make this project better!