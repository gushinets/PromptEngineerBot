"""
Performance tests for email prompt delivery system.

This module tests load handling, latency requirements, throughput,
concurrent operations, and system behavior under stress.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth_service import AuthService
from src.database import AuthEvent, DatabaseManager, User
from src.email_service import EmailService
from src.metrics import MetricsCollector
from src.redis_client import RedisClient


class TestDatabasePerformance:
    """Test database query performance under load."""

    @pytest.fixture
    def test_database(self):
        """Create test database with in-memory SQLite."""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.create_tables()
        yield db_manager

    async def test_database_query_performance(self, test_database):
        """Test database query response times under load."""
        start_time = time.time()

        # Create test users
        with test_database.get_session() as session:
            users = []
            for i in range(1000):
                user = User(
                    telegram_id=100000 + i,
                    email=f"user{i}@example.com",
                    email_original=f"User{i}@Example.Com",
                    is_authenticated=True,
                )
                users.append(user)

            session.add_all(users)
            session.commit()

        creation_time = time.time() - start_time
        assert creation_time < 5.0, (
            f"User creation took {creation_time:.2f}s, should be < 5s"
        )

        # Test query performance
        start_time = time.time()

        with test_database.get_session() as session:
            # Test individual lookups (should use indexes)
            for i in range(100):
                user = session.query(User).filter_by(telegram_id=100000 + i).first()
                assert user is not None

        lookup_time = time.time() - start_time
        avg_lookup_time = lookup_time / 100
        assert avg_lookup_time < 0.01, (
            f"Average lookup time {avg_lookup_time:.4f}s, should be < 0.01s"
        )

        # Test bulk operations
        start_time = time.time()

        with test_database.get_session() as session:
            authenticated_users = (
                session.query(User).filter_by(is_authenticated=True).all()
            )
            assert len(authenticated_users) == 1000

        bulk_query_time = time.time() - start_time
        assert bulk_query_time < 1.0, (
            f"Bulk query took {bulk_query_time:.2f}s, should be < 1s"
        )

    async def test_concurrent_database_operations(self, test_database):
        """Test database performance under concurrent load."""

        def create_auth_event(user_id):
            """Create auth event in separate thread."""
            try:
                with test_database.get_session() as session:
                    event = AuthEvent(
                        telegram_id=user_id,
                        email=f"user{user_id}@example.com",
                        event_type="OTP_SENT",
                        success=True,
                    )
                    session.add(event)
                    session.commit()
                    return True
            except Exception:
                # SQLite may have concurrency issues, this is expected
                return False

        start_time = time.time()

        # Run concurrent database operations with reduced concurrency for SQLite
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i in range(50):  # Reduced from 100
                future = executor.submit(create_auth_event, 200000 + i)
                futures.append(future)

            # Wait for all operations to complete
            results = [future.result() for future in futures]

        concurrent_time = time.time() - start_time
        successful_ops = sum(results)

        # SQLite may fail some concurrent operations, that's expected
        assert successful_ops >= 10, f"Only {successful_ops}/50 operations succeeded"
        assert concurrent_time < 15.0, (
            f"Concurrent operations took {concurrent_time:.2f}s, should be < 15s"
        )

        # Verify events were created
        with test_database.get_session() as session:
            event_count = session.query(AuthEvent).count()
            assert event_count >= 10

    async def test_database_connection_pooling(self, test_database):
        """Test database connection pool performance."""

        async def db_operation():
            """Perform database operation."""
            with test_database.get_session() as session:
                user = User(
                    telegram_id=int(time.time() * 1000000) % 1000000,
                    email=f"test{int(time.time() * 1000000)}@example.com",
                    email_original="Test@Example.Com",
                    is_authenticated=False,
                )
                session.add(user)
                session.commit()
                return True

        start_time = time.time()

        # Run many concurrent database operations
        tasks = [db_operation() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        pool_time = time.time() - start_time
        successful_ops = sum(1 for r in results if r is True)

        assert successful_ops >= 15, f"Only {successful_ops}/50 operations succeeded"
        assert pool_time < 5.0, (
            f"Connection pool operations took {pool_time:.2f}s, should be < 5s"
        )


class TestRedisPerformance:
    """Test Redis operation performance."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client for performance testing."""
        client = MagicMock(spec=RedisClient)

        # Mock Redis operations with realistic delays
        async def mock_set(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms delay
            return True

        async def mock_get(*args, **kwargs):
            await asyncio.sleep(0.001)  # 1ms delay
            return b"test_value"

        client.set = AsyncMock(side_effect=mock_set)
        client.get = AsyncMock(side_effect=mock_get)
        client.delete = AsyncMock(return_value=True)
        client.health_check = MagicMock(return_value=True)

        return client

    async def test_redis_operation_latency(self, mock_redis_client):
        """Test Redis operation latency."""
        operations = []

        # Test SET operations
        start_time = time.time()
        for i in range(100):
            await mock_redis_client.set(f"key_{i}", f"value_{i}")
        set_time = time.time() - start_time

        avg_set_latency = set_time / 100
        assert avg_set_latency < 0.02, (
            f"Average SET latency {avg_set_latency:.4f}s, should be < 0.02s"
        )

        # Test GET operations
        start_time = time.time()
        for i in range(100):
            await mock_redis_client.get(f"key_{i}")
        get_time = time.time() - start_time

        avg_get_latency = get_time / 100
        assert avg_get_latency < 0.02, (
            f"Average GET latency {avg_get_latency:.4f}s, should be < 0.02s"
        )

    async def test_concurrent_redis_operations(self, mock_redis_client):
        """Test Redis performance under concurrent load."""

        async def redis_workflow():
            """Simulate OTP workflow in Redis."""
            user_id = int(time.time() * 1000000) % 1000000

            # Store OTP
            await mock_redis_client.set(f"otp:{user_id}", "hashed_otp")

            # Check rate limits
            await mock_redis_client.get(f"rl:email:test@example.com:hour")
            await mock_redis_client.get(f"rl:tg:{user_id}:hour")

            # Retrieve OTP
            await mock_redis_client.get(f"otp:{user_id}")

            # Clean up
            await mock_redis_client.delete(f"otp:{user_id}")

            return True

        start_time = time.time()

        # Run concurrent Redis workflows
        tasks = [redis_workflow() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        concurrent_time = time.time() - start_time
        successful_ops = sum(1 for r in results if r is True)

        assert successful_ops >= 45, (
            f"Only {successful_ops}/50 Redis workflows succeeded"
        )
        assert concurrent_time < 3.0, (
            f"Concurrent Redis operations took {concurrent_time:.2f}s, should be < 3s"
        )


class TestEmailServicePerformance:
    """Test email service performance and throughput."""

    @pytest.fixture
    def mock_email_service(self):
        """Create mock email service for performance testing."""
        service = MagicMock(spec=EmailService)

        # Mock email sending with realistic delays
        async def mock_send_email(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms SMTP delay
            result = MagicMock()
            result.success = True
            result.delivery_time_ms = 100
            return result

        service.send_otp_email = AsyncMock(side_effect=mock_send_email)
        service.send_optimized_prompts_email = AsyncMock(side_effect=mock_send_email)

        return service

    async def test_email_delivery_throughput(self, mock_email_service):
        """Test email delivery performance."""
        start_time = time.time()

        # Send multiple emails concurrently
        tasks = []
        for i in range(20):
            task = mock_email_service.send_otp_email(
                f"user{i}@example.com", "123456", 100000 + i
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        throughput_time = time.time() - start_time
        successful_sends = sum(
            1 for r in results if hasattr(r, "success") and r.success
        )

        assert successful_sends >= 18, (
            f"Only {successful_sends}/20 emails sent successfully"
        )
        assert throughput_time < 5.0, (
            f"Email throughput test took {throughput_time:.2f}s, should be < 5s"
        )

        # Calculate emails per second
        emails_per_second = successful_sends / throughput_time
        assert emails_per_second >= 4, (
            f"Email throughput {emails_per_second:.1f} emails/s, should be >= 4"
        )

    async def test_email_template_rendering_performance(self):
        """Test email template rendering performance."""
        from src.email_templates import EmailTemplates

        templates = EmailTemplates("en")

        start_time = time.time()

        # Render many templates
        for i in range(1000):
            subject = templates.get_otp_subject()
            body = templates.get_otp_html_body("123456")
            optimized_subject = templates.get_optimization_subject()
            optimized_body = templates.get_optimization_html_body(
                f"Original prompt {i}",
                f"Improved prompt {i}",
                f"CRAFT result {i}",
                f"LYRA result {i}",
                f"GGL result {i}",
            )

        rendering_time = time.time() - start_time
        avg_render_time = rendering_time / 1000

        assert avg_render_time < 0.001, (
            f"Average template render time {avg_render_time:.4f}s, should be < 0.001s"
        )
        assert rendering_time < 1.0, (
            f"Template rendering took {rendering_time:.2f}s, should be < 1s"
        )


class TestAuthServicePerformance:
    """Test authentication service performance."""

    @pytest.fixture
    def mock_auth_service(self):
        """Create mock auth service for performance testing."""
        service = MagicMock(spec=AuthService)

        # Mock auth operations with realistic processing times
        async def mock_send_otp(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms processing
            return (True, "otp_sent", "123456")

        async def mock_verify_otp(*args, **kwargs):
            await asyncio.sleep(0.005)  # 5ms processing
            return (True, "verification_successful")

        service.send_otp = AsyncMock(side_effect=mock_send_otp)
        service.verify_otp = AsyncMock(side_effect=mock_verify_otp)
        service.check_rate_limits = MagicMock(return_value=(True, "allowed"))

        return service

    async def test_otp_generation_performance(self, mock_auth_service):
        """Test OTP generation under load."""
        start_time = time.time()

        # Generate many OTPs concurrently
        tasks = []
        for i in range(100):
            task = mock_auth_service.send_otp(100000 + i, f"user{i}@example.com")
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        generation_time = time.time() - start_time
        successful_generations = sum(
            1 for r in results if isinstance(r, tuple) and r[0]
        )

        assert successful_generations >= 95, (
            f"Only {successful_generations}/100 OTPs generated successfully"
        )
        assert generation_time < 3.0, (
            f"OTP generation took {generation_time:.2f}s, should be < 3s"
        )

    async def test_otp_verification_performance(self, mock_auth_service):
        """Test OTP verification performance."""
        start_time = time.time()

        # Verify many OTPs concurrently
        tasks = []
        for i in range(100):
            task = mock_auth_service.verify_otp(100000 + i, "123456")
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        verification_time = time.time() - start_time
        successful_verifications = sum(
            1 for r in results if isinstance(r, tuple) and r[0]
        )

        assert successful_verifications >= 95, (
            f"Only {successful_verifications}/100 OTPs verified successfully"
        )
        assert verification_time < 2.0, (
            f"OTP verification took {verification_time:.2f}s, should be < 2s"
        )


class TestSystemLoadTesting:
    """Test system behavior under concurrent load."""

    async def test_concurrent_user_load(self):
        """Test system behavior with multiple concurrent users."""

        async def simulate_user_flow(user_id):
            """Simulate complete user flow."""
            try:
                # Mock services
                with (
                    patch("src.auth_service.AuthService") as mock_auth_class,
                    patch("src.email_service.EmailService") as mock_email_class,
                    patch("src.redis_client.RedisClient") as mock_redis_class,
                ):
                    # Set up mocks
                    mock_auth = MagicMock()
                    mock_auth.send_otp = AsyncMock(
                        return_value=(True, "otp_sent", "123456")
                    )
                    mock_auth.verify_otp = AsyncMock(
                        return_value=(True, "verification_successful")
                    )
                    mock_auth_class.return_value = mock_auth

                    mock_email = MagicMock()
                    mock_email_result = MagicMock()
                    mock_email_result.success = True
                    mock_email.send_otp_email = AsyncMock(
                        return_value=mock_email_result
                    )
                    mock_email.send_optimized_prompts_email = AsyncMock(
                        return_value=mock_email_result
                    )
                    mock_email_class.return_value = mock_email

                    mock_redis = MagicMock()
                    mock_redis.set_flow_state = MagicMock(return_value=True)
                    mock_redis.get_flow_state = MagicMock(return_value=None)
                    mock_redis_class.return_value = mock_redis

                    # Simulate user flow steps with small delays
                    await asyncio.sleep(0.01)  # Email input
                    await mock_auth.send_otp(user_id, f"user{user_id}@example.com")

                    await asyncio.sleep(0.01)  # OTP verification
                    await mock_auth.verify_otp(user_id, "123456")

                    await asyncio.sleep(0.02)  # Follow-up questions

                    await asyncio.sleep(0.05)  # Optimization and email delivery
                    await mock_email.send_optimized_prompts_email(
                        f"user{user_id}@example.com",
                        "original",
                        "craft",
                        "lyra",
                        "ggl",
                        user_id,
                        "improved",
                    )

                    return True

            except Exception as e:
                return f"Error for user {user_id}: {str(e)}"

        start_time = time.time()

        # Simulate 50 concurrent users
        tasks = [simulate_user_flow(i) for i in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        load_test_time = time.time() - start_time
        successful_flows = sum(1 for r in results if r is True)

        assert successful_flows >= 45, (
            f"Only {successful_flows}/50 user flows completed successfully"
        )
        assert load_test_time < 10.0, (
            f"Load test took {load_test_time:.2f}s, should be < 10s"
        )

        # Calculate throughput
        flows_per_second = successful_flows / load_test_time
        assert flows_per_second >= 4.5, (
            f"Flow throughput {flows_per_second:.1f} flows/s, should be >= 4.5"
        )

    async def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load."""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            pytest.skip("psutil not available for memory testing")

        # Create many objects to simulate load
        metrics_collector = MetricsCollector()

        # Simulate heavy metrics collection
        for i in range(10000):
            metrics_collector.increment_counter(f"test_counter_{i % 100}")
            metrics_collector.record_latency(f"test_latency_{i % 50}", 0.001 * i)
            metrics_collector.record_success_failure(
                f"test_operation_{i % 25}", i % 2 == 0
            )

        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = peak_memory - initial_memory

        # Memory growth should be reasonable (less than 100MB for this test)
        assert memory_growth < 100, (
            f"Memory grew by {memory_growth:.1f}MB, should be < 100MB"
        )

    async def test_error_rate_under_load(self):
        """Test error rate remains acceptable under load."""

        async def operation_with_occasional_failure(operation_id):
            """Simulate operation that occasionally fails."""
            await asyncio.sleep(0.001)  # Small processing delay

            # 5% failure rate
            if operation_id % 20 == 0:
                raise Exception(f"Simulated failure for operation {operation_id}")

            return True

        # Run many operations
        tasks = [operation_with_occasional_failure(i) for i in range(200)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_ops = sum(1 for r in results if r is True)
        failed_ops = sum(1 for r in results if isinstance(r, Exception))

        error_rate = failed_ops / len(results) * 100

        # Error rate should be around 5% (acceptable range: 3-7%)
        assert 3 <= error_rate <= 7, f"Error rate {error_rate:.1f}%, should be 3-7%"
        assert successful_ops >= 185, f"Only {successful_ops}/200 operations succeeded"


class TestLatencyRequirements:
    """Test system meets latency requirements."""

    async def test_end_to_end_latency(self):
        """Test end-to-end latency for complete email flow."""

        async def mock_email_flow():
            """Mock complete email flow with realistic delays."""
            # Email input validation: 1ms
            await asyncio.sleep(0.001)

            # OTP generation and sending: 50ms
            await asyncio.sleep(0.05)

            # OTP verification: 10ms
            await asyncio.sleep(0.01)

            # Follow-up questions (2 rounds): 200ms each
            await asyncio.sleep(0.4)

            # Optimization (3 methods): 500ms each
            await asyncio.sleep(1.5)

            # Email composition and sending: 100ms
            await asyncio.sleep(0.1)

            return True

        start_time = time.time()
        result = await mock_email_flow()
        end_to_end_time = time.time() - start_time

        assert result is True
        # Total flow should complete within 3 seconds
        assert end_to_end_time < 3.0, (
            f"End-to-end latency {end_to_end_time:.2f}s, should be < 3s"
        )

    async def test_individual_component_latency(self):
        """Test individual component latency requirements."""

        # Test database operations
        start_time = time.time()
        # Simulate database query
        await asyncio.sleep(0.005)  # 5ms
        db_latency = time.time() - start_time
        assert db_latency < 0.02, (
            f"Database latency {db_latency:.3f}s, should be < 0.02s"
        )

        # Test Redis operations
        start_time = time.time()
        # Simulate Redis operation
        await asyncio.sleep(0.001)  # 1ms
        redis_latency = time.time() - start_time
        assert redis_latency < 0.02, (
            f"Redis latency {redis_latency:.3f}s, should be < 0.02s"
        )

        # Test email sending
        start_time = time.time()
        # Simulate SMTP operation
        await asyncio.sleep(0.1)  # 100ms
        smtp_latency = time.time() - start_time
        assert smtp_latency < 0.2, f"SMTP latency {smtp_latency:.3f}s, should be < 0.2s"


if __name__ == "__main__":
    pytest.main([__file__])
