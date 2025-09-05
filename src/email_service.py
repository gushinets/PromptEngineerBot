"""
Email service with SMTP integration for the Telegram bot.

This module provides email sending functionality with SMTP-Pulse integration,
connection pooling, retry logic, and comprehensive error handling.
"""

import asyncio
import hashlib
import logging
import smtplib
import ssl
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, AsyncGenerator, Dict, Optional, Set

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .audit_service import get_audit_service
from .config import BotConfig
from .email_templates import EmailTemplates, _

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message data structure."""

    to_email: str
    subject: str
    html_body: str
    plain_body: Optional[str] = None


@dataclass
class EmailDeliveryResult:
    """Result of email delivery attempt."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    delivery_time_ms: Optional[int] = None


class SMTPConnectionError(Exception):
    """SMTP connection related errors."""

    pass


class EmailDeliveryError(Exception):
    """Email delivery related errors."""

    pass


class EmailService:
    """
    Email service with SMTP integration and connection management.

    Features:
    - SMTP-Pulse integration with TLS/SSL support
    - Connection pooling and retry logic
    - Comprehensive error handling
    - Delivery confirmation and metrics
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self.templates = EmailTemplates(config.language)
        self._connection_pool: Dict[str, Any] = {}
        self._pool_lock = asyncio.Lock()
        self._connection_timeout = 30.0  # seconds

        # Idempotency tracking (in-memory for webhook replay protection)
        self._sent_emails: Set[str] = set()
        self._idempotency_lock = asyncio.Lock()

        # Email retry queue for SMTP health issues
        self._email_queue: asyncio.Queue = asyncio.Queue()
        self._queue_worker_task: Optional[asyncio.Task] = None
        self._queue_worker_running = False
        self._smtp_healthy = True
        self._health_check_lock = asyncio.Lock()

        # Validate SMTP configuration
        self._validate_smtp_config()

    def _validate_smtp_config(self) -> None:
        """Validate SMTP configuration settings."""
        if not self.config.smtp_host:
            raise ValueError("SMTP_HOST is required")

        if not self.config.smtp_username:
            raise ValueError("SMTP_USERNAME is required")

        if not self.config.smtp_password:
            raise ValueError("SMTP_PASSWORD is required")

        if not self.config.smtp_from_email:
            raise ValueError("SMTP_FROM_EMAIL is required")

        if self.config.smtp_use_tls and self.config.smtp_use_ssl:
            raise ValueError("Cannot use both TLS and SSL. Choose one.")

    def mask_email(self, email: str) -> str:
        """Mask email for logging: user@example.com → u***@e***.com"""
        if "@" not in email:
            return email[:1] + "***"
        local, domain = email.split("@", 1)
        masked_local = local[:1] + "***" if len(local) > 1 else "***"
        masked_domain = (
            domain[:1] + "***." + domain.split(".")[-1] if "." in domain else "***"
        )
        return f"{masked_local}@{masked_domain}"

    def _extract_provider_error(self, error_message: str) -> str:
        """
        Extract non-sensitive provider error information for audit logging.

        Args:
            error_message: Full error message from email provider

        Returns:
            Sanitized error reason suitable for audit logging
        """
        if not error_message:
            return "unknown_error"

        error_lower = error_message.lower()

        # Common SMTP error patterns (non-sensitive)
        if "timeout" in error_lower or "timed out" in error_lower:
            return "smtp_timeout"
        elif "connection refused" in error_lower or "connection failed" in error_lower:
            return "connection_refused"
        elif "authentication failed" in error_lower or "auth" in error_lower:
            return "authentication_failed"
        elif "invalid recipient" in error_lower or "recipient rejected" in error_lower:
            return "invalid_recipient"
        elif "quota exceeded" in error_lower or "rate limit" in error_lower:
            return "quota_exceeded"
        elif "dns" in error_lower or "hostname" in error_lower:
            return "dns_error"
        elif "ssl" in error_lower or "tls" in error_lower:
            return "ssl_tls_error"
        elif "network" in error_lower:
            return "network_error"
        elif (
            "server unavailable" in error_lower or "service unavailable" in error_lower
        ):
            return "server_unavailable"
        else:
            # Return generic error type without sensitive details
            return "smtp_error"

    def _generate_email_hash(
        self, to_email: str, subject: str, content_preview: str
    ) -> str:
        """
        Generate unique hash for email idempotency.

        Args:
            to_email: Recipient email address
            subject: Email subject
            content_preview: First 100 chars of email content for uniqueness

        Returns:
            SHA256 hash for idempotency tracking
        """
        content = f"{to_email}|{subject}|{content_preview[:100]}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _is_email_already_sent(self, email_hash: str) -> bool:
        """Check if email with this hash was already sent."""
        async with self._idempotency_lock:
            return email_hash in self._sent_emails

    async def _mark_email_as_sent(self, email_hash: str) -> None:
        """Mark email as sent for idempotency tracking."""
        async with self._idempotency_lock:
            self._sent_emails.add(email_hash)
            # Limit memory usage by keeping only recent hashes (last 1000)
            if len(self._sent_emails) > 1000:
                # Remove oldest 200 entries (simple FIFO approximation)
                oldest_hashes = list(self._sent_emails)[:200]
                for old_hash in oldest_hashes:
                    self._sent_emails.discard(old_hash)

    @retry(
        stop=stop_after_attempt(3),  # 2 retries + 1 initial attempt
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type(
            (
                smtplib.SMTPConnectError,
                ConnectionError,
                TimeoutError,
            )
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and configure SMTP connection."""
        try:
            logger.debug(
                f"SMTP_CONNECT: Connecting to {self.config.smtp_host}:{self.config.smtp_port}"
            )

            # Create SMTP connection
            if self.config.smtp_use_ssl:
                # SSL connection (port 465)
                context = ssl.create_default_context()
                smtp = smtplib.SMTP_SSL(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self._connection_timeout,
                    context=context,
                )
                logger.debug("SMTP_SSL: SSL connection established")
            else:
                # Regular connection, potentially with STARTTLS
                smtp = smtplib.SMTP(
                    self.config.smtp_host,
                    self.config.smtp_port,
                    timeout=self._connection_timeout,
                )

                if self.config.smtp_use_tls:
                    # Start TLS encryption
                    context = ssl.create_default_context()
                    smtp.starttls(context=context)
                    logger.debug("SMTP_TLS: TLS encryption enabled")

            # Authenticate
            smtp.login(self.config.smtp_username, self.config.smtp_password)
            logger.debug("SMTP_AUTH: Authentication successful")

            return smtp

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP_AUTH_FAILED: Authentication failed - {str(e)}")
            raise SMTPConnectionError(f"SMTP authentication failed: {str(e)}")
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP_CONNECT_FAILED: Connection failed - {str(e)}")
            raise SMTPConnectionError(f"SMTP connection failed: {str(e)}")
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"SMTP_DISCONNECTED: Server disconnected - {str(e)}")
            raise SMTPConnectionError(f"SMTP server disconnected: {str(e)}")
        except Exception as e:
            logger.error(f"SMTP_ERROR: Unexpected error - {str(e)}")
            raise SMTPConnectionError(f"SMTP connection error: {str(e)}")

    @asynccontextmanager
    async def _get_smtp_connection(self) -> AsyncGenerator[smtplib.SMTP, None]:
        """Get SMTP connection with connection pooling."""
        connection_key = f"{self.config.smtp_host}:{self.config.smtp_port}"
        smtp = None
        reusing_connection = False

        async with self._pool_lock:
            # Try to reuse existing connection
            if connection_key in self._connection_pool:
                smtp = self._connection_pool[connection_key]
                try:
                    # Test connection
                    smtp.noop()
                    logger.debug("SMTP_POOL: Reusing existing connection")
                    reusing_connection = True
                except Exception:
                    # Connection is stale, remove from pool
                    logger.debug("SMTP_POOL: Removing stale connection")
                    del self._connection_pool[connection_key]
                    smtp = None

            # Create new connection if needed
            if smtp is None:
                smtp = await self._create_smtp_connection()
                self._connection_pool[connection_key] = smtp

        try:
            yield smtp
        except Exception:
            # Remove failed connection from pool
            async with self._pool_lock:
                if connection_key in self._connection_pool:
                    del self._connection_pool[connection_key]
            raise
        finally:
            # Keep connection in pool for reuse
            pass

    @retry(
        stop=stop_after_attempt(4),  # 3 retries + 1 initial attempt
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                smtplib.SMTPRecipientsRefused,
                ConnectionError,
                TimeoutError,
                SMTPConnectionError,
            )
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _send_email_core(self, message: EmailMessage) -> tuple[str, int, int]:
        """Core email sending logic with tenacity retry."""
        start_time = time.time()
        retry_state = getattr(self._send_email_core.retry, "statistics", {})
        attempt_number = retry_state.get("attempt_number", 1) if retry_state else 1

        async with self._get_smtp_connection() as smtp:
            # Create MIME message
            mime_msg = MIMEMultipart("alternative")
            mime_msg["From"] = (
                f"{self.config.smtp_from_name} <{self.config.smtp_from_email}>"
            )
            mime_msg["To"] = message.to_email
            mime_msg["Subject"] = message.subject

            # Add plain text part if provided
            if message.plain_body:
                plain_part = MIMEText(message.plain_body, "plain", "utf-8")
                mime_msg.attach(plain_part)

            # Add HTML part
            html_part = MIMEText(message.html_body, "html", "utf-8")
            mime_msg.attach(html_part)

            # Send email
            smtp.send_message(mime_msg)

            delivery_time_ms = int((time.time() - start_time) * 1000)
            message_id = mime_msg.get("Message-ID", "")

            return message_id, delivery_time_ms, max(0, attempt_number - 1)

    async def _send_email_with_retry(
        self, message: EmailMessage
    ) -> EmailDeliveryResult:
        """Send email with tenacity-based retry logic."""
        try:
            message_id, delivery_time_ms, retry_count = await self._send_email_core(
                message
            )

            if retry_count > 0:
                logger.info(
                    f"EMAIL_SEND_SUCCESS: Email delivered to {self.mask_email(message.to_email)} in {delivery_time_ms}ms after {retry_count} retries"
                )
            else:
                logger.info(
                    f"EMAIL_SEND_SUCCESS: Email delivered to {self.mask_email(message.to_email)} in {delivery_time_ms}ms"
                )

            return EmailDeliveryResult(
                success=True,
                message_id=message_id,
                delivery_time_ms=delivery_time_ms,
                retry_count=retry_count,
            )

        except Exception as e:
            # Extract retry information from tenacity
            retry_count = 3  # Default fallback

            # Try to get actual retry count from tenacity context
            if hasattr(e, "__cause__") and hasattr(e.__cause__, "last_attempt"):
                retry_count = e.__cause__.last_attempt.attempt_number - 1
            elif hasattr(e, "last_attempt"):
                retry_count = e.last_attempt.attempt_number - 1

            error_msg = str(e)
            logger.error(
                f"EMAIL_SEND_FAILED: All retries exhausted for {self.mask_email(message.to_email)} after {retry_count} attempts - {error_msg}"
            )

            return EmailDeliveryResult(
                success=False, error=error_msg, retry_count=retry_count
            )

    async def send_otp_email(
        self, to_email: str, otp: str, telegram_id: int
    ) -> EmailDeliveryResult:
        """
        Send OTP verification email with idempotency protection.

        Args:
            to_email: Recipient email address
            otp: One-time password to send
            telegram_id: User's telegram ID for audit logging

        Returns:
            EmailDeliveryResult with delivery status
        """
        try:
            logger.info(
                f"OTP_EMAIL_COMPOSE: Preparing OTP email for {self.mask_email(to_email)}"
            )

            # Generate email content using templates
            subject = self.templates.get_otp_subject()
            html_body = self.templates.get_otp_html_body(otp)
            plain_body = self.templates.get_otp_plain_body(otp)

            # Check idempotency (prevent duplicate OTP sends)
            email_hash = self._generate_email_hash(to_email, subject, f"OTP:{otp}")
            if await self._is_email_already_sent(email_hash):
                logger.info(
                    f"OTP_DUPLICATE_BLOCKED: Duplicate OTP email blocked for {self.mask_email(to_email)}"
                )
                return EmailDeliveryResult(
                    success=True, message_id="duplicate_blocked", delivery_time_ms=0
                )

            message = EmailMessage(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                plain_body=plain_body,
            )

            # Send email with queue fallback for SMTP health issues
            result = await self._send_email_with_queue_fallback(message, email_hash)

            # Log audit event
            try:
                audit_service = get_audit_service()
                if result.success:
                    logger.info(f"OTP_SENT: Email sent to {self.mask_email(to_email)}")
                    audit_service.log_email_send_success(telegram_id, to_email)
                else:
                    logger.error(
                        f"OTP_SEND_FAILED: Failed to send OTP to {self.mask_email(to_email)} - {result.error}"
                    )
                    # Extract provider error info (non-sensitive)
                    error_reason = self._extract_provider_error(result.error)
                    audit_service.log_email_send_failure(
                        telegram_id, to_email, error_reason
                    )
            except Exception as audit_error:
                logger.error(
                    f"AUDIT_ERROR: Failed to log email audit event - {audit_error}"
                )

            return result

        except Exception as e:
            logger.error(
                f"OTP_EMAIL_ERROR: Unexpected error sending OTP to {self.mask_email(to_email)} - {str(e)}"
            )

            # Log audit event for unexpected error
            try:
                audit_service = get_audit_service()
                error_reason = self._extract_provider_error(str(e))
                audit_service.log_email_send_failure(
                    telegram_id, to_email, error_reason
                )
            except Exception as audit_error:
                logger.error(
                    f"AUDIT_ERROR: Failed to log email audit event - {audit_error}"
                )

            return EmailDeliveryResult(
                success=False, error=f"Unexpected error: {str(e)}"
            )

    async def send_optimized_prompts_email(
        self,
        to_email: str,
        original_prompt: str,
        improved_prompt: str,
        craft_result: str,
        lyra_result: str,
        ggl_result: str,
        telegram_id: int,
    ) -> EmailDeliveryResult:
        """
        Send optimized prompts email with all three optimization results and idempotency protection.

        Args:
            to_email: Recipient email address
            original_prompt: User's original prompt
            improved_prompt: Improved prompt from follow-up questions
            craft_result: CRAFT optimization result
            lyra_result: LYRA optimization result
            ggl_result: GGL optimization result
            telegram_id: User's telegram ID for audit logging

        Returns:
            EmailDeliveryResult with delivery status
        """
        try:
            logger.info(
                f"OPTIMIZATION_EMAIL_COMPOSE: Preparing optimization email for {self.mask_email(to_email)}"
            )

            # Generate email content using templates
            subject = self.templates.get_optimization_subject()
            html_body = self.templates.get_optimization_html_body(
                original_prompt=original_prompt,
                improved_prompt=improved_prompt,
                craft_result=craft_result,
                lyra_result=lyra_result,
                ggl_result=ggl_result,
            )
            plain_body = self.templates.get_optimization_plain_body(
                original_prompt=original_prompt,
                improved_prompt=improved_prompt,
                craft_result=craft_result,
                lyra_result=lyra_result,
                ggl_result=ggl_result,
            )

            # Check idempotency (prevent duplicate optimization emails)
            content_preview = (
                f"OPTIMIZATION:{original_prompt[:50]}:{improved_prompt[:50]}"
            )
            email_hash = self._generate_email_hash(to_email, subject, content_preview)
            if await self._is_email_already_sent(email_hash):
                logger.info(
                    f"OPTIMIZATION_DUPLICATE_BLOCKED: Duplicate optimization email blocked for {self.mask_email(to_email)}"
                )
                return EmailDeliveryResult(
                    success=True, message_id="duplicate_blocked", delivery_time_ms=0
                )

            message = EmailMessage(
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                plain_body=plain_body,
            )

            # Send email with queue fallback for SMTP health issues
            result = await self._send_email_with_queue_fallback(message, email_hash)

            # Log audit event
            try:
                audit_service = get_audit_service()
                if result.success:
                    logger.info(
                        f"OPTIMIZATION_EMAIL_SENT: Email delivered to {self.mask_email(to_email)}"
                    )
                    audit_service.log_email_send_success(telegram_id, to_email)
                else:
                    logger.error(
                        f"OPTIMIZATION_EMAIL_FAILED: Failed to send optimization email to {self.mask_email(to_email)} - {result.error}"
                    )
                    # Extract provider error info (non-sensitive)
                    error_reason = self._extract_provider_error(result.error)
                    audit_service.log_email_send_failure(
                        telegram_id, to_email, error_reason
                    )
            except Exception as audit_error:
                logger.error(
                    f"AUDIT_ERROR: Failed to log email audit event - {audit_error}"
                )

            return result

        except Exception as e:
            logger.error(
                f"OPTIMIZATION_EMAIL_ERROR: Unexpected error sending optimization email to {self.mask_email(to_email)} - {str(e)}"
            )

            # Log audit event for unexpected error
            try:
                audit_service = get_audit_service()
                error_reason = self._extract_provider_error(str(e))
                audit_service.log_email_send_failure(
                    telegram_id, to_email, error_reason
                )
            except Exception as audit_error:
                logger.error(
                    f"AUDIT_ERROR: Failed to log email audit event - {audit_error}"
                )

            return EmailDeliveryResult(
                success=False, error=f"Unexpected error: {str(e)}"
            )

    def get_fallback_prompts_text(
        self, craft_result: str, lyra_result: str, ggl_result: str
    ) -> str:
        """
        Get formatted text for chat fallback when email delivery fails.

        This method returns ONLY the three optimized prompts for chat delivery,
        following the strict fallback requirement (no improved prompt in chat).

        Args:
            craft_result: CRAFT optimization result
            lyra_result: LYRA optimization result
            ggl_result: GGL optimization result

        Returns:
            Formatted text with only the three optimized prompts
        """
        craft_label = _(
            "🛠 CRAFT - Структурированный подход:",
            "🛠 CRAFT - Structured Approach:",
            self.config.language,
        )

        lyra_label = _(
            "⚡ LYRA - Быстрая оптимизация:",
            "⚡ LYRA - Quick Optimization:",
            self.config.language,
        )

        ggl_label = _(
            "🔍 GGL - Фокус на цели:", "🔍 GGL - Goal-Focused:", self.config.language
        )

        fallback_note = _(
            "📧 Не удалось отправить на email. Вот ваши оптимизированные промпты:",
            "📧 Email delivery failed. Here are your optimized prompts:",
            self.config.language,
        )

        return f"""
{fallback_note}

{craft_label}
```
{craft_result}
```

{lyra_label}
```
{lyra_result}
```

{ggl_label}
```
{ggl_result}
```
"""

    @retry(
        stop=stop_after_attempt(2),  # Quick health check, only 1 retry
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        retry=retry_if_exception_type(
            (
                smtplib.SMTPServerDisconnected,
                smtplib.SMTPConnectError,
                ConnectionError,
                TimeoutError,
                SMTPConnectionError,
            )
        ),
        reraise=True,
    )
    async def _smtp_health_check_core(self) -> None:
        """Core SMTP health check with tenacity retry."""
        async with self._get_smtp_connection() as smtp:
            smtp.noop()

    async def _check_smtp_health(self) -> bool:
        """Check SMTP server health."""
        try:
            await self._smtp_health_check_core()
            return True
        except Exception as e:
            logger.warning(f"SMTP_HEALTH_CHECK_FAILED: {str(e)}")
            return False

    async def _update_smtp_health_status(self) -> None:
        """Update SMTP health status and start/stop queue worker as needed."""
        async with self._health_check_lock:
            old_status = self._smtp_healthy
            self._smtp_healthy = await self._check_smtp_health()

            if old_status != self._smtp_healthy:
                if self._smtp_healthy:
                    logger.info("SMTP_HEALTH_RECOVERED: SMTP server is healthy again")
                    await self._start_queue_worker()
                else:
                    logger.warning("SMTP_HEALTH_DEGRADED: SMTP server is unhealthy")
                    await self._stop_queue_worker()

    async def _enqueue_email(self, message: EmailMessage, email_hash: str) -> None:
        """Enqueue email for retry when SMTP is unhealthy."""
        try:
            queue_item = {
                "message": message,
                "email_hash": email_hash,
                "enqueued_at": time.time(),
                "attempts": 0,
            }
            await self._email_queue.put(queue_item)
            logger.info(
                f"EMAIL_QUEUED: Email queued for retry - {self.mask_email(message.to_email)}"
            )
        except Exception as e:
            logger.error(f"EMAIL_QUEUE_ERROR: Failed to enqueue email - {str(e)}")

    async def _start_queue_worker(self) -> None:
        """Start the background queue worker."""
        if not self._queue_worker_running and self._smtp_healthy:
            self._queue_worker_running = True
            self._queue_worker_task = asyncio.create_task(self._queue_worker())
            logger.info("EMAIL_QUEUE_WORKER_STARTED: Background worker started")

    async def _stop_queue_worker(self) -> None:
        """Stop the background queue worker."""
        if self._queue_worker_running and self._queue_worker_task:
            self._queue_worker_running = False
            self._queue_worker_task.cancel()
            try:
                await self._queue_worker_task
            except asyncio.CancelledError:
                pass
            self._queue_worker_task = None
            logger.info("EMAIL_QUEUE_WORKER_STOPPED: Background worker stopped")

    async def _queue_worker(self) -> None:
        """Background worker to process queued emails when SMTP is healthy."""
        logger.info("EMAIL_QUEUE_WORKER: Starting queue processing")

        while self._queue_worker_running and self._smtp_healthy:
            try:
                # Wait for queued email with timeout
                queue_item = await asyncio.wait_for(
                    self._email_queue.get(), timeout=5.0
                )

                message = queue_item["message"]
                email_hash = queue_item["email_hash"]
                attempts = queue_item["attempts"]

                logger.info(
                    f"EMAIL_QUEUE_PROCESSING: Processing queued email for {self.mask_email(message.to_email)}"
                )

                # Check if already sent (idempotency)
                if await self._is_email_already_sent(email_hash):
                    logger.info(
                        f"EMAIL_QUEUE_SKIP: Email already sent, skipping - {self.mask_email(message.to_email)}"
                    )
                    continue

                # Try to send the email
                result = await self._send_email_with_retry(message)

                if result.success:
                    # Mark as sent for idempotency
                    await self._mark_email_as_sent(email_hash)
                    logger.info(
                        f"EMAIL_QUEUE_SUCCESS: Queued email sent successfully - {self.mask_email(message.to_email)}"
                    )
                else:
                    # Re-queue if max attempts not reached
                    if attempts < 2:  # Max 3 total attempts
                        queue_item["attempts"] = attempts + 1
                        await self._email_queue.put(queue_item)
                        logger.warning(
                            f"EMAIL_QUEUE_RETRY: Re-queuing email (attempt {attempts + 1}/3) - {self.mask_email(message.to_email)}"
                        )
                    else:
                        logger.error(
                            f"EMAIL_QUEUE_FAILED: Max attempts reached, dropping email - {self.mask_email(message.to_email)}"
                        )

            except asyncio.TimeoutError:
                # No emails in queue, continue
                continue
            except Exception as e:
                logger.error(
                    f"EMAIL_QUEUE_WORKER_ERROR: Error processing queue - {str(e)}"
                )
                await asyncio.sleep(1)  # Brief pause before continuing

        logger.info("EMAIL_QUEUE_WORKER: Queue processing stopped")

    async def _send_email_with_queue_fallback(
        self, message: EmailMessage, email_hash: str
    ) -> EmailDeliveryResult:
        """
        Send email with queue fallback when SMTP is unhealthy.

        Args:
            message: Email message to send
            email_hash: Hash for idempotency tracking

        Returns:
            EmailDeliveryResult with delivery status
        """
        # Update SMTP health status
        await self._update_smtp_health_status()

        if self._smtp_healthy:
            # SMTP is healthy, send directly
            result = await self._send_email_with_retry(message)
            if result.success:
                await self._mark_email_as_sent(email_hash)
            return result
        else:
            # SMTP is unhealthy, enqueue for later
            await self._enqueue_email(message, email_hash)
            return EmailDeliveryResult(
                success=False, error="SMTP unhealthy, email queued for retry"
            )

    async def test_smtp_connection(self) -> bool:
        """
        Test SMTP connection and authentication.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("SMTP_TEST: Testing SMTP connection")

            # Use the same health check logic for consistency
            await self._smtp_health_check_core()

            logger.info("SMTP_TEST_SUCCESS: SMTP connection test passed")
            return True

        except Exception as e:
            logger.error(f"SMTP_TEST_FAILED: SMTP connection test failed - {str(e)}")
            return False

    async def close_connections(self) -> None:
        """Close all SMTP connections and stop queue worker."""
        # Stop queue worker
        await self._stop_queue_worker()

        # Close SMTP connections
        async with self._pool_lock:
            for connection_key, smtp in self._connection_pool.items():
                try:
                    smtp.quit()
                    logger.debug(f"SMTP_CLOSE: Closed connection {connection_key}")
                except Exception as e:
                    logger.warning(
                        f"SMTP_CLOSE_ERROR: Error closing connection {connection_key} - {str(e)}"
                    )

            self._connection_pool.clear()
            logger.info("SMTP_POOL_CLEARED: All SMTP connections closed")

    async def start_background_services(self) -> None:
        """Start background services (queue worker if SMTP is healthy)."""
        await self._update_smtp_health_status()
        logger.info("EMAIL_SERVICE_STARTED: Background services initialized")

    def health_check(self) -> bool:
        """
        Check if email service is healthy and ready to send emails.

        Returns:
            True if SMTP is healthy, False otherwise
        """
        return self._smtp_healthy

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status for monitoring."""
        return {
            "queue_size": self._email_queue.qsize(),
            "worker_running": self._queue_worker_running,
            "smtp_healthy": self._smtp_healthy,
            "sent_emails_count": len(self._sent_emails),
            "retry_config": {
                "max_attempts": 4,  # 3 retries + 1 initial
                "backoff": "exponential",
                "min_wait": 1,
                "max_wait": 10,
            },
        }


# Global email service instance
email_service: Optional[EmailService] = None


def init_email_service(config: BotConfig) -> EmailService:
    """
    Initialize global email service.

    Args:
        config: Bot configuration

    Returns:
        EmailService instance
    """
    global email_service
    email_service = EmailService(config)
    return email_service


def get_email_service() -> EmailService:
    """
    Get the global email service instance.

    Returns:
        EmailService instance

    Raises:
        RuntimeError: If email service is not initialized
    """
    if email_service is None:
        raise RuntimeError(
            "Email service not initialized. Call init_email_service() first."
        )
    return email_service
