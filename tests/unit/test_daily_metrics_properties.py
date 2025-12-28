"""Property-based tests for Daily Metrics calculations in ReportService.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 6: Daily Metrics Method Counts**
**Validates: Requirements 3.5, 3.6, 3.7, 3.8**
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from telegram_bot.data.database import Base, Session, User
from telegram_bot.services.report_config import ReportConfig
from telegram_bot.services.report_service import ReportService


# Strategy for generating valid optimization methods
optimization_method_strategy = st.sampled_from(["CRAFT", "LYRA", "GGL", None])

# Strategy for generating session status
session_status_strategy = st.sampled_from(["successful", "unsuccessful", "in_progress"])


def create_test_db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory()


def create_user(
    db_session,
    telegram_id: int,
    last_interaction_at: datetime,
    first_interaction_at: datetime | None = None,
    email: str | None = None,
) -> User:
    """Create a test user in the database."""
    user = User(
        telegram_id=telegram_id,
        email=email,
        last_interaction_at=last_interaction_at,
        first_interaction_at=first_interaction_at or last_interaction_at,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_session(
    db_session,
    user_id: int,
    optimization_method: str | None,
    status: str,
    tokens_total: int,
    duration_seconds: int,
    start_time: datetime,
) -> Session:
    """Create a test session in the database."""
    session = Session(
        user_id=user_id,
        optimization_method=optimization_method,
        status=status,
        tokens_total=tokens_total,
        duration_seconds=duration_seconds,
        model_name="test-model",
        start_time=start_time,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


class TestDailyMetricsMethodCounts:
    """
    **Feature: marketing-reports, Property 6: Daily Metrics Method Counts**
    **Validates: Requirements 3.5, 3.6, 3.7, 3.8**

    Property 6: Daily Metrics Method Counts
    *For any* report date with sessions using different optimization methods,
    CraftUsed, LyraUsed, and GglUsed should count only successful sessions
    with the respective method on that date.
    """

    @given(
        craft_successful=st.integers(min_value=0, max_value=10),
        craft_unsuccessful=st.integers(min_value=0, max_value=10),
        lyra_successful=st.integers(min_value=0, max_value=10),
        lyra_unsuccessful=st.integers(min_value=0, max_value=10),
        ggl_successful=st.integers(min_value=0, max_value=10),
        ggl_unsuccessful=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_method_counts_only_include_successful_sessions(
        self,
        craft_successful: int,
        craft_unsuccessful: int,
        lyra_successful: int,
        lyra_unsuccessful: int,
        ggl_successful: int,
        ggl_unsuccessful: int,
    ):
        """
        **Feature: marketing-reports, Property 6: Daily Metrics Method Counts**
        **Validates: Requirements 3.5, 3.6, 3.7, 3.8**

        For any report date with sessions using different optimization methods
        and statuses, CraftUsed, LyraUsed, and GglUsed should count only
        successful sessions with the respective method.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        report_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Create successful CRAFT sessions on report date
            for _ in range(craft_successful):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create unsuccessful CRAFT sessions on report date
            for _ in range(craft_unsuccessful):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="unsuccessful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create successful LYRA sessions on report date
            for _ in range(lyra_successful):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="LYRA",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create unsuccessful LYRA sessions on report date
            for _ in range(lyra_unsuccessful):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="LYRA",
                    status="unsuccessful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create successful GGL sessions on report date
            for _ in range(ggl_successful):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="GGL",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create unsuccessful GGL sessions on report date
            for _ in range(ggl_unsuccessful):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="GGL",
                    status="unsuccessful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=30,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            metrics, _ = service.generate_daily_metrics(report_date)

            # Property: Method counts should only include successful sessions
            assert metrics.craft_used == craft_successful, (
                f"CraftUsed should be {craft_successful}, got {metrics.craft_used}"
            )
            assert metrics.lyra_used == lyra_successful, (
                f"LyraUsed should be {lyra_successful}, got {metrics.lyra_used}"
            )
            assert metrics.ggl_used == ggl_successful, (
                f"GglUsed should be {ggl_successful}, got {metrics.ggl_used}"
            )

            # Also verify total_prompts counts only successful sessions
            expected_total_prompts = craft_successful + lyra_successful + ggl_successful
            assert metrics.total_prompts == expected_total_prompts, (
                f"TotalPrompts should be {expected_total_prompts}, got {metrics.total_prompts}"
            )
        finally:
            db_session.close()

    @given(
        methods_and_statuses=st.lists(
            st.tuples(
                optimization_method_strategy,
                session_status_strategy,
            ),
            min_size=1,
            max_size=30,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_method_counts_for_random_sessions(
        self,
        methods_and_statuses: list[tuple[str | None, str]],
    ):
        """
        **Feature: marketing-reports, Property 6: Daily Metrics Method Counts**
        **Validates: Requirements 3.5, 3.6, 3.7, 3.8**

        For any random sequence of sessions with various optimization methods
        and statuses, the method counts should match the count of successful
        sessions for each method.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        report_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Calculate expected counts
            expected_craft = sum(
                1 for m, s in methods_and_statuses if m == "CRAFT" and s == "successful"
            )
            expected_lyra = sum(
                1 for m, s in methods_and_statuses if m == "LYRA" and s == "successful"
            )
            expected_ggl = sum(
                1 for m, s in methods_and_statuses if m == "GGL" and s == "successful"
            )
            expected_total_prompts = sum(1 for _, s in methods_and_statuses if s == "successful")

            # Create sessions with the given methods and statuses
            for method, status in methods_and_statuses:
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method=method,
                    status=status,
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=30,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            metrics, _ = service.generate_daily_metrics(report_date)

            # Property: Method counts should match expected values
            assert metrics.craft_used == expected_craft, (
                f"CraftUsed should be {expected_craft}, got {metrics.craft_used}"
            )
            assert metrics.lyra_used == expected_lyra, (
                f"LyraUsed should be {expected_lyra}, got {metrics.lyra_used}"
            )
            assert metrics.ggl_used == expected_ggl, (
                f"GglUsed should be {expected_ggl}, got {metrics.ggl_used}"
            )
            assert metrics.total_prompts == expected_total_prompts, (
                f"TotalPrompts should be {expected_total_prompts}, got {metrics.total_prompts}"
            )
        finally:
            db_session.close()

    @given(
        craft_on_date=st.integers(min_value=0, max_value=10),
        craft_other_date=st.integers(min_value=0, max_value=10),
        lyra_on_date=st.integers(min_value=0, max_value=10),
        lyra_other_date=st.integers(min_value=0, max_value=10),
        ggl_on_date=st.integers(min_value=0, max_value=10),
        ggl_other_date=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_method_counts_only_include_sessions_on_report_date(
        self,
        craft_on_date: int,
        craft_other_date: int,
        lyra_on_date: int,
        lyra_other_date: int,
        ggl_on_date: int,
        ggl_other_date: int,
    ):
        """
        **Feature: marketing-reports, Property 6: Daily Metrics Method Counts**
        **Validates: Requirements 3.5, 3.6, 3.7, 3.8**

        For any report date, method counts should only include successful
        sessions that occurred on that specific date, not on other dates.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        report_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        other_datetime = report_datetime - timedelta(days=1)

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Create successful CRAFT sessions on report date
            for _ in range(craft_on_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create successful CRAFT sessions on other date
            for _ in range(craft_other_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=other_datetime,
                )

            # Create successful LYRA sessions on report date
            for _ in range(lyra_on_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="LYRA",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create successful LYRA sessions on other date
            for _ in range(lyra_other_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="LYRA",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=other_datetime,
                )

            # Create successful GGL sessions on report date
            for _ in range(ggl_on_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="GGL",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            # Create successful GGL sessions on other date
            for _ in range(ggl_other_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="GGL",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=other_datetime,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=30,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            metrics, _ = service.generate_daily_metrics(report_date)

            # Property: Method counts should only include sessions on report date
            assert metrics.craft_used == craft_on_date, (
                f"CraftUsed should be {craft_on_date}, got {metrics.craft_used}"
            )
            assert metrics.lyra_used == lyra_on_date, (
                f"LyraUsed should be {lyra_on_date}, got {metrics.lyra_used}"
            )
            assert metrics.ggl_used == ggl_on_date, (
                f"GglUsed should be {ggl_on_date}, got {metrics.ggl_used}"
            )

            # Also verify total_prompts counts only sessions on report date
            expected_total_prompts = craft_on_date + lyra_on_date + ggl_on_date
            assert metrics.total_prompts == expected_total_prompts, (
                f"TotalPrompts should be {expected_total_prompts}, got {metrics.total_prompts}"
            )
        finally:
            db_session.close()

    def test_method_counts_are_zero_when_no_sessions_on_date(self):
        """
        **Feature: marketing-reports, Property 6: Daily Metrics Method Counts**
        **Validates: Requirements 3.5, 3.6, 3.7, 3.8**

        When there are no sessions on the report date, all method counts
        should be zero.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        other_datetime = datetime.combine(
            report_date - timedelta(days=1), datetime.min.time()
        ).replace(tzinfo=UTC)

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Create sessions on a different date
            create_session(
                db_session,
                user_id=user.id,
                optimization_method="CRAFT",
                status="successful",
                tokens_total=100,
                duration_seconds=60,
                start_time=other_datetime,
            )
            create_session(
                db_session,
                user_id=user.id,
                optimization_method="LYRA",
                status="successful",
                tokens_total=100,
                duration_seconds=60,
                start_time=other_datetime,
            )
            create_session(
                db_session,
                user_id=user.id,
                optimization_method="GGL",
                status="successful",
                tokens_total=100,
                duration_seconds=60,
                start_time=other_datetime,
            )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=30,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            metrics, _ = service.generate_daily_metrics(report_date)

            # Property: All method counts should be zero when no sessions on date
            assert metrics.craft_used == 0, f"CraftUsed should be 0, got {metrics.craft_used}"
            assert metrics.lyra_used == 0, f"LyraUsed should be 0, got {metrics.lyra_used}"
            assert metrics.ggl_used == 0, f"GglUsed should be 0, got {metrics.ggl_used}"
            assert metrics.total_prompts == 0, (
                f"TotalPrompts should be 0, got {metrics.total_prompts}"
            )
        finally:
            db_session.close()
