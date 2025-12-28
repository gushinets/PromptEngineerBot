"""Property-based tests for User Summary calculations in ReportService.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 2: User Activity Filtering**
**Validates: Requirements 2.2, 2.3**

**Feature: marketing-reports, Property 3: Method Count Accuracy**
**Validates: Requirements 2.6, 2.7, 2.8**

**Feature: marketing-reports, Property 4: Success Rate Calculation**
**Validates: Requirements 2.5, 2.10**

**Feature: marketing-reports, Property 5: Average Calculations**
**Validates: Requirements 2.9, 2.12**
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

# Strategy for generating positive integers for tokens and duration
positive_int_strategy = st.integers(min_value=1, max_value=10000)

# Strategy for generating non-negative integers
non_negative_int_strategy = st.integers(min_value=0, max_value=10000)


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
    start_time: datetime | None = None,
) -> Session:
    """Create a test session in the database."""
    session = Session(
        user_id=user_id,
        optimization_method=optimization_method,
        status=status,
        tokens_total=tokens_total,
        duration_seconds=duration_seconds,
        model_name="test-model",
        start_time=start_time or datetime.now(UTC),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


class TestUserActivityFiltering:
    """
    **Feature: marketing-reports, Property 2: User Activity Filtering**
    **Validates: Requirements 2.2, 2.3**

    Property 2: User Activity Filtering
    *For any* set of users with various last_interaction_at timestamps and a
    positive activity_days value N, the User_Summary_Report should include
    exactly those users whose last_interaction_at is within N days of the
    report date.
    """

    @given(
        activity_days=st.integers(min_value=1, max_value=365),
        days_ago_list=st.lists(
            st.integers(min_value=0, max_value=400),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_users_within_activity_window_are_included(
        self,
        activity_days: int,
        days_ago_list: list[int],
    ):
        """
        **Feature: marketing-reports, Property 2: User Activity Filtering**
        **Validates: Requirements 2.2**

        For any positive activity_days value N and set of users with various
        last_interaction_at timestamps, only users whose last_interaction_at
        is within N days of the report date should be included.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create users with different last_interaction_at dates
            expected_user_ids = set()
            for i, days_ago in enumerate(days_ago_list):
                last_interaction = datetime.now(UTC) - timedelta(days=days_ago)
                user = create_user(
                    db_session,
                    telegram_id=1000 + i,
                    last_interaction_at=last_interaction,
                    email=f"user{i}@test.com",
                )
                # User should be included if within activity window
                if days_ago <= activity_days:
                    expected_user_ids.add(user.id)

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=activity_days,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=False)

            actual_user_ids = {row.user_id for row in rows}

            # Property: Only users within activity window should be included
            assert actual_user_ids == expected_user_ids, (
                f"With activity_days={activity_days}, expected users {expected_user_ids}, "
                f"got {actual_user_ids}"
            )
        finally:
            db_session.close()

    @given(
        days_ago_list=st.lists(
            st.integers(min_value=0, max_value=400),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_all_users_included_when_activity_days_is_zero(
        self,
        days_ago_list: list[int],
    ):
        """
        **Feature: marketing-reports, Property 2: User Activity Filtering**
        **Validates: Requirements 2.3**

        When activity_days is 0, all users should be included regardless
        of their last_interaction_at timestamp.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create users with different last_interaction_at dates
            all_user_ids = set()
            for i, days_ago in enumerate(days_ago_list):
                last_interaction = datetime.now(UTC) - timedelta(days=days_ago)
                user = create_user(
                    db_session,
                    telegram_id=1000 + i,
                    last_interaction_at=last_interaction,
                    email=f"user{i}@test.com",
                )
                all_user_ids.add(user.id)

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,  # 0 means include all users
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=False)

            actual_user_ids = {row.user_id for row in rows}

            # Property: All users should be included when activity_days=0
            assert actual_user_ids == all_user_ids, (
                f"With activity_days=0, expected all users {all_user_ids}, got {actual_user_ids}"
            )
        finally:
            db_session.close()

    @given(
        activity_days=st.integers(min_value=1, max_value=365),
        days_ago_list=st.lists(
            st.integers(min_value=0, max_value=400),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_include_all_users_flag_overrides_activity_filter(
        self,
        activity_days: int,
        days_ago_list: list[int],
    ):
        """
        **Feature: marketing-reports, Property 2: User Activity Filtering**
        **Validates: Requirements 2.2, 2.3**

        When include_all_users=True, all users should be included regardless
        of the configured activity_days value.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create users with different last_interaction_at dates
            all_user_ids = set()
            for i, days_ago in enumerate(days_ago_list):
                last_interaction = datetime.now(UTC) - timedelta(days=days_ago)
                user = create_user(
                    db_session,
                    telegram_id=1000 + i,
                    last_interaction_at=last_interaction,
                    email=f"user{i}@test.com",
                )
                all_user_ids.add(user.id)

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=activity_days,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            actual_user_ids = {row.user_id for row in rows}

            # Property: All users should be included when include_all_users=True
            assert actual_user_ids == all_user_ids, (
                f"With include_all_users=True, expected all users {all_user_ids}, "
                f"got {actual_user_ids}"
            )
        finally:
            db_session.close()


class TestMethodCountAccuracy:
    """
    **Feature: marketing-reports, Property 3: Method Count Accuracy**
    **Validates: Requirements 2.6, 2.7, 2.8**

    Property 3: Method Count Accuracy
    *For any* user with sessions using different optimization methods
    (CRAFT, LYRA, GGL), the CraftCount, LyraCount, and GglCount in the
    User_Summary_Report should equal the actual count of sessions with
    each respective method.
    """

    @given(
        craft_count=st.integers(min_value=0, max_value=20),
        lyra_count=st.integers(min_value=0, max_value=20),
        ggl_count=st.integers(min_value=0, max_value=20),
        none_count=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_method_counts_match_actual_session_counts(
        self,
        craft_count: int,
        lyra_count: int,
        ggl_count: int,
        none_count: int,
    ):
        """
        **Feature: marketing-reports, Property 3: Method Count Accuracy**
        **Validates: Requirements 2.6, 2.7, 2.8**

        For any user with a known number of sessions per optimization method,
        the reported counts should exactly match the actual counts.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Create sessions with different methods
            for _ in range(craft_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            for _ in range(lyra_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="LYRA",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            for _ in range(ggl_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="GGL",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            for _ in range(none_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method=None,
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Property: Method counts should match actual session counts
            assert row.craft_count == craft_count, (
                f"CraftCount should be {craft_count}, got {row.craft_count}"
            )
            assert row.lyra_count == lyra_count, (
                f"LyraCount should be {lyra_count}, got {row.lyra_count}"
            )
            assert row.ggl_count == ggl_count, (
                f"GglCount should be {ggl_count}, got {row.ggl_count}"
            )

            # Also verify total sessions
            expected_total = craft_count + lyra_count + ggl_count + none_count
            assert row.total_sessions == expected_total, (
                f"TotalSessions should be {expected_total}, got {row.total_sessions}"
            )
        finally:
            db_session.close()

    @given(
        methods=st.lists(
            optimization_method_strategy,
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_method_counts_sum_correctly_for_random_sessions(
        self,
        methods: list[str | None],
    ):
        """
        **Feature: marketing-reports, Property 3: Method Count Accuracy**
        **Validates: Requirements 2.6, 2.7, 2.8**

        For any random sequence of sessions with various optimization methods,
        the sum of CraftCount + LyraCount + GglCount + sessions with None
        should equal TotalSessions.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Count expected values
            expected_craft = sum(1 for m in methods if m == "CRAFT")
            expected_lyra = sum(1 for m in methods if m == "LYRA")
            expected_ggl = sum(1 for m in methods if m == "GGL")

            # Create sessions with the given methods
            for method in methods:
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method=method,
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Property: Method counts should match expected values
            assert row.craft_count == expected_craft
            assert row.lyra_count == expected_lyra
            assert row.ggl_count == expected_ggl
            assert row.total_sessions == len(methods)
        finally:
            db_session.close()


class TestSuccessRateCalculation:
    """
    **Feature: marketing-reports, Property 4: Success Rate Calculation**
    **Validates: Requirements 2.5, 2.10**

    Property 4: Success Rate Calculation
    *For any* user with a mix of successful and unsuccessful sessions,
    the SuccessRate should equal (successful_count / total_count) * 100,
    and TotalPrompts should equal TotalSessions.
    """

    @given(
        successful_count=st.integers(min_value=0, max_value=50),
        unsuccessful_count=st.integers(min_value=0, max_value=50),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_success_rate_calculation_accuracy(
        self,
        successful_count: int,
        unsuccessful_count: int,
    ):
        """
        **Feature: marketing-reports, Property 4: Success Rate Calculation**
        **Validates: Requirements 2.10**

        For any user with a known number of successful and unsuccessful
        sessions, the SuccessRate should equal (successful / total) * 100.
        """
        # Skip if no sessions (avoid division by zero edge case)
        total_count = successful_count + unsuccessful_count
        if total_count == 0:
            return

        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Create successful sessions
            for _ in range(successful_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            # Create unsuccessful sessions
            for _ in range(unsuccessful_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="unsuccessful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Calculate expected success rate
            expected_rate = (successful_count / total_count) * 100

            # Property: Success rate should match expected calculation
            assert abs(row.success_rate - expected_rate) < 0.01, (
                f"SuccessRate should be {expected_rate:.2f}, got {row.success_rate:.2f}"
            )
        finally:
            db_session.close()

    @given(
        session_count=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_total_prompts_equals_total_sessions(
        self,
        session_count: int,
    ):
        """
        **Feature: marketing-reports, Property 4: Success Rate Calculation**
        **Validates: Requirements 2.5**

        For any user, TotalPrompts should equal TotalSessions
        (one prompt per session).
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Create sessions
            for _ in range(session_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=60,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Property: TotalPrompts should equal TotalSessions
            assert row.total_prompts == row.total_sessions, (
                f"TotalPrompts ({row.total_prompts}) should equal "
                f"TotalSessions ({row.total_sessions})"
            )
            assert row.total_sessions == session_count, (
                f"TotalSessions should be {session_count}, got {row.total_sessions}"
            )
        finally:
            db_session.close()

    def test_success_rate_is_zero_for_user_with_no_sessions(self):
        """
        **Feature: marketing-reports, Property 4: Success Rate Calculation**
        **Validates: Requirements 2.10**

        For a user with no sessions, the SuccessRate should be 0.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user with no sessions
            create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Property: Success rate should be 0 for user with no sessions
            assert row.success_rate == 0.0, (
                f"SuccessRate should be 0 for user with no sessions, got {row.success_rate}"
            )
            assert row.total_sessions == 0
            assert row.total_prompts == 0
        finally:
            db_session.close()


class TestAverageCalculations:
    """
    **Feature: marketing-reports, Property 5: Average Calculations**
    **Validates: Requirements 2.9, 2.12**

    Property 5: Average Calculations
    *For any* user with sessions having various tokens_total and
    duration_seconds values, AvgTokens should equal the arithmetic mean
    of tokens_total, and AvgDuration should equal the arithmetic mean
    of duration_seconds.
    """

    @given(
        tokens_list=st.lists(
            st.integers(min_value=1, max_value=100000),
            min_size=1,
            max_size=50,
        ),
        durations_list=st.lists(
            st.integers(min_value=1, max_value=86400),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_average_tokens_calculation(
        self,
        tokens_list: list[int],
        durations_list: list[int],
    ):
        """
        **Feature: marketing-reports, Property 5: Average Calculations**
        **Validates: Requirements 2.9**

        For any user with sessions having various tokens_total values,
        AvgTokens should equal the arithmetic mean of tokens_total.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Use the shorter list length to pair tokens and durations
            session_count = min(len(tokens_list), len(durations_list))

            # Create sessions with the given tokens and durations
            for i in range(session_count):
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=tokens_list[i],
                    duration_seconds=durations_list[i],
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Calculate expected averages
            expected_avg_tokens = sum(tokens_list[:session_count]) / session_count

            # Property: AvgTokens should match expected average
            assert abs(row.avg_tokens - expected_avg_tokens) < 0.01, (
                f"AvgTokens should be {expected_avg_tokens:.2f}, got {row.avg_tokens:.2f}"
            )
        finally:
            db_session.close()

    @given(
        durations_list=st.lists(
            st.integers(min_value=1, max_value=86400),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_average_duration_calculation(
        self,
        durations_list: list[int],
    ):
        """
        **Feature: marketing-reports, Property 5: Average Calculations**
        **Validates: Requirements 2.12**

        For any user with sessions having various duration_seconds values,
        AvgDuration should equal the arithmetic mean of duration_seconds.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user
            user = create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            # Create sessions with the given durations
            for duration in durations_list:
                create_session(
                    db_session,
                    user_id=user.id,
                    optimization_method="CRAFT",
                    status="successful",
                    tokens_total=100,
                    duration_seconds=duration,
                )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Calculate expected average duration
            expected_avg_duration = sum(durations_list) / len(durations_list)

            # Property: AvgDuration should match expected average
            assert abs(row.avg_duration - expected_avg_duration) < 0.01, (
                f"AvgDuration should be {expected_avg_duration:.2f}, got {row.avg_duration:.2f}"
            )
        finally:
            db_session.close()

    def test_averages_are_zero_for_user_with_no_sessions(self):
        """
        **Feature: marketing-reports, Property 5: Average Calculations**
        **Validates: Requirements 2.9, 2.12**

        For a user with no sessions, AvgTokens and AvgDuration should be 0.
        """
        db_session = create_test_db_session()
        mock_email_service = MagicMock()
        report_date = date.today()

        try:
            # Create a user with no sessions
            create_user(
                db_session,
                telegram_id=1000,
                last_interaction_at=datetime.now(UTC),
                email="test@test.com",
            )

            config = ReportConfig(
                generation_time="01:00",
                user_activity_days=0,
                recipient_emails=["test@test.com"],
            )

            service = ReportService(db_session, mock_email_service, config)
            rows, _ = service.generate_user_summary(report_date, include_all_users=True)

            assert len(rows) == 1
            row = rows[0]

            # Property: Averages should be 0 for user with no sessions
            assert row.avg_tokens == 0.0, (
                f"AvgTokens should be 0 for user with no sessions, got {row.avg_tokens}"
            )
            assert row.avg_duration == 0.0, (
                f"AvgDuration should be 0 for user with no sessions, got {row.avg_duration}"
            )
        finally:
            db_session.close()
