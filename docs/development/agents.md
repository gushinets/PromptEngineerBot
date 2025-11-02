# Telegram Prompt Engineering Bot
A professional Telegram bot that helps users optimize their prompts using different AI-powered methodologies (CRAFT, LYRA, GGL). Built with a clean, modular architecture and comprehensive testing.

## CODING GUIDELINES
- Update the documentation where necessary
- Always follow the PEP8 style guide
- Always write docstrings
- Follow all the ruff conventions
- Type hints are strongly encouraged
- Always use the `self` variable to access class attributes
- After each update, run the tests, linting and typechecking to make sure everything is passing
- After introducing new functionality, add a test for it
- After changing existing functionality, add a test for it or change appropriate tests
- After refactoring, run the tests to make sure everything is passing
- After introducing new package dependency, add it to the requirements.txt file
- After adding new files to the project, change Dockerfile and docker-compose.yml to include the new files
- Implementing new features add logging for important events
- For strings use single quotes instead of douvle quotes
- DO NOT use "magic numbers". Move any number to a meaningfull variable and place it appropriately
- DO NOT use deprecated methods
- Update Readme.md where relevant

## SECURITY GUIDELINES
- Do not expose any sensitive information in the code
- Never push sensitive information to the repository
- Only use packages without Critical and Severe vulnerabilities
- Never log sensitive data - OTPs, passwords, full emails, credentials
- Always mask identifiers - Emails and telegram IDs in logs
- Secure credential storage - Environment variables, secrets management
- Audit trail safety - Log events without exposing sensitive details
