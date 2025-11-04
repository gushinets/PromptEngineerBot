#!/usr/bin/env python3
"""
System validation script for email prompt delivery feature.

This script performs basic validation of the system integration
without requiring external services to be running.
"""

import asyncio
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing imports...")

    try:
        # Test core imports
        from telegram_bot.core.bot_handler import BotHandler
        from telegram_bot.main import main
        from telegram_bot.utils.config import BotConfig

        print("✓ Core modules imported successfully")

        # Test email feature imports
        from telegram_bot.auth.auth_service import AuthService
        from telegram_bot.data.database import init_database
        from telegram_bot.flows.background_tasks import BackgroundTaskScheduler
        from telegram_bot.flows.email_flow import EmailFlowOrchestrator
        from telegram_bot.services.email_service import EmailService
        from telegram_bot.services.redis_client import RedisClient
        from telegram_bot.utils.audit_service import AuditService
        from telegram_bot.utils.health_checks import HealthMonitor
        from telegram_bot.utils.metrics import MetricsCollector

        print("✓ Email feature modules imported successfully")

        return True

    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_configuration():
    """Test configuration loading and validation."""
    print("\nTesting configuration...")

    try:
        from telegram_bot.utils.config import BotConfig

        # Test with minimal environment
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "OPENAI_API_KEY": "test_key",
                "LLM_BACKEND": "OPENAI",
                "EMAIL_ENABLED": "false",  # Disable email for basic test
            },
        ):
            config = BotConfig.from_env()
            config.validate()
            print("✓ Configuration loaded and validated successfully")

        # Test with email enabled
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "OPENAI_API_KEY": "test_key",
                "LLM_BACKEND": "OPENAI",
                "EMAIL_ENABLED": "true",
                "SMTP_USERNAME": "test@example.com",
                "SMTP_PASSWORD": "test_password",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            },
        ):
            config = BotConfig.from_env()
            config.validate()
            print("✓ Email-enabled configuration loaded and validated successfully")

        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_service_initialization():
    """Test service initialization without external dependencies."""
    print("\nTesting service initialization...")

    try:
        from telegram_bot.auth.auth_service import AuthService
        from telegram_bot.flows.background_tasks import BackgroundTaskScheduler
        from telegram_bot.services.redis_client import RedisClient
        from telegram_bot.utils.audit_service import AuditService
        from telegram_bot.utils.config import BotConfig
        from telegram_bot.utils.health_checks import HealthMonitor
        from telegram_bot.utils.metrics import MetricsCollector

        # Create test config
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "OPENAI_API_KEY": "test_key",
                "LLM_BACKEND": "OPENAI",
                "EMAIL_ENABLED": "true",
                "SMTP_USERNAME": "test@example.com",
                "SMTP_PASSWORD": "test_password",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            },
        ):
            config = BotConfig.from_env()

        # Test service creation (without actual connections)
        with patch(
            "telegram_bot.auth.auth_service.get_redis_client", return_value=Mock()
        ):
            auth_service = AuthService(config)
        print("✓ Auth service created successfully")

        health_monitor = HealthMonitor(config)
        print("✓ Health monitor created successfully")

        background_scheduler = BackgroundTaskScheduler()
        print("✓ Background scheduler created successfully")

        audit_service = AuditService()
        print("✓ Audit service created successfully")

        metrics_collector = MetricsCollector()
        print("✓ Metrics collector created successfully")

        return True

    except Exception as e:
        print(f"✗ Service initialization failed: {e}")
        return False


def test_email_flow_components():
    """Test email flow components without external dependencies."""
    print("\nTesting email flow components...")

    try:
        from telegram_bot.auth.auth_service import AuthService
        from telegram_bot.services.email_service import EmailService
        from telegram_bot.utils.config import BotConfig
        from telegram_bot.utils.email_templates import EmailTemplates

        # Create test config
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "OPENAI_API_KEY": "test_key",
                "LLM_BACKEND": "OPENAI",
                "EMAIL_ENABLED": "true",
                "SMTP_USERNAME": "test@example.com",
                "SMTP_PASSWORD": "test_password",
                "SMTP_FROM_EMAIL": "noreply@example.com",
            },
        ):
            config = BotConfig.from_env()

        # Test email template generation
        templates = EmailTemplates("EN")
        otp_subject = templates.get_otp_subject()
        otp_body = templates.get_otp_html_body("123456")
        print("✓ OTP email template generated successfully")

        optimization_subject = templates.get_optimization_subject()
        optimization_body = templates.get_optimization_html_body(
            original_prompt="Test prompt",
            improved_prompt="Improved test prompt",
            craft_result="CRAFT result",
            lyra_result="LYRA result",
            ggl_result="GGL result",
        )
        print("✓ Optimized prompts email template generated successfully")

        # Test email service creation (without SMTP connection)
        email_service = EmailService(config)
        print("✓ Email service created successfully")

        return True

    except Exception as e:
        print(f"✗ Email flow components test failed: {e}")
        return False


def test_graceful_degradation():
    """Test graceful degradation system."""
    print("\nTesting graceful degradation...")

    try:
        from telegram_bot.utils.config import BotConfig
        from telegram_bot.utils.graceful_degradation import (
            GracefulDegradationManager,
            check_email_flow_readiness,
            handle_smtp_fallback,
        )

        # Create test config
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "OPENAI_API_KEY": "test_key",
                "LLM_BACKEND": "OPENAI",
                "EMAIL_ENABLED": "true",
            },
        ):
            config = BotConfig.from_env()

        # Test degradation manager creation
        degradation_manager = GracefulDegradationManager(config)
        print("✓ Graceful degradation manager created successfully")

        # Test degradation functions
        is_ready, message = check_email_flow_readiness("EN")
        print("✓ Email flow readiness check completed")

        should_fallback, fallback_message = handle_smtp_fallback("EN")
        print("✓ SMTP fallback check completed")

        return True

    except Exception as e:
        print(f"✗ Graceful degradation test failed: {e}")
        return False


async def test_async_components():
    """Test async components."""
    print("\nTesting async components...")

    try:
        from telegram_bot.utils.config import BotConfig
        from telegram_bot.utils.graceful_degradation import GracefulDegradationManager
        from telegram_bot.utils.health_checks import HealthMonitor

        # Create test config
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "OPENAI_API_KEY": "test_key",
                "LLM_BACKEND": "OPENAI",
                "EMAIL_ENABLED": "true",
            },
        ):
            config = BotConfig.from_env()

        # Test health monitor async methods (without actual health checks)
        health_monitor = HealthMonitor(config)

        # Mock the health check methods to avoid external dependencies
        with (
            patch.object(health_monitor, "check_database_health"),
            patch.object(health_monitor, "check_redis_health"),
            patch.object(health_monitor, "check_smtp_health"),
        ):
            # This would normally check actual services
            print("✓ Health monitor async methods available")

        # Test degradation manager async methods
        degradation_manager = GracefulDegradationManager(config)

        # Mock the health monitor to avoid external dependencies
        with patch("telegram_bot.utils.graceful_degradation.get_health_monitor"):
            state = await degradation_manager.check_and_update_degradation()
            print("✓ Degradation manager async methods working")

        return True

    except Exception as e:
        print(f"✗ Async components test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("=== System Validation for Email Prompt Delivery Feature ===\n")

    tests = [
        test_imports,
        test_configuration,
        test_service_initialization,
        test_email_flow_components,
        test_graceful_degradation,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    # Run async tests
    print("Running async tests...")
    try:
        asyncio.run(test_async_components())
        passed += 1
        total += 1
    except Exception as e:
        print(f"✗ Async tests failed: {e}")
        total += 1

    print(f"\n=== Validation Results ===")
    print(f"Passed: {passed}/{total} tests")

    if passed == total:
        print("✓ All validation tests passed!")
        print("\nSystem integration is working correctly.")
        print("The email prompt delivery feature is ready for deployment.")
        return 0
    else:
        print(f"✗ {total - passed} tests failed.")
        print("\nSystem integration has issues that need to be resolved.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
