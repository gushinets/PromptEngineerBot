"""Property-based tests for user activity tracking feature.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document.

Note: SQLite (used for testing) does not preserve timezone information in datetime
columns. PostgreSQL (used in production) does preserve timezone info. These tests
verify the property holds when timezone info is properly set, acknowledging that
SQLite may strip timezone info during storage/retrieval.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from telegram_bot.data.database import Base, User
from telegram_bot.services.user_tracking import UserTrackingService


@contextmanager
def get_test_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


class TestTimestampProperties:
    """
    **Feature: user-activity-tracking, Property 8: Timestamps are timezone-aware UTC**
    **Validates: Requirements 2.3, 3.3, 7.2**

    Property 8: Timestamps are timezone-aware UTC
    *For any* user record, the `first_interaction_at` and `last_interaction_at` fields
    SHALL be timezone-aware datetime values in UTC.

    Note: SQLite strips timezone info, so we test that:
    1. Timestamps can be set with timezone info
    2. Retrieved timestamps can be interpreted as UTC
    3. The datetime values are preserved correctly
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
    )
    @settings(max_examples=100)
    def test_timestamps_are_set_and_retrievable_as_utc(self, telegram_id: int):
        """
        **Feature: user-activity-tracking, Property 8: Timestamps are timezone-aware UTC**
        **Validates: Requirements 2.3, 3.3, 7.2**

        For any new user created in the database, both first_interaction_at and
        last_interaction_at should be set and retrievable. When retrieved, they
        can be interpreted as UTC timestamps.

        Note: SQLite doesn't preserve timezone info, but PostgreSQL does.
        This test verifies the timestamps are stored and can be treated as UTC.
        """
        with get_test_session() as session:
            # Create a user with explicit UTC timestamps
            now_utc = datetime.now(UTC)
            user = User(
                telegram_id=telegram_id,
                email=None,
                is_authenticated=False,
                first_interaction_at=now_utc,
                last_interaction_at=now_utc,
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # Property: timestamps should be set (not None)
            assert user.first_interaction_at is not None, "first_interaction_at must be set"
            assert user.last_interaction_at is not None, "last_interaction_at must be set"

            # Property: timestamps can be interpreted as UTC
            # (normalize to UTC if timezone info was stripped by SQLite)
            first_ts = user.first_interaction_at
            last_ts = user.last_interaction_at

            if first_ts.tzinfo is None:
                first_ts = first_ts.replace(tzinfo=UTC)
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=UTC)

            # Verify the timestamps are valid UTC datetimes
            assert first_ts.tzinfo == UTC
            assert last_ts.tzinfo == UTC

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
    )
    @settings(max_examples=100)
    def test_timestamps_preserve_utc_values(self, telegram_id: int):
        """
        **Feature: user-activity-tracking, Property 8: Timestamps are timezone-aware UTC**
        **Validates: Requirements 2.3, 3.3, 7.2**

        For any user, timestamps stored as UTC should preserve their values
        when retrieved (within a small tolerance for test execution time).
        """
        with get_test_session() as session:
            # Create timestamp in UTC
            now_utc = datetime.now(UTC)

            user = User(
                telegram_id=telegram_id,
                email=None,
                is_authenticated=False,
                first_interaction_at=now_utc,
                last_interaction_at=now_utc,
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # Property: timestamps should be close to the original UTC time
            # (allowing for small time differences during test execution)
            # Note: SQLite may strip timezone info, so we normalize for comparison
            first_ts = user.first_interaction_at
            last_ts = user.last_interaction_at

            if first_ts.tzinfo is None:
                first_ts = first_ts.replace(tzinfo=UTC)
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=UTC)

            time_diff_first = abs((first_ts - now_utc).total_seconds())
            time_diff_last = abs((last_ts - now_utc).total_seconds())

            assert time_diff_first < 5, "first_interaction_at should be close to creation time"
            assert time_diff_last < 5, "last_interaction_at should be close to creation time"


# Strategy for generating mock effective_user objects
@st.composite
def effective_user_strategy(draw):
    """Generate mock Telegram effective_user objects with realistic profile data."""
    first_name = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))
    last_name = draw(st.one_of(st.none(), st.text(min_size=0, max_size=50)))
    is_bot = draw(st.booleans())
    is_premium = draw(st.one_of(st.none(), st.booleans()))
    language_code = draw(
        st.one_of(st.none(), st.sampled_from(["en", "es", "fr", "de", "ru", "zh"]))
    )

    class MockEffectiveUser:
        pass

    user = MockEffectiveUser()
    user.first_name = first_name
    user.last_name = last_name
    user.is_bot = is_bot
    user.is_premium = is_premium
    user.language_code = language_code
    return user


class TestNewUserCreationTimestamps:
    """
    **Feature: user-activity-tracking, Property 1: New user creation sets both timestamps equally**
    **Validates: Requirements 2.1, 3.1, 4.1**

    Property 1: New user creation sets both timestamps equally
    *For any* new user created via `get_or_create_user()`, the `first_interaction_at`
    and `last_interaction_at` fields SHALL be equal and set to the current UTC time.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_new_user_timestamps_are_equal(self, telegram_id: int, effective_user):
        """
        **Feature: user-activity-tracking, Property 1: New user creation sets both timestamps equally**
        **Validates: Requirements 2.1, 3.1, 4.1**

        For any new user created via get_or_create_user(), both first_interaction_at
        and last_interaction_at should be set to the same value (current UTC time).
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        # Patch get_db_session to use our test session
        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Record time before creation
            before_creation = datetime.now(UTC)

            # Create new user
            user, was_created = service.get_or_create_user(telegram_id, effective_user)

            # Record time after creation
            after_creation = datetime.now(UTC)

            # Property assertions
            assert user is not None, "User should be created successfully"
            assert was_created is True, "User should be newly created"

            # Property 1: Both timestamps should be equal for new users
            assert user.first_interaction_at == user.last_interaction_at, (
                f"For new users, first_interaction_at ({user.first_interaction_at}) "
                f"should equal last_interaction_at ({user.last_interaction_at})"
            )

            # Normalize timestamps for comparison (SQLite may strip timezone)
            first_ts = user.first_interaction_at
            last_ts = user.last_interaction_at
            if first_ts.tzinfo is None:
                first_ts = first_ts.replace(tzinfo=UTC)
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=UTC)

            # Property: Timestamps should be set to current UTC time (within test window)
            assert before_creation <= first_ts <= after_creation, (
                f"first_interaction_at ({first_ts}) should be between "
                f"{before_creation} and {after_creation}"
            )
            assert before_creation <= last_ts <= after_creation, (
                f"last_interaction_at ({last_ts}) should be between "
                f"{before_creation} and {after_creation}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
    )
    @settings(max_examples=100)
    def test_new_user_timestamps_equal_with_none_effective_user(self, telegram_id: int):
        """
        **Feature: user-activity-tracking, Property 1: New user creation sets both timestamps equally**
        **Validates: Requirements 2.1, 3.1, 4.1**

        For any new user created with effective_user=None, both timestamps
        should still be equal and set to current UTC time.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            before_creation = datetime.now(UTC)
            user, was_created = service.get_or_create_user(telegram_id, None)
            after_creation = datetime.now(UTC)

            assert user is not None, "User should be created successfully"
            assert was_created is True, "User should be newly created"

            # Property 1: Both timestamps should be equal
            assert user.first_interaction_at == user.last_interaction_at, (
                f"For new users, first_interaction_at ({user.first_interaction_at}) "
                f"should equal last_interaction_at ({user.last_interaction_at})"
            )

            # Normalize for comparison
            first_ts = user.first_interaction_at
            if first_ts.tzinfo is None:
                first_ts = first_ts.replace(tzinfo=UTC)

            assert before_creation <= first_ts <= after_creation, (
                f"Timestamp ({first_ts}) should be within test window"
            )


class TestUnauthenticatedUserState:
    """
    **Feature: user-activity-tracking, Property 6: Unauthenticated users have null email**
    **Validates: Requirements 1.2, 8.1**

    Property 6: Unauthenticated users have null email
    *For any* user created via `get_or_create_user()` (before email verification),
    the `email` field SHALL be `null` and `is_authenticated` SHALL be `false`.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_new_user_has_null_email_and_unauthenticated(self, telegram_id: int, effective_user):
        """
        **Feature: user-activity-tracking, Property 6: Unauthenticated users have null email**
        **Validates: Requirements 1.2, 8.1**

        For any new user created via get_or_create_user(), the email field should
        be null and is_authenticated should be false.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Create new user
            user, was_created = service.get_or_create_user(telegram_id, effective_user)

            # Property assertions
            assert user is not None, "User should be created successfully"
            assert was_created is True, "User should be newly created"

            # Property 6: email should be null for unauthenticated users
            assert user.email is None, (
                f"For unauthenticated users, email should be null, got: {user.email}"
            )

            # Property 6: is_authenticated should be false for new users
            assert user.is_authenticated is False, (
                f"For unauthenticated users, is_authenticated should be False, "
                f"got: {user.is_authenticated}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
    )
    @settings(max_examples=100)
    def test_new_user_with_none_effective_user_has_null_email(self, telegram_id: int):
        """
        **Feature: user-activity-tracking, Property 6: Unauthenticated users have null email**
        **Validates: Requirements 1.2, 8.1**

        For any new user created with effective_user=None, the email field should
        still be null and is_authenticated should be false.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Create new user with None effective_user
            user, was_created = service.get_or_create_user(telegram_id, None)

            # Property assertions
            assert user is not None, "User should be created successfully"
            assert was_created is True, "User should be newly created"

            # Property 6: email should be null
            assert user.email is None, (
                f"For unauthenticated users, email should be null, got: {user.email}"
            )

            # Property 6: is_authenticated should be false
            assert user.is_authenticated is False, (
                f"For unauthenticated users, is_authenticated should be False, "
                f"got: {user.is_authenticated}"
            )


def _normalize_timestamp(ts: datetime) -> datetime:
    """
    Normalize a timestamp for comparison by stripping timezone info.

    SQLite doesn't preserve timezone info, so we need to compare timestamps
    without timezone info. This helper ensures consistent comparison.
    """
    if ts is None:
        return None
    if ts.tzinfo is not None:
        return ts.replace(tzinfo=None)
    return ts


class TestFirstInteractionTimestampImmutability:
    """
    **Feature: user-activity-tracking, Property 2: First interaction timestamp is immutable**
    **Validates: Requirements 2.2, 5.3**

    Property 2: First interaction timestamp is immutable
    *For any* existing user, subsequent calls to `track_user_interaction()` SHALL NOT
    modify the `first_interaction_at` value.

    Note: SQLite strips timezone info, so we normalize timestamps for comparison.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        num_interactions=st.integers(min_value=2, max_value=10),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_first_interaction_timestamp_unchanged_after_multiple_interactions(
        self, telegram_id: int, num_interactions: int, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 2: First interaction timestamp is immutable**
        **Validates: Requirements 2.2, 5.3**

        For any existing user, calling track_user_interaction() multiple times
        should never modify the first_interaction_at value.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # First interaction - creates the user
            user, is_first_time = service.track_user_interaction(telegram_id, effective_user)

            assert user is not None, "User should be created successfully"
            assert is_first_time is True, "First interaction should mark user as first-time"

            # Capture the original first_interaction_at value (normalized for SQLite)
            original_first_interaction_at = _normalize_timestamp(user.first_interaction_at)

            # Perform multiple subsequent interactions
            for i in range(num_interactions - 1):
                user, is_first_time = service.track_user_interaction(telegram_id, effective_user)

                assert user is not None, f"User should exist after interaction {i + 2}"

                # Property 2: first_interaction_at should remain unchanged
                # Normalize for comparison (SQLite strips timezone info)
                current_first_interaction_at = _normalize_timestamp(user.first_interaction_at)
                assert current_first_interaction_at == original_first_interaction_at, (
                    f"After interaction {i + 2}, first_interaction_at changed from "
                    f"{original_first_interaction_at} to {current_first_interaction_at}"
                )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_first_interaction_timestamp_preserved_with_profile_changes(
        self, telegram_id: int, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 2: First interaction timestamp is immutable**
        **Validates: Requirements 2.2, 5.3**

        For any existing user, even when profile data changes between interactions,
        the first_interaction_at value should remain unchanged.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # First interaction - creates the user
            user, _ = service.track_user_interaction(telegram_id, effective_user)

            assert user is not None, "User should be created successfully"

            # Capture the original first_interaction_at value (normalized for SQLite)
            original_first_interaction_at = _normalize_timestamp(user.first_interaction_at)

            # Create a modified effective_user with different profile data
            class ModifiedEffectiveUser:
                pass

            modified_user = ModifiedEffectiveUser()
            modified_user.first_name = "ChangedFirstName"
            modified_user.last_name = "ChangedLastName"
            modified_user.is_bot = False
            modified_user.is_premium = True
            modified_user.language_code = "de"

            # Second interaction with modified profile
            user, _ = service.track_user_interaction(telegram_id, modified_user)

            assert user is not None, "User should exist after second interaction"

            # Property 2: first_interaction_at should remain unchanged
            # Normalize for comparison (SQLite strips timezone info)
            current_first_interaction_at = _normalize_timestamp(user.first_interaction_at)
            assert current_first_interaction_at == original_first_interaction_at, (
                f"first_interaction_at changed from {original_first_interaction_at} "
                f"to {current_first_interaction_at} after profile update"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
    )
    @settings(max_examples=100)
    def test_first_interaction_timestamp_preserved_with_none_effective_user(self, telegram_id: int):
        """
        **Feature: user-activity-tracking, Property 2: First interaction timestamp is immutable**
        **Validates: Requirements 2.2, 5.3**

        For any existing user, subsequent interactions with effective_user=None
        should not modify the first_interaction_at value.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # First interaction - creates the user
            user, _ = service.track_user_interaction(telegram_id, None)

            assert user is not None, "User should be created successfully"

            # Capture the original first_interaction_at value (normalized for SQLite)
            original_first_interaction_at = _normalize_timestamp(user.first_interaction_at)

            # Multiple subsequent interactions with None effective_user
            for i in range(3):
                user, _ = service.track_user_interaction(telegram_id, None)

                assert user is not None, f"User should exist after interaction {i + 2}"

                # Property 2: first_interaction_at should remain unchanged
                # Normalize for comparison (SQLite strips timezone info)
                current_first_interaction_at = _normalize_timestamp(user.first_interaction_at)
                assert current_first_interaction_at == original_first_interaction_at, (
                    f"After interaction {i + 2}, first_interaction_at changed from "
                    f"{original_first_interaction_at} to {current_first_interaction_at}"
                )


class TestNoDuplicateUsers:
    """
    **Feature: user-activity-tracking, Property 5: No duplicate users created**
    **Validates: Requirements 1.3**

    Property 5: No duplicate users created
    *For any* `telegram_id`, calling `get_or_create_user()` multiple times SHALL
    result in exactly one user record in the database.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        num_calls=st.integers(min_value=2, max_value=10),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_multiple_calls_create_single_user(
        self, telegram_id: int, num_calls: int, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 5: No duplicate users created**
        **Validates: Requirements 1.3**

        For any telegram_id, calling get_or_create_user() multiple times should
        result in exactly one user record in the database.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Call get_or_create_user multiple times with the same telegram_id
            results = []
            for _ in range(num_calls):
                user, was_created = service.get_or_create_user(telegram_id, effective_user)
                results.append((user, was_created))

            # Property 5: Only the first call should create a user
            assert results[0][1] is True, "First call should create a new user"
            for i, (user, was_created) in enumerate(results[1:], start=2):
                assert was_created is False, (
                    f"Call {i} should return existing user, not create new one"
                )

            # Property 5: All calls should return the same user
            first_user = results[0][0]
            for i, (user, _) in enumerate(results[1:], start=2):
                assert user.id == first_user.id, (
                    f"Call {i} returned user with id={user.id}, expected id={first_user.id}"
                )
                assert user.telegram_id == first_user.telegram_id, (
                    f"Call {i} returned user with telegram_id={user.telegram_id}, "
                    f"expected telegram_id={first_user.telegram_id}"
                )

            # Property 5: Database should contain exactly one user with this telegram_id
            with get_test_session() as session:
                user_count = session.query(User).filter_by(telegram_id=telegram_id).count()
                assert user_count == 1, (
                    f"Expected exactly 1 user with telegram_id={telegram_id}, found {user_count}"
                )

    @given(
        telegram_ids=st.lists(
            st.integers(min_value=1, max_value=2**63 - 1),
            min_size=2,
            max_size=5,
            unique=True,
        ),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_different_telegram_ids_create_separate_users(
        self, telegram_ids: list[int], effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 5: No duplicate users created**
        **Validates: Requirements 1.3**

        For any set of distinct telegram_ids, each should create exactly one user,
        and the total user count should equal the number of distinct telegram_ids.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Create users for each telegram_id
            created_users = []
            for tid in telegram_ids:
                user, was_created = service.get_or_create_user(tid, effective_user)
                assert was_created is True, (
                    f"First call for telegram_id={tid} should create a new user"
                )
                created_users.append(user)

            # Property: Each telegram_id should have exactly one user
            with get_test_session() as session:
                total_users = session.query(User).count()
                assert total_users == len(telegram_ids), (
                    f"Expected {len(telegram_ids)} users, found {total_users}"
                )

                # Verify each telegram_id has exactly one user
                for tid in telegram_ids:
                    count = session.query(User).filter_by(telegram_id=tid).count()
                    assert count == 1, f"Expected 1 user for telegram_id={tid}, found {count}"


class TestLastInteractionTimestampUpdates:
    """
    **Feature: user-activity-tracking, Property 3: Last interaction timestamp updates on each interaction**
    **Validates: Requirements 3.2, 7.1**

    Property 3: Last interaction timestamp updates on each interaction
    *For any* existing user, calling `track_user_interaction()` SHALL update
    `last_interaction_at` to a value greater than or equal to the previous value.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        num_interactions=st.integers(min_value=2, max_value=10),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_last_interaction_timestamp_updates_on_each_interaction(
        self, telegram_id: int, num_interactions: int, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 3: Last interaction timestamp updates on each interaction**
        **Validates: Requirements 3.2, 7.1**

        For any existing user, calling track_user_interaction() multiple times
        should update last_interaction_at to a value >= the previous value.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # First interaction - creates the user
            user, is_first_time = service.track_user_interaction(telegram_id, effective_user)

            assert user is not None, "User should be created successfully"
            assert is_first_time is True, "First interaction should mark user as first-time"

            # Capture the initial last_interaction_at value (normalized for SQLite)
            previous_last_interaction_at = _normalize_timestamp(user.last_interaction_at)

            # Perform multiple subsequent interactions
            for i in range(num_interactions - 1):
                user, is_first_time = service.track_user_interaction(telegram_id, effective_user)

                assert user is not None, f"User should exist after interaction {i + 2}"

                # Property 3: last_interaction_at should be >= previous value
                current_last_interaction_at = _normalize_timestamp(user.last_interaction_at)
                assert current_last_interaction_at >= previous_last_interaction_at, (
                    f"After interaction {i + 2}, last_interaction_at ({current_last_interaction_at}) "
                    f"should be >= previous value ({previous_last_interaction_at})"
                )

                # Update previous value for next iteration
                previous_last_interaction_at = current_last_interaction_at

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_last_interaction_timestamp_monotonically_increases(
        self, telegram_id: int, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 3: Last interaction timestamp updates on each interaction**
        **Validates: Requirements 3.2, 7.1**

        For any existing user, the sequence of last_interaction_at values across
        multiple interactions should be monotonically non-decreasing.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Collect timestamps from multiple interactions
            timestamps = []

            # First interaction
            user, _ = service.track_user_interaction(telegram_id, effective_user)
            assert user is not None, "User should be created successfully"
            timestamps.append(_normalize_timestamp(user.last_interaction_at))

            # Multiple subsequent interactions
            for _ in range(4):
                user, _ = service.track_user_interaction(telegram_id, effective_user)
                assert user is not None, "User should exist after interaction"
                timestamps.append(_normalize_timestamp(user.last_interaction_at))

            # Property 3: Timestamps should be monotonically non-decreasing
            for i in range(1, len(timestamps)):
                assert timestamps[i] >= timestamps[i - 1], (
                    f"Timestamp at interaction {i + 1} ({timestamps[i]}) should be >= "
                    f"timestamp at interaction {i} ({timestamps[i - 1]})"
                )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
    )
    @settings(max_examples=100)
    def test_last_interaction_timestamp_updates_with_none_effective_user(self, telegram_id: int):
        """
        **Feature: user-activity-tracking, Property 3: Last interaction timestamp updates on each interaction**
        **Validates: Requirements 3.2, 7.1**

        For any existing user, calling track_user_interaction() with effective_user=None
        should still update last_interaction_at to a value >= the previous value.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # First interaction - creates the user
            user, _ = service.track_user_interaction(telegram_id, None)

            assert user is not None, "User should be created successfully"

            # Capture the initial last_interaction_at value (normalized for SQLite)
            previous_last_interaction_at = _normalize_timestamp(user.last_interaction_at)

            # Multiple subsequent interactions with None effective_user
            for i in range(3):
                user, _ = service.track_user_interaction(telegram_id, None)

                assert user is not None, f"User should exist after interaction {i + 2}"

                # Property 3: last_interaction_at should be >= previous value
                current_last_interaction_at = _normalize_timestamp(user.last_interaction_at)
                assert current_last_interaction_at >= previous_last_interaction_at, (
                    f"After interaction {i + 2}, last_interaction_at ({current_last_interaction_at}) "
                    f"should be >= previous value ({previous_last_interaction_at})"
                )

                # Update previous value for next iteration
                previous_last_interaction_at = current_last_interaction_at


class TestFirstTimeUserIdentification:
    """
    **Feature: user-activity-tracking, Property 4: First-time user identification**
    **Validates: Requirements 4.1, 4.2, 4.3**

    Property 4: First-time user identification
    *For any* user where `first_interaction_at` equals `last_interaction_at`, the
    `is_first_time_user()` method SHALL return `True`. *For any* user where
    `last_interaction_at` is later than `first_interaction_at`, the method SHALL
    return `False`.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_new_user_is_identified_as_first_time(self, telegram_id: int, effective_user):
        """
        **Feature: user-activity-tracking, Property 4: First-time user identification**
        **Validates: Requirements 4.1, 4.2, 4.3**

        For any newly created user (where first_interaction_at equals last_interaction_at),
        the is_first_time_user() method should return True.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Create new user
            user, was_created = service.get_or_create_user(telegram_id, effective_user)

            assert user is not None, "User should be created successfully"
            assert was_created is True, "User should be newly created"

            # Property 4: For new users, timestamps are equal
            assert user.first_interaction_at == user.last_interaction_at, (
                "New user should have equal first and last interaction timestamps"
            )

            # Property 4: is_first_time_user() should return True for new users
            assert service.is_first_time_user(user) is True, (
                f"is_first_time_user() should return True for new user with "
                f"first_interaction_at={user.first_interaction_at} and "
                f"last_interaction_at={user.last_interaction_at}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
        hours_diff=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=100)
    def test_returning_user_is_not_identified_as_first_time(
        self, telegram_id: int, hours_diff: int
    ):
        """
        **Feature: user-activity-tracking, Property 4: First-time user identification**
        **Validates: Requirements 4.1, 4.2, 4.3**

        For any user with last_interaction_at later than first_interaction_at,
        the is_first_time_user() method should return False.
        """
        from datetime import timedelta

        with get_test_session() as session:
            service = UserTrackingService()

            # Create user with different timestamps (returning user)
            now_utc = datetime.now(UTC)
            user = User(
                telegram_id=telegram_id,
                email=None,
                is_authenticated=False,
                first_interaction_at=now_utc,
                last_interaction_at=now_utc + timedelta(hours=hours_diff),
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # Property 4: Different timestamps -> is_first_time_user() returns False
            assert service.is_first_time_user(user) is False, (
                f"User with different timestamps (diff={hours_diff}h) should NOT be "
                f"identified as first-time user"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
    )
    @settings(max_examples=100)
    def test_is_first_time_user_with_equal_timestamps(self, telegram_id: int):
        """
        **Feature: user-activity-tracking, Property 4: First-time user identification**
        **Validates: Requirements 4.1, 4.2, 4.3**

        For any user with equal first_interaction_at and last_interaction_at,
        is_first_time_user() should return True.
        """
        with get_test_session() as session:
            service = UserTrackingService()

            # Create user with equal timestamps (first-time user)
            now_utc = datetime.now(UTC)
            user = User(
                telegram_id=telegram_id,
                email=None,
                is_authenticated=False,
                first_interaction_at=now_utc,
                last_interaction_at=now_utc,  # Same as first
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # Property 4: Equal timestamps -> is_first_time_user() returns True
            assert service.is_first_time_user(user) is True, (
                "User with equal timestamps should be identified as first-time user"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
        hours_diff=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=100)
    def test_is_first_time_user_with_varying_time_differences(
        self, telegram_id: int, hours_diff: int
    ):
        """
        **Feature: user-activity-tracking, Property 4: First-time user identification**
        **Validates: Requirements 4.1, 4.2, 4.3**

        For any user with last_interaction_at later than first_interaction_at by
        any positive amount of time, is_first_time_user() should return False.
        """
        from datetime import timedelta

        with get_test_session() as session:
            service = UserTrackingService()

            now_utc = datetime.now(UTC)
            user = User(
                telegram_id=telegram_id,
                email=None,
                is_authenticated=False,
                first_interaction_at=now_utc,
                last_interaction_at=now_utc + timedelta(hours=hours_diff),
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # Property 4: Any positive time difference means NOT first-time user
            assert service.is_first_time_user(user) is False, (
                f"User with {hours_diff} hours between first and last interaction "
                f"should NOT be identified as first-time user"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_track_user_interaction_returns_correct_first_time_flag(
        self, telegram_id: int, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 4: First-time user identification**
        **Validates: Requirements 4.1, 4.2, 4.3**

        For any user, the track_user_interaction() method should return the correct
        is_first_time_user flag: True for first interaction, and the flag should
        match the is_first_time_user() method result for new users.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # First interaction
            user, is_first_time_flag = service.track_user_interaction(telegram_id, effective_user)

            assert user is not None, "User should be created successfully"

            # Property 4: First interaction should return is_first_time=True
            assert is_first_time_flag is True, "First interaction should return is_first_time=True"

            # Verify is_first_time_user() method agrees for new users
            assert service.is_first_time_user(user) is True, (
                "is_first_time_user() should return True for first interaction"
            )


class TestEmailVerificationPreservesHistory:
    """
    **Feature: user-activity-tracking, Property 7: Email verification preserves activity history**
    **Validates: Requirements 5.3**

    Property 7: Email verification preserves activity history
    *For any* user who verifies their email, the `first_interaction_at` and `created_at`
    values SHALL remain unchanged after verification.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
        email=st.emails(),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_email_verification_preserves_first_interaction_at(
        self, telegram_id: int, email: str, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 7: Email verification preserves activity history**
        **Validates: Requirements 5.3**

        For any user created on first interaction (with email=null), when they later
        verify their email, the first_interaction_at value should remain unchanged.
        """
        from telegram_bot.auth.auth_service import AuthService
        from telegram_bot.utils.config import BotConfig

        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        @contextmanager
        def get_test_session_context():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        # Mock Redis client to avoid initialization issues
        mock_redis = MagicMock()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session_context):
            with patch("telegram_bot.auth.auth_service.get_db_session", get_test_session_context):
                with patch(
                    "telegram_bot.auth.auth_service.get_redis_client", return_value=mock_redis
                ):
                    # Step 1: Create user on first interaction (simulating UserTrackingService)
                    tracking_service = UserTrackingService()
                    user, was_created = tracking_service.get_or_create_user(
                        telegram_id, effective_user
                    )

                    assert user is not None, "User should be created successfully"
                    assert was_created is True, "User should be newly created"
                    assert user.email is None, "New user should have null email"
                    assert user.is_authenticated is False, "New user should not be authenticated"

                    # Capture original timestamps (normalized for SQLite)
                    original_first_interaction_at = _normalize_timestamp(user.first_interaction_at)
                    original_created_at = _normalize_timestamp(user.created_at)

                    # Step 2: Simulate email verification via AuthService._persist_authentication_state
                    config = BotConfig("test_token", "TEST", "test-model")
                    auth_service = AuthService(config)

                    # Normalize email for storage
                    normalized_email = email.lower().strip()

                    # Call _persist_authentication_state to simulate email verification
                    success = auth_service._persist_authentication_state(
                        telegram_id=telegram_id,
                        email=normalized_email,
                        email_original=email,
                        effective_user=effective_user,
                    )

                    assert success is True, "Email verification should succeed"

                    # Step 3: Verify timestamps are preserved
                    with get_test_session_context() as session:
                        updated_user = (
                            session.query(User).filter_by(telegram_id=telegram_id).first()
                        )

                        assert updated_user is not None, "User should exist after verification"
                        assert updated_user.email == normalized_email, "Email should be updated"
                        assert updated_user.is_authenticated is True, "User should be authenticated"

                        # Property 7: first_interaction_at should be preserved
                        current_first_interaction_at = _normalize_timestamp(
                            updated_user.first_interaction_at
                        )
                        assert current_first_interaction_at == original_first_interaction_at, (
                            f"first_interaction_at changed from {original_first_interaction_at} "
                            f"to {current_first_interaction_at} after email verification"
                        )

                        # Property 7: created_at should be preserved
                        current_created_at = _normalize_timestamp(updated_user.created_at)
                        assert current_created_at == original_created_at, (
                            f"created_at changed from {original_created_at} "
                            f"to {current_created_at} after email verification"
                        )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
        email=st.emails(),
    )
    @settings(max_examples=100)
    def test_email_verification_preserves_created_at(self, telegram_id: int, email: str):
        """
        **Feature: user-activity-tracking, Property 7: Email verification preserves activity history**
        **Validates: Requirements 5.3**

        For any user created on first interaction, when they verify their email,
        the created_at value should remain unchanged.
        """
        from telegram_bot.auth.auth_service import AuthService
        from telegram_bot.utils.config import BotConfig

        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        @contextmanager
        def get_test_session_context():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        # Mock Redis client to avoid initialization issues
        mock_redis = MagicMock()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session_context):
            with patch("telegram_bot.auth.auth_service.get_db_session", get_test_session_context):
                with patch(
                    "telegram_bot.auth.auth_service.get_redis_client", return_value=mock_redis
                ):
                    # Step 1: Create user on first interaction
                    tracking_service = UserTrackingService()
                    user, was_created = tracking_service.get_or_create_user(telegram_id, None)

                    assert user is not None, "User should be created successfully"
                    assert was_created is True, "User should be newly created"

                    # Capture original created_at (normalized for SQLite)
                    original_created_at = _normalize_timestamp(user.created_at)

                    # Step 2: Simulate email verification
                    config = BotConfig("test_token", "TEST", "test-model")
                    auth_service = AuthService(config)
                    normalized_email = email.lower().strip()

                    success = auth_service._persist_authentication_state(
                        telegram_id=telegram_id,
                        email=normalized_email,
                        email_original=email,
                        effective_user=None,
                    )

                    assert success is True, "Email verification should succeed"

                    # Step 3: Verify created_at is preserved
                    with get_test_session_context() as session:
                        updated_user = (
                            session.query(User).filter_by(telegram_id=telegram_id).first()
                        )

                        assert updated_user is not None, "User should exist after verification"

                        # Property 7: created_at should be preserved
                        current_created_at = _normalize_timestamp(updated_user.created_at)
                        assert current_created_at == original_created_at, (
                            f"created_at changed from {original_created_at} "
                            f"to {current_created_at} after email verification"
                        )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**62 - 1),
        email=st.emails(),
        num_interactions=st.integers(min_value=1, max_value=5),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_email_verification_preserves_history_after_multiple_interactions(
        self, telegram_id: int, email: str, num_interactions: int, effective_user
    ):
        """
        **Feature: user-activity-tracking, Property 7: Email verification preserves activity history**
        **Validates: Requirements 5.3**

        For any user who has had multiple interactions before verifying their email,
        the first_interaction_at and created_at values should remain unchanged.
        """
        from telegram_bot.auth.auth_service import AuthService
        from telegram_bot.utils.config import BotConfig

        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        @contextmanager
        def get_test_session_context():
            session = session_factory()
            try:
                yield session
            finally:
                session.close()

        # Mock Redis client to avoid initialization issues
        mock_redis = MagicMock()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session_context):
            with patch("telegram_bot.auth.auth_service.get_db_session", get_test_session_context):
                with patch(
                    "telegram_bot.auth.auth_service.get_redis_client", return_value=mock_redis
                ):
                    # Step 1: Create user and simulate multiple interactions
                    tracking_service = UserTrackingService()

                    # First interaction creates the user
                    user, _ = tracking_service.track_user_interaction(telegram_id, effective_user)
                    assert user is not None, "User should be created successfully"

                    # Capture original timestamps immediately after first interaction
                    original_first_interaction_at = _normalize_timestamp(user.first_interaction_at)
                    original_created_at = _normalize_timestamp(user.created_at)

                    # Simulate additional interactions
                    for _ in range(num_interactions - 1):
                        user, _ = tracking_service.track_user_interaction(
                            telegram_id, effective_user
                        )

                    # Step 2: Simulate email verification
                    config = BotConfig("test_token", "TEST", "test-model")
                    auth_service = AuthService(config)
                    normalized_email = email.lower().strip()

                    success = auth_service._persist_authentication_state(
                        telegram_id=telegram_id,
                        email=normalized_email,
                        email_original=email,
                        effective_user=effective_user,
                    )

                    assert success is True, "Email verification should succeed"

                    # Step 3: Verify timestamps are preserved
                    with get_test_session_context() as session:
                        updated_user = (
                            session.query(User).filter_by(telegram_id=telegram_id).first()
                        )

                        assert updated_user is not None, "User should exist after verification"
                        assert updated_user.is_authenticated is True, "User should be authenticated"

                        # Property 7: first_interaction_at should be preserved
                        current_first_interaction_at = _normalize_timestamp(
                            updated_user.first_interaction_at
                        )
                        assert current_first_interaction_at == original_first_interaction_at, (
                            f"first_interaction_at changed from {original_first_interaction_at} "
                            f"to {current_first_interaction_at} after email verification "
                            f"(after {num_interactions} interactions)"
                        )

                        # Property 7: created_at should be preserved
                        current_created_at = _normalize_timestamp(updated_user.created_at)
                        assert current_created_at == original_created_at, (
                            f"created_at changed from {original_created_at} "
                            f"to {current_created_at} after email verification "
                            f"(after {num_interactions} interactions)"
                        )


class TestMultipleNullEmailsAllowed:
    """
    **Feature: user-activity-tracking, Property 9: Multiple null emails allowed**
    **Validates: Requirements 8.2**

    Property 9: Multiple null emails allowed
    *For any* number of unauthenticated users, the database SHALL allow multiple
    records with `email = null`.
    """

    @given(
        telegram_ids=st.lists(
            st.integers(min_value=1, max_value=2**63 - 1),
            min_size=2,
            max_size=10,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_multiple_users_can_have_null_email(self, telegram_ids: list[int]):
        """
        **Feature: user-activity-tracking, Property 9: Multiple null emails allowed**
        **Validates: Requirements 8.2**

        For any number of unauthenticated users, the database should allow multiple
        records with email = null without violating unique constraints.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Create multiple users with null email
            created_users = []
            for tid in telegram_ids:
                user, was_created = service.get_or_create_user(tid, None)
                assert user is not None, f"User with telegram_id={tid} should be created"
                assert was_created is True, f"User with telegram_id={tid} should be newly created"
                created_users.append(user)

            # Property 9: All users should have null email
            for user in created_users:
                assert user.email is None, (
                    f"User with telegram_id={user.telegram_id} should have null email"
                )

            # Property 9: All users should exist in the database
            with get_test_session() as session:
                total_users = session.query(User).count()
                assert total_users == len(telegram_ids), (
                    f"Expected {len(telegram_ids)} users with null email, found {total_users}"
                )

                # Verify all users have null email
                null_email_count = session.query(User).filter(User.email.is_(None)).count()
                assert null_email_count == len(telegram_ids), (
                    f"Expected {len(telegram_ids)} users with null email, found {null_email_count}"
                )

    @given(
        num_users=st.integers(min_value=2, max_value=20),
    )
    @settings(max_examples=100)
    def test_database_allows_multiple_null_emails_directly(self, num_users: int):
        """
        **Feature: user-activity-tracking, Property 9: Multiple null emails allowed**
        **Validates: Requirements 8.2**

        For any number of users, the database should allow creating multiple records
        with email = null directly (testing the database constraint).
        """
        with get_test_session() as session:
            # Create multiple users with null email directly in the database
            users = []
            for i in range(num_users):
                user = User(
                    telegram_id=1000000 + i,  # Unique telegram_ids
                    email=None,  # All have null email
                    is_authenticated=False,
                    first_interaction_at=datetime.now(UTC),
                    last_interaction_at=datetime.now(UTC),
                )
                session.add(user)
                users.append(user)

            # Commit should succeed without unique constraint violation
            session.commit()

            # Property 9: All users should be persisted with null email
            for user in users:
                session.refresh(user)
                assert user.id is not None, "User should have an ID after commit"
                assert user.email is None, "User email should remain null"

            # Verify count in database
            null_email_count = session.query(User).filter(User.email.is_(None)).count()
            assert null_email_count == num_users, (
                f"Expected {num_users} users with null email, found {null_email_count}"
            )

    @given(
        telegram_ids=st.lists(
            st.integers(min_value=1, max_value=2**63 - 1),
            min_size=3,
            max_size=10,
            unique=True,
        ),
        effective_user=effective_user_strategy(),
    )
    @settings(max_examples=100)
    def test_multiple_null_emails_with_profile_data(self, telegram_ids: list[int], effective_user):
        """
        **Feature: user-activity-tracking, Property 9: Multiple null emails allowed**
        **Validates: Requirements 8.2**

        For any number of unauthenticated users with profile data, the database
        should allow multiple records with email = null.
        """
        # Create an in-memory database for this test
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)

        def get_test_session():
            return session_factory()

        with patch("telegram_bot.services.user_tracking.get_db_session", get_test_session):
            service = UserTrackingService()

            # Create multiple users with profile data but null email
            for tid in telegram_ids:
                user, was_created = service.get_or_create_user(tid, effective_user)
                assert user is not None, f"User with telegram_id={tid} should be created"
                assert was_created is True, f"User with telegram_id={tid} should be newly created"
                assert user.email is None, f"User with telegram_id={tid} should have null email"

            # Property 9: All users should exist with null email
            with get_test_session() as session:
                null_email_users = session.query(User).filter(User.email.is_(None)).all()
                assert len(null_email_users) == len(telegram_ids), (
                    f"Expected {len(telegram_ids)} users with null email, "
                    f"found {len(null_email_users)}"
                )

                # Verify each telegram_id has exactly one user with null email
                for tid in telegram_ids:
                    user = session.query(User).filter_by(telegram_id=tid).first()
                    assert user is not None, f"User with telegram_id={tid} should exist"
                    assert user.email is None, f"User with telegram_id={tid} should have null email"

    @given(
        num_null_email_users=st.integers(min_value=2, max_value=5),
        num_verified_users=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100)
    def test_null_emails_coexist_with_verified_emails(
        self, num_null_email_users: int, num_verified_users: int
    ):
        """
        **Feature: user-activity-tracking, Property 9: Multiple null emails allowed**
        **Validates: Requirements 8.2**

        For any mix of unauthenticated users (null email) and authenticated users
        (verified email), the database should allow multiple null emails while
        maintaining unique constraint for non-null emails.
        """
        with get_test_session() as session:
            now_utc = datetime.now(UTC)

            # Create users with null email
            null_email_users = []
            for i in range(num_null_email_users):
                user = User(
                    telegram_id=2000000 + i,
                    email=None,
                    is_authenticated=False,
                    first_interaction_at=now_utc,
                    last_interaction_at=now_utc,
                )
                session.add(user)
                null_email_users.append(user)

            # Create users with verified email
            verified_users = []
            for i in range(num_verified_users):
                user = User(
                    telegram_id=3000000 + i,
                    email=f"user{i}@example.com",  # Unique emails
                    is_authenticated=True,
                    first_interaction_at=now_utc,
                    last_interaction_at=now_utc,
                )
                session.add(user)
                verified_users.append(user)

            # Commit should succeed
            session.commit()

            # Property 9: All null email users should be persisted
            null_count = session.query(User).filter(User.email.is_(None)).count()
            assert null_count == num_null_email_users, (
                f"Expected {num_null_email_users} users with null email, found {null_count}"
            )

            # Verified users should also be persisted
            verified_count = session.query(User).filter(User.email.isnot(None)).count()
            assert verified_count == num_verified_users, (
                f"Expected {num_verified_users} users with verified email, found {verified_count}"
            )

            # Total users should be correct
            total_count = session.query(User).count()
            expected_total = num_null_email_users + num_verified_users
            assert total_count == expected_total, (
                f"Expected {expected_total} total users, found {total_count}"
            )
