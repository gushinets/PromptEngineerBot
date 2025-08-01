# Testing the Telegram Prompt Engineering Bot

This directory contains the test suite for the Telegram Prompt Engineering Bot. The tests are written using `pytest` with `pytest-asyncio` for handling asynchronous code.

## Test Structure

- `test_bot.py`: Tests for the main bot functionality, including command handlers and message processing.
- `test_llm_clients.py`: Tests for the LLM client implementations (OpenAI and OpenRouter).
- `conftest.py`: Pytest configuration and fixtures used across test files.

## Running Tests

1. First, install the test dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run all tests:
   ```bash
   pytest -v
   ```

3. Run tests with coverage report:
   ```bash
   pytest --cov=./ --cov-report=term-missing
   ```

4. Run a specific test file:
   ```bash
   pytest tests/test_bot.py -v
   ```

5. Run a specific test case:
   ```bash
   pytest tests/test_bot.py::TestBotFunctionality::test_start_command -v
   ```

## Test Types

### Unit Tests
- Test individual functions and methods in isolation.
- Mock external dependencies.
- Fast execution.

### Integration Tests
- Test interactions between components.
- May include real network calls in some cases.
- Slower but more realistic.

### Manual Tests
For manual testing of the bot, you can use the following approaches:

1. **Network Simulation**:
   - Use tools like `clumsy` (Windows) or `Network Link Conditioner` (macOS) to simulate poor network conditions.
   - Test with high latency (500-1000ms), packet loss (1-5%), and limited bandwidth (1-5Mbps).

2. **Long-Running Tests**:
   - Send prompts that typically take a long time to process.
   - Monitor memory usage and response times.

## Test Coverage

The test suite aims to cover:

- Command handling (`/start`, method selection)
- Message processing
- Error handling and retries
- LLM client interactions
- Timeout handling
- Network resilience

## Writing New Tests

When adding new features, please add corresponding tests. Follow these guidelines:

1. Use descriptive test names that explain what's being tested.
2. Keep tests focused on a single piece of functionality.
3. Use fixtures for common test setup.
4. Mock external services to keep tests fast and reliable.
5. Add appropriate assertions to verify the expected behavior.

## Debugging Tests

To debug a failing test:

1. Run the specific test with `-s` to see print statements:
   ```bash
   pytest tests/test_bot.py::TestName::test_name -v -s
   ```

2. Use `pdb` for interactive debugging:
   ```python
   import pdb; pdb.set_trace()  # Add this line where you want to break
   ```

3. Check the test logs in `pytest.log` for detailed error information.
