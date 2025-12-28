"""Property-based tests for Sessions Export filtering in ReportService.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 7: Sessions Export Filtering**
**Validates: Requirements 4.2, 4.3**
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
    email: str | None = None,
) -> User:
    """Create a test user in the database."""
    user = User(
        telegram_id=telegram_id,
        email=email,
        last_interaction_at=last_interaction_at,
        first_interaction_at=last_interaction_at,
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


class TestSessionsExportFiltering:
    """
    **Feature: marketing-reports, Property 7: Sessions Export Filtering**
    **Validates: Requirements 4.2, 4.3**

    Property 7: Sessions Export Filtering
    *For any* set of sessions with various statuses and dates, the Sessions_Export
    should include exactly those sessions where status equals "successful" AND
    start_time falls on the report date.
    """

    @given(
        successful_on_date=st.integers(min_value=0, max_value=10),
        unsuccessful_on_date=st.integers(min_value=0, max_value=10),
        in_progress_on_date=st.integers(min_value=0, max_value=10),
        successful_other_date=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_export_includes_only_successful_sessions_on_report_date(
        self,
        successful_on_date: int,
        unsuccessful_on_date: int,
        in_progress_on_date: int,
        successful_other_date: int,
    ):
        """
        **Feature: marketing-reports, Property 7: Sessions Export Filtering**
        **Validates: Requirements 4.2, 4.3**

        For any set of sessions with various statuses and dates, the export
        should include exactly those sessions where status='successful' AND
        start_time is on the report date.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        report_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        other_datetime = report_datetime - timedelta(days=1)

        try:
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            expected_session_ids = set()

            for _ in range(successful_on_date):
                session = create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )
                expected_session_ids.add(session.id)

            for _ in range(unsuccessful_on_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="LYRA",
                    status="unsuccessful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            for _ in range(in_progress_on_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="GGL",
                    status="in_progress",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            for _ in range(successful_other_date):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
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
            rows, timing = service.export_sessions(report_date)

            actual_session_ids = {row.id for row in rows}

            assert actual_session_ids == expected_session_ids, (
                f"Expected session IDs {expected_session_ids}, got {actual_session_ids}"
            )
            assert len(rows) == successful_on_date, (
                f"Expected {successful_on_date} rows, got {len(rows)}"
            )
            assert timing.row_count == successful_on_date, (
                f"Timing row_count should be {successful_on_date}, got {timing.row_count}"
            )
        finally:
            db_session.close()

    @given(
        sessions_data=st.lists(
            st.tuples(
                session_status_strategy,
                st.integers(min_value=-3, max_value=3),
            ),
            min_size=1,
            max_size=30,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_export_filtering_for_random_sessions(
        self,
        sessions_data: list[tuple[str, int]],
    ):
        """
        **Feature: marketing-reports, Property 7: Sessions Export Filtering**
        **Validates: Requirements 4.2, 4.3**

        For any random sequence of sessions with various statuses and dates,
        the export should include exactly those sessions where status='successful'
        AND start_time is on the report date (days_offset=0).
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        report_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)

        try:
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            expected_session_ids = set()

            for status, days_offset in sessions_data:
                session_datetime = report_datetime + timedelta(days=days_offset)
                session = create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status=status,
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=session_datetime,
                )
                if status == "successful" and days_offset == 0:
                    expected_session_ids.add(session.id)

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=30,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.export_sessions(report_date)

            actual_session_ids = {row.id for row in rows}

            assert actual_session_ids == expected_session_ids, (
                f"Expected session IDs {expected_session_ids}, got {actual_session_ids}"
            )
        finally:
            db_session.close()

    @given(
        successful_count=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_all_exported_sessions_have_successful_status(
        self,
        successful_count: int,
    ):
        """
        **Feature: marketing-reports, Property 7: Sessions Export Filtering**
        **Validates: Requirements 4.2**

        For any export result, all sessions should have status='successful'.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        report_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)

        try:
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            for _ in range(successful_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                    start_time=report_datetime,
                )

            for _ in range(5):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="LYRA",
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
            rows, _ = service.export_sessions(report_date)

            for row in rows:
                assert row.status == "successful", (
                    f"Exported session {row.id} has status '{row.status}', expected 'successful'"
                )

            assert len(rows) == successful_count, (
                f"Expected {successful_count} rows, got {len(rows)}"
            )
        finally:
            db_session.close()

    def test_export_returns_empty_list_when_no_successful_sessions_on_date(self):
        """
        **Feature: marketing-reports, Property 7: Sessions Export Filtering**
        **Validates: Requirements 4.2, 4.3**

        When there are no successful sessions on the report date, the export
        should return an empty list.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()
        report_datetime = datetime.combine(report_date, datetime.min.time()).replace(tzinfo=UTC)
        other_datetime = report_datetime - timedelta(days=1)

        try:
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            create_session(
                db_session,
                user_id=user.id,
                optimization_method="CRAFT",
                status="unsuccessful",
                tokens_total=100,
                duration_seconds=60,
                start_time=report_datetime,
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

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=30,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, timing = service.export_sessions(report_date)

            assert len(rows) == 0, f"Expected 0 rows, got {len(rows)}"
            assert timing.row_count == 0, f"Timing row_count should be 0, got {timing.row_count}"
        finally:
            db_session.close()
