# Design Document

## Overview

This design document outlines the technical architecture for implementing email-based authentication and prompt delivery functionality in the Telegram bot. The system will add a new user flow where users can authenticate via email OTP and receive optimized prompts from all three methods (CRAFT, LYRA, GGL) directly in their inbox.

The design follows a modular approach, integrating with existing bot components while adding new layers for authentication, email services, and database management. The system uses Redis for temporary OTP storage, SQLAlchemy for persistent data, and SMTP for email delivery.

## Architecture

### Project Structure (Hybrid Approach)

```
src/
├── bot_handler.py          # ✅ Extended: Add email flow handlers
├── config.py               # ✅ Extended: Add email/DB/Redis config
├── main.py                 # ✅ Keep existing
├── messages.py             # ✅ Extended: Add email button
├── conversation_manager.py # ✅ Keep existing
├── state_manager.py        # ✅ Keep existing
├── [other existing files]  # ✅ Keep all existing files
│
├── auth_service.py         # 🆕 New: Authentication & OTP logic
├── email_service.py        # 🆕 New: Email sending functionality
├── email_templates.py      # 🆕 New: Email templates
├── database.py             # 🆕 New: SQLAlchemy models & connection
├── redis_client.py         # 🆕 New: Redis operations
├── email_flow.py           # 🆕 New: Email workflow orchestration
├── health_checks.py        # 🆕 New: Health monitoring & alerting
├── metrics.py              # 🆕 New: Metrics collection & observability
└── audit_service.py        # 🆕 New: Audit logging & event purging

alembic/                    # 🆕 New: Database migrations
├── versions/
├── env.py
└── script.py.mako

tests/
├── [existing test files]   # ✅ Keep all existing
├── test_auth_service.py    # 🆕 New: Auth service tests
├── test_email_service.py   # 🆕 New: Email service tests
├── test_database.py        # 🆕 New: Database tests
├── test_health_checks.py   # 🆕 New: Health monitoring tests
├── test_metrics.py         # 🆕 New: Metrics collection tests
├── test_audit_service.py   # 🆕 New: Audit service tests
└── test_email_flow_integration.py # 🆕 New: Integration tests
```

### High-Level Architecture

```mermaid
graph TB
    subgraph "Telegram Bot Layer"
        BH[bot_handler.py<br/>Extended]
        MSG[messages.py<br/>Extended]
        CFG[config.py<br/>Extended]
    end
    
    subgraph "New Email Feature Layer"
        EF[email_flow.py<br/>Orchestrator]
        AS[auth_service.py<br/>OTP & Auth]
        ES[email_service.py<br/>SMTP Client]
        ET[email_templates.py<br/>Templates]
    end
    
    subgraph "Data Layer"
        DB[database.py<br/>SQLAlchemy Models]
        RC[redis_client.py<br/>OTP Storage]
    end
    
    subgraph "External Services"
        SMTP[SMTP-Pulse<br/>Email Provider]
        REDIS[Redis<br/>Cache]
        PGDB[(PostgreSQL/SQLite<br/>Database)]
    end
    
    subgraph "Existing Features"
        CM[conversation_manager.py]
        SM[state_manager.py]
        OPT[Optimization Methods<br/>CRAFT, LYRA, GGL]
    end
    
    BH --> EF
    EF --> AS
    EF --> ES
    EF --> OPT
    AS --> RC
    ES --> ET
    ES --> SMTP
    RC --> REDIS
    DB --> PGDB
    CFG --> AS
    CFG --> ES
    CFG --> DB
    
    style EF fill:#e1f5fe
    style AS fill:#e8f5e8
    style ES fill:#fff3e0
    style DB fill:#f3e5f5
```

### Component Flow

1. **User Input** → Bot Handler → Auth Service
2. **OTP Generation** → Redis Storage → Email Service
3. **Verification** → Database Update → Direct Optimization
4. **Optimization** → Email Delivery → Audit Logging

## Components and Interfaces

### 1. Database Layer

#### File: `src/database.py` (New)
- SQLAlchemy models for User and AuthEvent tables
- Database connection factory with SQLite/PostgreSQL support
- Session management and ORM operations

#### File: `alembic/` (New Directory)
- Migration scripts directory
- Schema evolution management

#### File: `alembic.ini` (New)
- Alembic configuration file

### 2. Authentication Service

#### File: `src/auth_service.py` (New)
- Core authentication logic
- OTP generation and verification
- Rate limiting implementation
- Integration with Redis for temporary storage

#### File: `src/redis_client.py` (New)
- Redis connection and operations
- OTP storage and retrieval with TTL
- Rate limiting counters

### 3. Email Service

#### File: `src/email_service.py` (New)
- SMTP email sending logic using SMTP-Pulse
- Email composition and HTML formatting
- Connection management and error handling

#### File: `src/email_templates.py` (New)
- Email template definitions
- Multilingual email content using `_(ru, en)` pattern
- OTP and optimized prompt email templates

### 4. User Interface Extensions

#### File: `src/bot_handler.py` (Extended)
- Add new message handlers for email flow
- Integrate "Send 3 prompts to email" button
- Email authentication conversation flow

#### File: `src/messages.py` (Extended)
- Add new button definition for email delivery
- Keep existing translation system

### 5. Configuration Management

#### File: `src/config.py` (Extended)
- Add email service configuration (SMTP settings)
- Database connection strings
- Redis configuration
- Environment variable management for new services

### 6. Integration and Workflow

#### File: `src/email_flow.py` (New)
- Main email delivery workflow orchestration
- Direct integration with optimization methods (CRAFT, LYRA, GGL)
- System prompt modification for optimization methods
- Coordination between auth, email, and optimization services
- Error handling and fallback logic

## Data Models

### User Model (SQLAlchemy)

```python
# src/database.py
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email_original: Mapped[Optional[str]] = mapped_column(Text)
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_authenticated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

# Essential Indexes for User Model
Index('ix_users_telegram_id', User.telegram_id)  # Fast user lookup by telegram_id
Index('ix_users_email', User.email)  # Fast user lookup by email
Index('ix_users_authenticated', User.is_authenticated, User.last_authenticated_at.desc())  # Authenticated users queries
```

### AuthEvent Model (SQLAlchemy)

```python
# src/database.py
class AuthEvent(Base):
    __tablename__ = "auth_events"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

# Essential Indexes for Performance
Index('ix_auth_events_telegram_time', AuthEvent.telegram_id, AuthEvent.created_at.desc())
Index('ix_auth_events_email_time', AuthEvent.email, AuthEvent.created_at.desc())
Index('ix_auth_events_type_time', AuthEvent.event_type, AuthEvent.created_at.desc())
```

### Database Indexes Strategy

**Critical Indexes for Users Table:**
1. `telegram_id` - Primary lookup field (most frequent query)
2. `email` - Email-based lookups and uniqueness checks
3. `(is_authenticated, last_authenticated_at DESC)` - Find authenticated users

**Critical Indexes for AuthEvents Table:**
1. `(telegram_id, created_at DESC)` - Rate limiting queries per user
2. `(email, created_at DESC)` - Rate limiting queries per email  
3. `(event_type, created_at DESC)` - Audit queries and monitoring

**Note:** The `UNIQUE` constraints on `telegram_id` and `email` in the Users table automatically create indexes, but we explicitly define them for clarity and potential future optimization.

**Future Optimization Indexes (Can Add Later):**
- `(telegram_id, event_type, created_at)` - Specific event type queries per user
- `(success, created_at)` - Success/failure rate analysis

### Redis OTP Storage & Rate Limiting

**Redis Key Structure (Simplified):**

```python
# OTP Storage
otp:<tg_id> → Hash { otp_hash, email, expires_at, attempts } (TTL 300s)

# Rate Limiting Keys (Simplified)
rl:email:<email_norm>:hour → counter (TTL 3600s)    # ≤3/hour per email
rl:tg:<tg_id>:hour → counter (TTL 3600s)            # ≤5/hour per user
rl:tg:<tg_id>:last → timestamp (TTL 3600s)          # 60s spacing check

# Flow State Management
flow:<tg_id> → JSON state (TTL 86400s)  # awaiting_email, awaiting_otp, send_in_progress
```

**OTP Security:**
- **Hashing:** Argon2id (recommended) or bcrypt (cost≈12)
- **Attempts:** ≤3 per OTP; exceed → delete OTP + log `OTP_FAILED` with `attempt_limit`
- **Expiry:** 5 minutes TTL; expired → log `OTP_EXPIRED`

**Simplified Rate Limiting Logic:**
1. Check `rl:email:<email>:hour` ≤ 3 (per requirements)
2. Check `rl:tg:<tg_id>:hour` ≤ 5 (per requirements)
3. Check `rl:tg:<tg_id>:last` for 60s spacing (per requirements)
4. If all pass: increment counters + update timestamp + send OTP
5. If any fail: log `OTP_RATE_LIMITED` with specific reason

**Flow State Examples:**
```json
// Awaiting email input
{"state": "awaiting_email", "original_prompt": "user prompt text"}

// Awaiting OTP verification  
{"state": "awaiting_otp", "email": "user@example.com", "original_prompt": "..."}

// Optimization in progress
{"state": "optimizing", "email": "user@example.com", "original_prompt": "..."}

// Email sending in progress
{"state": "send_in_progress", "email": "user@example.com", "optimized_prompts": {...}}
```

## Optimization Method Integration

### Email-Specific System Prompts

When sending prompts to LLM optimization methods (CRAFT, LYRA, GGL) for email delivery, the system uses dedicated email-specific prompt files that already contain instructions to prevent follow-up questions:

**Implementation Pattern:**
```python
# For each optimization method, load email-specific prompt
email_prompts = {
    "CRAFT": load_prompt_file("src/prompts/CRAFT_email_prompt.txt"),
    "LYRA": load_prompt_file("src/prompts/LYRA_email_prompt.txt"), 
    "GGL": load_prompt_file("src/prompts/GGL_email_prompt.txt")
}

# Send to LLM with email-specific system prompt (no modification needed)
optimized_result = call_llm_method(method_name, user_prompt, email_prompts[method_name])
```

**Key Requirements:**
- Each method uses a dedicated email-specific prompt file
- Email prompts already contain instructions to avoid follow-up questions
- No runtime modification or string appending is needed
- Original system prompts (for regular optimization) remain unchanged
- PromptLoader loads both regular and email-specific versions of prompts

## Error Handling

### Authentication Errors

1. **Invalid Email Format**
   - Validation using regex
   - User-friendly error messages in configured language

2. **Rate Limiting**
   - Redis-based rate limiting
   - Clear error messages with retry timing

3. **OTP Verification Failures**
   - Attempt counting and lockout
   - Secure error messages (no information leakage)

### Email Delivery Errors

1. **SMTP Connection Failures**
   - Retry logic with exponential backoff
   - Error message notification in chat (no prompt sharing)

2. **Email Formatting Errors**
   - HTML sanitization
   - Error message notification in chat (no prompt sharing)

3. **Email Failure Handling**
   - On any email delivery failure, only show error message in chat
   - Do not share optimized prompts in chat as fallback
   - Log failure details for debugging and monitoring

### Database Errors

1. **Connection Failures**
   - Connection pooling and retry logic
   - Graceful degradation

2. **Migration Errors**
   - Rollback capabilities
   - Data integrity checks

## Testing Strategy

### Test Plan Overview

**Testing Approach:** Test-Driven Development with comprehensive coverage
**Test Environment:** Separate test database (SQLite), test Redis instance, mock SMTP
**Coverage Target:** >90% code coverage for new components
**Test Data:** Use masked/anonymized data, never real user information

### Unit Tests (Individual Component Testing)

#### File: `tests/test_auth_service.py` (New)
```python
class TestAuthService:
    async def test_otp_generation():
        """Test OTP generation creates 6-digit numeric code."""
        
    async def test_otp_hashing():
        """Test OTP is properly hashed with Argon2id."""
        
    async def test_rate_limiting_email_comprehensive():
        """Test email rate limiting (3/hour per email):
        - Test exactly 3 sends allowed per hour
        - Test 4th send blocked with proper error
        - Test rate limit reset after 1 hour
        - Test rate limiting across normalized email variants
        """
        
    async def test_rate_limiting_user_comprehensive():
        """Test user rate limiting (5/hour per telegram_id):
        - Test exactly 5 sends allowed per hour per user
        - Test 6th send blocked with proper error  
        - Test rate limit reset after 1 hour
        """
        
    async def test_rate_limiting_spacing_comprehensive():
        """Test 60s spacing between OTP sends per telegram_id:
        - Test send blocked if <60s since last send
        - Test send allowed if ≥60s since last send
        - Test spacing enforcement across different emails for same user
        """
        
    async def test_otp_verification_success():
        """Test successful OTP verification and Redis cleanup."""
        
    async def test_otp_verification_mismatch():
        """Test OTP verification with wrong code:
        - Test attempt counter increments
        - Test failure logged to audit_events
        - Test OTP remains valid for retry (until attempt limit)
        """
        
    async def test_otp_verification_expired():
        """Test OTP verification after 5-minute expiry:
        - Test expired OTP rejection
        - Test OTP_EXPIRED event logged
        - Test Redis key cleanup
        """
        
    async def test_otp_verification_attempt_limit():
        """Test OTP verification attempt limit (3 attempts):
        - Test 3 failed attempts allowed
        - Test 4th attempt blocked
        - Test OTP deleted after attempt limit exceeded
        - Test OTP_FAILED event logged with 'attempt_limit' reason
        """
```

#### File: `tests/test_email_service.py` (New)
```python
class TestEmailService:
    async def test_email_composition():
        """Test email HTML composition with proper formatting."""
        
    async def test_email_template_rendering_comprehensive():
        """Test email templates with RU/EN language support:
        - Test Russian template rendering with Cyrillic characters
        - Test English template rendering
        - Test proper HTML escaping of user content
        - Test <pre><code> block formatting for technical content
        - Test email subject line translation
        - Test professional signature in both languages
        """
        
    async def test_smtp_connection_tls():
        """Test SMTP connection with TLS (port 587)."""
        
    async def test_smtp_connection_ssl():
        """Test SMTP connection with SSL (port 465)."""
        
    async def test_email_sending_success():
        """Test successful email delivery."""
        
    async def test_email_sending_failure():
        """Test email delivery failure handling."""
        
    async def test_idempotent_email_send():
        """Test idempotent email sending (webhook replay protection):
        - Test duplicate email send requests result in single email
        - Test request deduplication mechanism
        - Test proper logging of duplicate attempts
        """
        
    async def test_email_failure_error_only():
        """Test error-only handling when email delivery fails:
        - Test only error message sent to chat (no optimized prompts)
        - Test proper error logging and user notification
        - Test no retry attempts for failed email delivery
        """
        
    async def test_email_content_sanitization():
        """Test HTML content sanitization for security."""
```

#### File: `tests/test_database.py` (New)
```python
class TestDatabase:
    async def test_user_model_creation():
        """Test User model creation and validation."""
        
    async def test_user_unique_constraints():
        """Test telegram_id and email uniqueness."""
        
    async def test_auth_event_logging():
        """Test AuthEvent creation and indexing."""
        
    async def test_database_migrations():
        """Test Alembic migrations up and down."""
        
    async def test_email_normalization():
        """Test email normalization for storage."""
        
    async def test_email_normalization_comprehensive():
        """Test comprehensive email normalization cases:
        - Case normalization: Test@Example.Com → test@example.com
        - Plus-tag handling: user+tag@domain.com → user@domain.com  
        - IDN (International Domain Names): unicode domains
        - Uniqueness enforcement across normalized forms
        """
        
    async def test_email_uniqueness_constraints():
        """Test email uniqueness across different input formats:
        - Same email with different cases should be treated as duplicate
        - Plus-tagged emails should be treated as same user
        - IDN variations should be properly handled
        """
```

#### File: `tests/test_redis_client.py` (New)
```python
class TestRedisClient:
    async def test_otp_storage():
        """Test OTP hash storage with TTL."""
        
    async def test_rate_limit_counters():
        """Test rate limiting counter operations."""
        
    async def test_flow_state_management():
        """Test flow state storage and retrieval."""
        
    async def test_redis_connection_failure():
        """Test Redis connection failure handling."""
```

#### File: `tests/test_metrics.py` (New)
```python
class TestMetrics:
    def test_otp_metrics():
        """Test OTP-related metric collection."""
        
    def test_email_metrics():
        """Test email delivery metric collection."""
        
    def test_latency_metrics():
        """Test LLM and SMTP latency tracking."""
        
    def test_metrics_export():
        """Test metrics summary export."""
```

#### File: `tests/test_audit_service.py` (New)
```python
class TestAuditService:
    async def test_event_logging():
        """Test audit event creation."""
        
    async def test_event_purging():
        """Test old event purging logic."""
        
    async def test_retention_policy():
        """Test configurable retention period."""
```

#### File: `tests/test_health_checks.py` (New)
```python
class TestHealthChecks:
    async def test_database_health():
        """Test database health check."""
        
    async def test_redis_health():
        """Test Redis health check."""
        
    async def test_smtp_health():
        """Test SMTP health check."""
        
    async def test_health_failure_handling():
        """Test health failure detection and alerting."""
```

### Integration Tests (Component Interaction Testing)

#### File: `tests/test_email_flow_integration.py` (New)
```python
class TestEmailFlowIntegration:
    async def test_complete_email_auth_flow():
        """Test complete flow: button → email → OTP → verification → optimization → email delivery."""
        
    async def test_email_auth_with_existing_user():
        """Test flow for already authenticated user."""
        
    async def test_email_auth_rate_limiting():
        """Test rate limiting integration across services."""
        
    async def test_email_delivery_failure_handling():
        """Test error message display when email fails (no prompt sharing)."""
        
    async def test_system_prompt_modification():
        """Test system prompt modification for optimization methods:
        - Test Russian instruction appended to each method's system prompt
        - Test original system prompts remain unchanged
        - Test all three methods receive modified prompts
        """
        
    async def test_optimization_integration():
        """Test integration with CRAFT/LYRA/GGL optimization with modified system prompts."""
```

#### File: `tests/test_bot_handler_integration.py` (Extended)
```python
class TestBotHandlerIntegration:
    async def test_email_button_display():
        """Test 'Send 3 prompts to email' button appears correctly."""
        
    async def test_email_input_handling():
        """Test email input validation and processing."""
        
    async def test_otp_input_handling():
        """Test OTP input validation and verification."""
        
    async def test_error_message_display():
        """Test error message display in user's language."""
        
    async def test_conversation_state_management():
        """Test conversation state during email flow."""
```

### End-to-End Tests (Full System Testing)

#### File: `tests/test_e2e_email_delivery.py` (New)
```python
class TestE2EEmailDelivery:
    async def test_new_user_complete_flow():
        """Test complete flow for new user from start to email delivery."""
        
    async def test_returning_user_flow():
        """Test flow for returning authenticated user."""
        
    async def test_multiple_concurrent_users():
        """Test system behavior with multiple users simultaneously."""
        
    async def test_system_recovery_scenarios():
        """Test system behavior during service failures and recovery."""
```

### Performance Tests

#### File: `tests/test_performance.py` (New)
```python
class TestPerformance:
    async def test_database_query_performance():
        """Test database query response times under load."""
        
    async def test_redis_operation_performance():
        """Test Redis operation latency."""
        
    async def test_email_delivery_throughput():
        """Test email delivery performance."""
        
    async def test_concurrent_otp_generation():
        """Test OTP generation under concurrent load."""
```

### Security Tests

#### File: `tests/test_security.py` (New)
```python
class TestSecurity:
    async def test_otp_brute_force_protection():
        """Test OTP brute force protection."""
        
    async def test_rate_limiting_bypass_attempts():
        """Test rate limiting cannot be bypassed."""
        
    async def test_email_injection_protection():
        """Test protection against email header injection."""
        
    async def test_data_masking_in_logs():
        """Test sensitive data is properly masked in logs."""
        
    async def test_credential_exposure():
        """Test no credentials are exposed in logs or errors."""
```

### Test Data Management

```python
# tests/fixtures.py
@pytest.fixture
async def test_user():
    """Create test user with masked data."""
    return {
        "telegram_id": 123456789,
        "email": "test@example.com",
        "email_original": "Test@Example.Com"
    }

@pytest.fixture
async def mock_smtp():
    """Mock SMTP server for testing."""
    
@pytest.fixture
async def test_redis():
    """Test Redis instance with cleanup."""
    
@pytest.fixture
async def test_database():
    """Test database with migrations."""
```

### Test Environment Setup

```yaml
# docker-compose.test.yml
services:
  test-redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"
  
  test-postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: test_botdb
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5433:5432"
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test_pass
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest --cov=src --cov-report=html
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Security Considerations

### OTP Security

1. **Hashing**: Use Argon2id for OTP hashing
2. **Storage**: Store only hashes in Redis, never plain text
3. **Expiry**: 5-minute expiration for OTPs
4. **Rate Limiting**: Multiple layers to prevent abuse

### Email Security

1. **Validation**: Strict email format validation
2. **Normalization**: Canonical email format for uniqueness
3. **Content**: HTML sanitization for email content
4. **Transport**: TLS/SSL for SMTP connections

### Database Security

1. **ORM Only**: No raw SQL queries
2. **Migrations**: Versioned schema changes
3. **Indexing**: Proper indexes for performance and security

### Sensitive Data Protection & Logging

#### **Data Masking Requirements:**

```python
# Email masking for logs
def mask_email(email: str) -> str:
    """Mask email for logging: user@example.com → u***@e***.com"""
    if '@' not in email:
        return email[:1] + '***'
    local, domain = email.split('@', 1)
    masked_local = local[:1] + '***' if len(local) > 1 else '***'
    masked_domain = domain[:1] + '***.' + domain.split('.')[-1] if '.' in domain else '***'
    return f"{masked_local}@{masked_domain}"

# Telegram ID partial masking
def mask_telegram_id(tg_id: int) -> str:
    """Mask telegram ID: 123456789 → 123***789"""
    tg_str = str(tg_id)
    if len(tg_str) <= 6:
        return tg_str[:2] + '***'
    return tg_str[:3] + '***' + tg_str[-3:]
```

#### **Never Log These Sensitive Items:**
- ❌ Plain text OTPs
- ❌ OTP hashes  
- ❌ Full email addresses (always mask)
- ❌ SMTP passwords or credentials
- ❌ Database connection strings with passwords
- ❌ Redis connection strings with auth tokens
- ❌ Full telegram IDs (always mask)

#### **Safe to Log (Masked/Sanitized):**
- ✅ Masked emails (`u***@e***.com`)
- ✅ Masked telegram IDs (`123***789`)
- ✅ Event types (`OTP_SENT`, `EMAIL_DELIVERED`)
- ✅ Success/failure status (boolean)
- ✅ Error types (without sensitive details)
- ✅ Timestamps and request IDs

#### **Environment Variable Security:**
```bash
# ❌ Never commit these to version control
SMTP_PASSWORD=secret_password
DATABASE_URL=postgresql://user:password@host:port/db
REDIS_URL=redis://:password@host:port/db

# ✅ Use .env files and .gitignore
# ✅ Use secrets management in production
# ✅ Rotate credentials regularly
```

#### **Comprehensive Email Auth Flow Logging:**

```python
# Email Authentication Flow Events
logger.info(f"EMAIL_FLOW_START: User {mask_telegram_id(tg_id)} initiated email delivery")
logger.info(f"EMAIL_INPUT: User {mask_telegram_id(tg_id)} provided email {mask_email(email)}")
logger.info(f"EMAIL_VALIDATION: Email format {'valid' if valid else 'invalid'} for {mask_telegram_id(tg_id)}")

# Rate Limiting Events  
logger.info(f"RATE_CHECK: User {mask_telegram_id(tg_id)} rate limit status: email={email_count}/3, user={user_count}/5, last_send={seconds_ago}s")
logger.warning(f"RATE_LIMITED: User {mask_telegram_id(tg_id)} blocked - {reason}")

# Redis Operations
logger.debug(f"REDIS_SET: OTP hash stored for {mask_telegram_id(tg_id)}, expires in 300s")
logger.debug(f"REDIS_INCR: Rate limit counter updated - rl:tg:{mask_telegram_id(tg_id)}:hour = {count}")
logger.debug(f"REDIS_GET: OTP verification attempt for {mask_telegram_id(tg_id)}")
logger.debug(f"REDIS_DEL: OTP cleared for {mask_telegram_id(tg_id)} after {'success' if success else 'failure'}")

# OTP Generation & Verification
logger.info(f"OTP_GENERATED: 6-digit OTP created for {mask_telegram_id(tg_id)}")
logger.info(f"OTP_SENT: Email sent to {mask_email(email)} for {mask_telegram_id(tg_id)}")
logger.info(f"OTP_VERIFY_ATTEMPT: User {mask_telegram_id(tg_id)} attempt {attempt}/3")
logger.info(f"OTP_VERIFY_SUCCESS: User {mask_telegram_id(tg_id)} authenticated")
logger.warning(f"OTP_VERIFY_FAILED: User {mask_telegram_id(tg_id)} failed attempt {attempt}/3 - {reason}")
logger.warning(f"OTP_EXPIRED: Expired OTP for {mask_telegram_id(tg_id)}")

# Database Operations
logger.info(f"DB_USER_CREATE: New user created for {mask_telegram_id(tg_id)}")
logger.info(f"DB_USER_UPDATE: Authentication status updated for {mask_telegram_id(tg_id)}")
logger.info(f"DB_EVENT_LOG: {event_type} recorded for {mask_telegram_id(tg_id)}")

# Email Sending
logger.info(f"SMTP_CONNECT: Connecting to SMTP server for {mask_telegram_id(tg_id)}")
logger.info(f"EMAIL_COMPOSE: Optimized prompts email prepared for {mask_email(email)}")
logger.info(f"EMAIL_SEND_SUCCESS: Email delivered to {mask_email(email)}")
logger.error(f"EMAIL_SEND_FAILED: Email delivery failed for {mask_email(email)} - {error_type}")

# Direct Optimization
logger.info(f"OPTIMIZATION_START: Running 3 methods for {mask_telegram_id(tg_id)}")
logger.info(f"SYSTEM_PROMPT_MODIFIED: Added Russian instruction to {method_name} for {mask_telegram_id(tg_id)}")
logger.info(f"OPTIMIZATION_COMPLETE: All methods completed for {mask_telegram_id(tg_id)}")

# Error Scenarios
logger.error(f"REDIS_CONNECTION_FAILED: Cannot connect to Redis for {mask_telegram_id(tg_id)}")
logger.error(f"DB_CONNECTION_FAILED: Database error for {mask_telegram_id(tg_id)}")
logger.error(f"SMTP_AUTH_FAILED: SMTP authentication failed")
logger.error(f"FLOW_STATE_CORRUPTED: Invalid flow state for {mask_telegram_id(tg_id)}")
```

#### **Redis State Change Logging:**

```python
# Redis Key Lifecycle Tracking
logger.debug(f"REDIS_KEY_SET: {key_type}:{mask_telegram_id(tg_id)} → TTL={ttl}s")
logger.debug(f"REDIS_KEY_GET: {key_type}:{mask_telegram_id(tg_id)} → {'found' if exists else 'not_found'}")
logger.debug(f"REDIS_KEY_INCR: {key_type}:{mask_telegram_id(tg_id)} → {old_value} to {new_value}")
logger.debug(f"REDIS_KEY_DEL: {key_type}:{mask_telegram_id(tg_id)} → deleted")
logger.debug(f"REDIS_KEY_EXPIRE: {key_type}:{mask_telegram_id(tg_id)} → expired")

# Flow State Transitions
logger.info(f"FLOW_STATE: {mask_telegram_id(tg_id)} → {old_state} to {new_state}")
logger.debug(f"FLOW_DATA: {mask_telegram_id(tg_id)} → state updated with {data_keys}")
```

#### **Log Levels Strategy:**
- **DEBUG**: Redis operations, state transitions, internal flow
- **INFO**: User actions, successful operations, state changes  
- **WARNING**: Rate limiting, failed attempts, recoverable errors
- **ERROR**: System failures, unrecoverable errors, security issues

## Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=sqlite:///./bot.db  # Development
DATABASE_URL=postgresql://user:pass@host:port/db  # Production

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Email Configuration (SMTP-Pulse)
SMTP_HOST=smtp-pulse.com
SMTP_PORT=587                    # TLS port (default)
SMTP_PORT_SSL=465               # SSL port (alternative)
SMTP_USERNAME=your_username
SMTP_PASSWORD=your_password
SMTP_USE_TLS=true               # true for TLS (port 587), false for SSL (port 465)
SMTP_USE_SSL=false              # true for SSL (port 465), false for TLS (port 587)

# Language Configuration
LANGUAGE=ru  # or en

# Audit Configuration
AUDIT_RETENTION_DAYS=90  # Days to retain audit events (default: 90)
```

### Configuration Files

#### File: `src/config.py` (Extended)
```python
class Config:
    # Existing configuration...
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bot.db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Email Configuration
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp-pulse.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_PORT_SSL: int = int(os.getenv("SMTP_PORT_SSL", "465"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    
    # Language
    LANGUAGE: str = os.getenv("LANGUAGE", "ru")
    
    # Audit Configuration
    AUDIT_RETENTION_DAYS: int = int(os.getenv("AUDIT_RETENTION_DAYS", "90"))
    
    @property
    def smtp_port(self) -> int:
        """Get the appropriate SMTP port based on TLS/SSL configuration."""
        if self.SMTP_USE_SSL:
            return self.SMTP_PORT_SSL  # 465 for SSL
        else:
            return self.SMTP_PORT      # 587 for TLS (default)
    
    @property
    def smtp_security(self) -> str:
        """Get the SMTP security method for logging."""
        if self.SMTP_USE_SSL:
            return "SSL"
        elif self.SMTP_USE_TLS:
            return "TLS"
        else:
            return "NONE"
```

## Deployment Considerations

### Docker Configuration

#### File: `docker-compose.yml` (Extended)
```yaml
services:
  bot:
    # Existing bot configuration...
    depends_on:
      - redis
      - postgres
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/botdb
      - REDIS_URL=redis://redis:6379/0
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: botdb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Migration Strategy

1. **Initial Setup**: Run `alembic upgrade head` on deployment
2. **Schema Changes**: Generate migrations with `alembic revision --autogenerate`
3. **Rollback**: Use `alembic downgrade` for rollbacks
4. **Backup**: Database backup before major migrations

## Performance Optimization

### Database Optimization

1. **Indexes**: Composite indexes on frequently queried columns
2. **Connection Pooling**: SQLAlchemy connection pool configuration
3. **Query Optimization**: Efficient ORM queries with proper joins

### Redis Optimization

1. **Connection Pooling**: Redis connection pool for concurrent operations
2. **Memory Management**: TTL-based cleanup for expired OTPs
3. **Pipelining**: Batch Redis operations where possible

### Email Optimization

1. **Connection Reuse**: SMTP connection pooling
2. **Async Operations**: Non-blocking email sending
3. **Queue Management**: Email queue for high-volume scenarios

## Monitoring and Observability

### Audit Requirements ✅

**Database Audit Trail:**
- ✅ Every OTP outcome recorded in `auth_events` table
- ✅ Every email outcome recorded in `auth_events` table  
- ✅ Event types: `OTP_SENT`, `OTP_VERIFIED`, `OTP_FAILED`, `OTP_EXPIRED`, `EMAIL_SEND_OK`, `EMAIL_SEND_FAIL`
- ✅ Includes telegram_id, email (masked), success status, reason, timestamp
- ✅ **Retention Policy**: Configurable purging of events older than 90 days (default)

**Audit Event Purging Implementation:**

```python
# src/audit_service.py (New File)
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import delete, select, func
from .database import AuthEvent, get_db_session
from .config import Config

class AuditService:
    def __init__(self, config: Config):
        self.retention_days = int(config.AUDIT_RETENTION_DAYS or 90)
    
    async def log_event(self, telegram_id: int, email: str, event_type: str, 
                       success: bool, reason: str = None):
        """Log an audit event to the database."""
        async with get_db_session() as session:
            event = AuthEvent(
                telegram_id=telegram_id,
                email=email,  # Store normalized email
                event_type=event_type,
                success=success,
                reason=reason
            )
            session.add(event)
            await session.commit()
            
            logger.info(f"AUDIT_EVENT: {event_type} for {mask_telegram_id(telegram_id)} - {'success' if success else 'failed'}")
    
    async def purge_old_events(self):
        """Purge audit events older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        async with get_db_session() as session:
            # Count events to be purged
            count_query = select(func.count(AuthEvent.id)).where(
                AuthEvent.created_at < cutoff_date
            )
            count_result = await session.execute(count_query)
            events_to_purge = count_result.scalar()
            
            if events_to_purge > 0:
                # Delete old events
                delete_query = delete(AuthEvent).where(
                    AuthEvent.created_at < cutoff_date
                )
                await session.execute(delete_query)
                await session.commit()
                
                logger.info(f"AUDIT_PURGE: Deleted {events_to_purge} events older than {self.retention_days} days")
            else:
                logger.debug(f"AUDIT_PURGE: No events to purge (retention: {self.retention_days} days)")
    
    async def start_periodic_purge(self):
        """Start periodic purging task (runs daily)."""
        while True:
            try:
                await self.purge_old_events()
                # Sleep for 24 hours
                await asyncio.sleep(86400)
            except Exception as e:
                logger.error(f"AUDIT_PURGE_ERROR: {type(e).__name__} - {str(e)}")
                # Sleep for 1 hour on error, then retry
                await asyncio.sleep(3600)

# Global audit service instance  
audit_service = AuditService(config)
```

### Metrics Collection ✅

**Required Metrics Implementation:**

```python
# src/metrics.py (New File)
import time
from collections import defaultdict, Counter
from typing import Dict, Any

class MetricsCollector:
    def __init__(self):
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = defaultdict(float)
    
    # OTP Metrics
    def increment_otp_sent(self):
        self.counters['otp_sent'] += 1
        logger.info("METRIC: otp_sent incremented")
    
    def increment_otp_verified(self):
        self.counters['otp_verified'] += 1
        logger.info("METRIC: otp_verified incremented")
    
    def increment_otp_failed(self, reason: str):
        self.counters['otp_failed'] += 1
        self.counters[f'otp_failed_{reason}'] += 1
        logger.info(f"METRIC: otp_failed incremented (reason: {reason})")
    
    def increment_otp_expired(self):
        self.counters['otp_expired'] += 1
        logger.info("METRIC: otp_expired incremented")
    
    # Email Metrics
    def increment_email_ok(self):
        self.counters['email_ok'] += 1
        logger.info("METRIC: email_ok incremented")
    
    def increment_email_fail(self, reason: str):
        self.counters['email_fail'] += 1
        self.counters[f'email_fail_{reason}'] += 1
        logger.info(f"METRIC: email_fail incremented (reason: {reason})")
    
    # Latency Metrics
    def record_llm_latency(self, method: str, latency_ms: float, tokens: int):
        self.timers[f'llm_latency_{method}'].append(latency_ms)
        self.counters[f'llm_tokens_{method}'] += tokens
        logger.info(f"METRIC: LLM {method} - {latency_ms}ms, {tokens} tokens")
    
    def record_smtp_latency(self, latency_ms: float):
        self.timers['smtp_latency'].append(latency_ms)
        logger.info(f"METRIC: SMTP latency - {latency_ms}ms")
    
    # Metrics Export
    def get_metrics_summary(self) -> Dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "latency_avg": {
                key: sum(values) / len(values) if values else 0
                for key, values in self.timers.items()
            },
            "timestamp": time.time()
        }

# Global metrics instance
metrics = MetricsCollector()
```

**Metrics Integration Examples:**

```python
# In auth_service.py
async def send_otp(telegram_id: int, email: str):
    start_time = time.time()
    try:
        # ... OTP generation and sending logic ...
        metrics.increment_otp_sent()
        await audit_service.log_event(telegram_id, email, "OTP_SENT", True)
    except Exception as e:
        metrics.increment_otp_failed("send_error")
        await audit_service.log_event(telegram_id, email, "OTP_SENT", False, str(e))

# In email_service.py  
async def send_email(to_email: str, content: str):
    start_time = time.time()
    try:
        # ... email sending logic ...
        smtp_latency = (time.time() - start_time) * 1000
        metrics.record_smtp_latency(smtp_latency)
        metrics.increment_email_ok()
        await audit_service.log_event(telegram_id, to_email, "EMAIL_SEND_OK", True)
    except Exception as e:
        metrics.increment_email_fail("smtp_error")
        await audit_service.log_event(telegram_id, to_email, "EMAIL_SEND_FAIL", False, str(e))

# In LLM optimization calls
async def optimize_prompt(method: str, prompt: str):
    start_time = time.time()
    response = await llm_client.generate(prompt)
    latency_ms = (time.time() - start_time) * 1000
    token_count = len(response.split())  # Approximate
    metrics.record_llm_latency(method, latency_ms, token_count)
```

### Logging Strategy ✅

**PII Protection Requirements:**
- ✅ **Minimal PII**: Always mask emails and telegram IDs in logs
- ✅ **Domain Masking**: `user@example.com` → `u***@e***.com`  
- ✅ **User Masking**: `123456789` → `123***789`
- ✅ **Never Log**: OTPs, OTP hashes, passwords, credentials, secrets
- ✅ **Structured Logging**: JSON-formatted logs for parsing
- ✅ **Appropriate Levels**: DEBUG/INFO/WARNING/ERROR/CRITICAL

### Health Checks & Monitoring

#### **Health Check Implementation:**

```python
# src/health_checks.py (New File)
class HealthChecker:
    async def check_database_health(self) -> dict:
        """Check database connectivity and basic operations."""
        try:
            # Test connection and simple query
            result = await db.execute("SELECT 1")
            return {
                "service": "database",
                "status": "healthy",
                "response_time_ms": response_time,
                "details": "Connection and query successful"
            }
        except Exception as e:
            logger.error(f"DB_HEALTH_FAILED: {type(e).__name__}")
            return {
                "service": "database", 
                "status": "unhealthy",
                "error": type(e).__name__,
                "details": "Database connection failed"
            }
    
    async def check_redis_health(self) -> dict:
        """Check Redis connectivity and operations."""
        try:
            # Test connection, set/get operation
            await redis.ping()
            test_key = f"health_check_{int(time.time())}"
            await redis.setex(test_key, 10, "test")
            await redis.delete(test_key)
            
            return {
                "service": "redis",
                "status": "healthy", 
                "response_time_ms": response_time,
                "details": "Connection and operations successful"
            }
        except Exception as e:
            logger.error(f"REDIS_HEALTH_FAILED: {type(e).__name__}")
            return {
                "service": "redis",
                "status": "unhealthy",
                "error": type(e).__name__,
                "details": "Redis connection or operations failed"
            }
    
    async def check_smtp_health(self) -> dict:
        """Check SMTP server connectivity."""
        try:
            # Test SMTP connection without sending email
            server = smtplib.SMTP(config.SMTP_HOST, config.smtp_port)
            if config.SMTP_USE_TLS:
                server.starttls()
            elif config.SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(config.SMTP_HOST, config.smtp_port)
            
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.quit()
            
            return {
                "service": "smtp",
                "status": "healthy",
                "response_time_ms": response_time,
                "details": f"SMTP connection successful ({config.smtp_security})"
            }
        except Exception as e:
            logger.error(f"SMTP_HEALTH_FAILED: {type(e).__name__}")
            return {
                "service": "smtp",
                "status": "unhealthy", 
                "error": type(e).__name__,
                "details": "SMTP connection or authentication failed"
            }
```

#### **Health Monitoring Strategy:**

**Periodic Health Checks:**
```python
# Run health checks every 60 seconds
async def periodic_health_check():
    while True:
        health_results = await run_all_health_checks()
        
        # Log health status
        for result in health_results:
            if result["status"] == "healthy":
                logger.info(f"HEALTH_OK: {result['service']} - {result['response_time_ms']}ms")
            else:
                logger.error(f"HEALTH_FAILED: {result['service']} - {result['error']}")
        
        # Check for critical failures
        failed_services = [r for r in health_results if r["status"] == "unhealthy"]
        if failed_services:
            await handle_health_failures(failed_services)
        
        await asyncio.sleep(60)  # Check every minute
```

#### **Alerting & Degraded Mode:**

**Critical Service Failures:**
```python
async def handle_health_failures(failed_services: list):
    service_names = [s["service"] for s in failed_services]
    
    # Log critical alert
    logger.critical(f"CRITICAL_HEALTH_FAILURE: Services down: {service_names}")
    
    # Enable degraded mode
    if "database" in service_names:
        # Disable new user registrations, use cache for existing users
        logger.warning("DEGRADED_MODE: Database unavailable - disabling new registrations")
    
    if "redis" in service_names:
        # Disable OTP functionality, fallback to chat-only mode
        logger.warning("DEGRADED_MODE: Redis unavailable - disabling email authentication")
    
    if "smtp" in service_names:
        # Disable email delivery, fallback to chat delivery
        logger.warning("DEGRADED_MODE: SMTP unavailable - using chat fallback for prompts")
```

#### **Health Check Logging:**

**Regular Health Monitoring:**
```python
# Every minute - INFO level
logger.info(f"HEALTH_CHECK: db=healthy(15ms), redis=healthy(8ms), smtp=healthy(120ms)")

# Service recovery - INFO level  
logger.info(f"HEALTH_RECOVERED: redis service restored after 3min downtime")

# Service degradation - WARNING level
logger.warning(f"HEALTH_DEGRADED: smtp response time 2500ms (threshold: 1000ms)")

# Service failure - ERROR level
logger.error(f"HEALTH_FAILED: database connection timeout after 30s")

# Critical system failure - CRITICAL level
logger.critical(f"HEALTH_CRITICAL: Multiple services down - db, redis. Bot entering safe mode")
```

#### **Graceful Degradation:**

**Service Unavailability Handling:**
1. **Database Down**: 
   - Disable new user registrations
   - Use Redis cache for existing authenticated users
   - Log all operations for later replay

2. **Redis Down**:
   - Disable email authentication flow
   - Fall back to chat-only prompt delivery
   - Continue serving existing authenticated users

3. **SMTP Down**:
   - Disable email delivery
   - Automatically fall back to chat delivery
   - Queue emails for retry when service recovers

#### **Health Check Integration:**

**Bot Handler Integration:**
```python
# Before processing email flow
if not await health_checker.is_service_healthy("redis"):
    await update.message.reply_text(
        "⚠️ Email authentication temporarily unavailable. Please try again later."
    )
    return

# Before sending emails  
if not await health_checker.is_service_healthy("smtp"):
    logger.info(f"EMAIL_FALLBACK: SMTP unhealthy, using chat delivery for {mask_telegram_id(tg_id)}")
    # Proceed with chat delivery instead
```