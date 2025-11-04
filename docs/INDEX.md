# Documentation Index

Welcome to the Telegram Prompt Engineer Bot documentation. This index provides quick access to all documentation organized by category.

## Architecture

- [User Profile System](architecture/USER_PROFILE_SYSTEM.md) - Comprehensive documentation of the user profile and authentication system

## Deployment

- [Deployment Guide](deployment/DEPLOYMENT.md) - Instructions for deploying the bot to production

## User Guides

- [End-to-End User Paths](guides/E2E_USER_PATHS_DOCUMENTATION.md) - Complete user journey documentation and testing paths

## Guidelines

- [Agent Guidelines](guidelines/AGENTS.md) - Guidelines for AI agents working with this codebase

## Development Notes

Historical development notes and fix summaries:

- [Async/Sync Fix Summary](development/ASYNC_SYNC_FIX_SUMMARY.md)
- [Final Code Cleanup Summary](development/FINAL_CODE_CLEANUP_SUMMARY.md)
- [Final Integration Validation Report](development/FINAL_INTEGRATION_VALIDATION_REPORT.md)
- [Final Validation Report](development/FINAL_VALIDATION_REPORT.md)
- [Fix Summary](development/FIX_SUMMARY.md)
- [Follow-up Decline Fix Summary](development/FOLLOWUP_DECLINE_FIX_SUMMARY.md)
- [Post Optimization Email Fix Summary](development/POST_OPTIMIZATION_EMAIL_FIX_SUMMARY.md)
- [Validate Post Optimization Fix](development/VALIDATE_POST_OPTIMIZATION_FIX.md)

## Feature Specifications

Feature specifications are maintained in the `.kiro/specs/` directory:

- [Code Cleanup](../.kiro/specs/code-cleanup/) - Code cleanup and refactoring tasks
  - [Tasks](../.kiro/specs/code-cleanup/tasks.md)

- [Email Prompt Delivery](../.kiro/specs/email-prompt-delivery/) - Email delivery of optimized prompts
  - [Requirements](../.kiro/specs/email-prompt-delivery/requirements.md)
  - [Design](../.kiro/specs/email-prompt-delivery/design.md)
  - [Tasks](../.kiro/specs/email-prompt-delivery/tasks.md)

- [Follow-up Questions](../.kiro/specs/follow-up-questions/) - Interactive follow-up question system
  - [Requirements](../.kiro/specs/follow-up-questions/requirements.md)
  - [Design](../.kiro/specs/follow-up-questions/design.md)
  - [Tasks](../.kiro/specs/follow-up-questions/tasks.md)

- [Message Internationalization](../.kiro/specs/message-internationalization/) - Multi-language support
  - [Requirements](../.kiro/specs/message-internationalization/requirements.md)
  - [Design](../.kiro/specs/message-internationalization/design.md)
  - [Tasks](../.kiro/specs/message-internationalization/tasks.md)

- [Project Restructuring](../.kiro/specs/project-restructuring/) - Project structure reorganization
  - [Requirements](../.kiro/specs/project-restructuring/requirements.md)
  - [Design](../.kiro/specs/project-restructuring/design.md)
  - [Tasks](../.kiro/specs/project-restructuring/tasks.md)

- [User Profile Extension](../.kiro/specs/user-profile-extension/) - Enhanced user profile system
  - [Requirements](../.kiro/specs/user-profile-extension/requirements.md)
  - [Design](../.kiro/specs/user-profile-extension/design.md)
  - [Tasks](../.kiro/specs/user-profile-extension/tasks.md)

## Project Structure

The project follows a modular package structure:

```
telegram_bot/
├── core/              # Core business logic (bot handler, conversation manager, state)
├── services/          # External services (LLM, email, Redis, Google Sheets)
│   └── llm/          # LLM client implementations
├── auth/              # Authentication and user profile management
├── data/              # Data layer (database models and operations)
├── utils/             # Utility modules (config, messages, logging, metrics)
├── flows/             # Complex workflows (email flow, background tasks)
├── prompts/           # Prompt templates
├── main.py            # Application entry point
└── dependencies.py    # Dependency injection container
```

## Migration Guide

- [Migration Guide](MIGRATION_GUIDE.md) - Guide for migrating to the new project structure

## Quick Links

- [README](../README.md) - Project overview and setup instructions
- [Tests](../tests/) - Test suite organization
  - [Unit Tests](../tests/unit/)
  - [Integration Tests](../tests/integration/)
  - [E2E Tests](../tests/e2e/)
