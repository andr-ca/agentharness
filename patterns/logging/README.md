# Logging & Telemetry – Complete Logging Guide

Comprehensive logging and telemetry standards for all code. Logging is MANDATORY and must be verified before marking work complete.

## 📚 Documentation

### [LOGGING_STANDARDS.md](./LOGGING_STANDARDS.md)
**Complete logging framework and standards**

- Why logging is non-negotiable (production debugging, security)
- Logging architecture (backends, configuration, processors)
- Log levels (TRACE, DEBUG, INFO, WARN, ERROR, CRITICAL)
- Structured logging (mandatory JSON/key=value format)
- Central configuration (single source of truth)
- Environment-based configuration
- Implementation for all languages (Python, TypeScript, Go, Java)
- What to log (and what NOT to log)
- Log rotation & retention policies
- Telemetry & metrics configuration
- Logging checklist (before marking work complete)
- Complete working examples
- Debugging with logs
- OTEL integration

### [logging.yaml.example](./logging.yaml.example)
**Comprehensive configuration template**

- Ready-to-copy logging configuration
- Environment variable substitution
- Logging backend setup (file, OTEL, console, cloud)
- Logger configuration by functionality
- Metrics collection
- Distributed tracing
- Security & PII handling
- Performance settings
- Development settings

---

## 🚨 Critical Requirements

### Logging is MANDATORY

**All code MUST have:**
- ✅ Centralized logging configuration
- ✅ Multiple backend support (file, OTEL, console, cloud)
- ✅ Proper log rotation and retention
- ✅ Structured logging (JSON)
- ✅ All critical events logged
- ✅ Full error context
- ✅ Telemetry/metrics
- ✅ Sensitive data protection
- ✅ Debugging capability

**At Production tier, code without logging WILL NOT BE ACCEPTED. See Rigor Tiers in `.github/CODING_GUIDELINES.md`.**

### Never Ship Without Logging

**Acceptance criteria:**
- [ ] Centralized logging configured
- [ ] All critical paths logged
- [ ] All errors logged with context
- [ ] Telemetry working
- [ ] Logs accessible for debugging
- [ ] Log rotation working
- [ ] Sensitive data NOT in logs
- [ ] Log levels appropriate
- [ ] Dashboards/alerts configured

---

## Quick Start

### 1. Copy Configuration

```bash
# Copy example to your project
cp patterns/logging/logging.yaml.example config/logging.yaml
```

### 2. Customize for Your Service

```yaml
logging:
  context:
    service: my-api-service
    environment: production
  
  backends:
    file:
      path: /var/log/my-service
    otel:
      endpoint: otel-collector.internal:4317
```

### 3. Implement in Your Code

**Python:**
```python
import logging.config
import yaml

with open('config/logging.yaml') as f:
    config = yaml.safe_load(f)
logging.config.dictConfig(config)

logger = logging.getLogger('api')
logger.info("Server started", {"port": 8000})
```

**TypeScript:**
```typescript
import winston from 'winston';
import yaml from 'js-yaml';
import fs from 'fs';

const config = yaml.load(fs.readFileSync('config/logging.yaml', 'utf8'));
const logger = winston.createLogger(config.logging);
logger.info('Server started', { port: 8000 });
```

**Go:**
```go
import "log/slog"

slog.Info("Server started", "port", 8000)
```

### 4. Add to Your Code

```python
# Log important events
logger.info("user_login", {
    "user_id": "123",
    "method": "password",
    "ip": "192.168.1.1"
})

# Log errors with context
logger.error("payment_failed", {
    "order_id": "456",
    "error": str(e),
    "retry": True
})

# Log performance
logger.debug("query_executed", {
    "query_time_ms": 1234,
    "rows": 42
})
```

### 5. Verify in Development

```bash
# See logs in console
tail -f logs/app-$(date +%Y-%m-%d).log

# Or use log viewer
npx playwright show-report  # View as formatted JSON
```

---

## Logging Best Practices

### DO ✅

- ✅ Use structured logging (JSON)
- ✅ Include trace IDs for distributed tracing
- ✅ Log all errors with full context
- ✅ Log external API calls
- ✅ Log state changes
- ✅ Rotate logs by day or size
- ✅ Configure OTEL for production
- ✅ Sanitize sensitive data
- ✅ Use appropriate log levels

### DON'T ❌

- ❌ Log passwords or secrets
- ❌ Log full credit card numbers
- ❌ Log social security numbers
- ❌ Log without structure (printf-style)
- ❌ Ignore errors (always log them)
- ❌ Ship without logging configuration
- ❌ Use only one backend
- ❌ Log and forget (enable dashboards)
- ❌ Skip log rotation

---

## Configuration by Environment

### Development

```yaml
logging:
  level: DEBUG
  format: text
  backends:
    console:
      enabled: true
      colorize: true
    file:
      enabled: false  # Logs to stdout only
```

**Run:**
```bash
LOG_LEVEL=DEBUG npm run dev
```

### Staging

```yaml
logging:
  level: INFO
  format: json
  backends:
    console:
      enabled: false
    file:
      enabled: true
      path: /var/log/app
    otel:
      enabled: true
```

**Run:**
```bash
ENVIRONMENT=staging npm run start
```

### Production

```yaml
logging:
  level: INFO
  format: json
  backends:
    console:
      enabled: false
    file:
      enabled: true
      path: /var/log/app
      rotation:
        max_age_days: 90
    otel:
      enabled: true
    cloud:
      enabled: true
      provider: gcp
```

**Run:**
```bash
ENVIRONMENT=production CLOUD_LOGGING_ENABLED=true npm run start
```

---

## Log Levels Guide

```
TRACE   → Variable values, function flow
         Use in development for detailed debugging
         
DEBUG   → Detailed info useful for debugging
         Configuration, decisions, query times
         
INFO    → Major milestones, state changes
         User actions, important events
         
WARN    → Unusual but handled situations
         Degraded performance, retries, timeouts
         
ERROR   → Operation failed (but recovered)
         Validation errors, API failures, DB errors
         
CRITICAL → System failure, unrecoverable
         Out of memory, database down, auth failed
```

### Example: Setting Log Levels

```yaml
loggers:
  auth:
    level: DEBUG      # Detailed auth logging
  
  database:
    level: INFO       # Normal ops only
  
  external:
    level: WARN       # Only warn/error from 3rd party
```

---

## Structured Logging Examples

### Good ✅

```python
# Clear, parseable, fields
logger.info("payment_processed", {
    "transaction_id": "txn_123",
    "amount": 99.99,
    "currency": "USD",
    "status": "success",
    "duration_ms": 1234
})

# Multiple contexts
logger.error("payment_failed", {
    "transaction_id": "txn_123",
    "error": "card_declined",
    "error_code": "DECLINED",
    "retry_count": 2,
    "user_id": "user_456"
})
```

### Bad ❌

```python
# Unstructured, unparseable
logger.info(f"Payment processed: txn_123, amount: 99.99, status: success")

# String concatenation
logger.error(f"Payment failed: {transaction_id} - {error}")

# No context
logger.error("Error occurred")
```

---

## Telemetry & Metrics

### Key Metrics to Track

```
API Endpoints:
- Request count (total)
- Request duration (histogram)
- Error rate (percentage)
- Response size

Database:
- Query count
- Query duration (histogram)
- Connection pool usage
- Slow query count

Business Logic:
- Operations total
- Operations failed
- Operation duration

System:
- CPU usage
- Memory usage
- Disk usage
- Active connections
```

### Exporting Metrics

```yaml
metrics:
  enabled: true
  backend: otel
  interval_seconds: 60
  include:
    - http_requests_total
    - http_request_duration_seconds
    - database_query_duration_seconds
```

**Then visualize in:**
- Grafana (with Prometheus)
- DataDog
- New Relic
- CloudMonitoring

---

## Debugging with Logs

### Finding an Issue

```bash
# Search for error
grep "ERROR" logs/app-*.log

# Filter by user
grep "user_id=123" logs/app-*.log

# Filter by operation
grep "payment_failed" logs/app-*.log

# Get context
grep -B5 -A5 "error_line" logs/app-*.log

# Follow trace
grep "trace_id=xyz" logs/app-*.log
```

### Example: Debugging a Bug

```
Step 1: Error appears in monitoring
        ↓
Step 2: Search logs for error
        ERROR: payment_failed, order_id=789
        ↓
Step 3: Get full context
        - Started: 10:34:22
        - User: user_456
        - Amount: $99.99
        - Gateway: stripe
        ↓
Step 4: Check metrics at that time
        - Gateway latency: 2.5s (normal)
        - Gateway error rate: 2% (abnormal!)
        ↓
Step 5: Root cause identified
        Stripe was experiencing elevated error rate
        User should retry
```

---

## Logging Checklist

Before marking work complete:

### Configuration
- [ ] Logging config file created (logging.yaml)
- [ ] All settings configurable via environment vars
- [ ] Sensible defaults work without config
- [ ] Multiple backends configured (file, OTEL, console)
- [ ] Log rotation configured
- [ ] Retention policies set

### Implementation
- [ ] All entry points logged (function entry/exit)
- [ ] All state changes logged
- [ ] All errors logged with full context
- [ ] All external API calls logged
- [ ] All database operations logged
- [ ] Sensitive data NOT logged (passwords, secrets)
- [ ] Structured logging used (JSON)
- [ ] Trace IDs used for tracing

### Telemetry
- [ ] Key metrics identified
- [ ] Metrics exported to OTEL
- [ ] Performance metrics included
- [ ] Error rates tracked

### Testing
- [ ] Logs work in development (can see output)
- [ ] Log files created and rotated correctly
- [ ] Sensitive data sanitized
- [ ] OTEL export tested
- [ ] Log parsing verified (valid JSON)

### Documentation
- [ ] How to configure logging documented
- [ ] How to access logs documented
- [ ] What each logger logs documented
- [ ] How to debug using logs documented

---

## Complete Example

See `LOGGING_STANDARDS.md` for:
- Complete Python implementation
- Complete TypeScript implementation
- Complete Go implementation
- Complete Java implementation
- Real-world debugging example
- Security guidelines
- PII handling
- Log rotation strategies

---

## Resources

- [Python logging](https://docs.python.org/3/library/logging.html)
- [Winston (Node.js)](https://github.com/winstonjs/winston)
- [slog (Go 1.21+)](https://pkg.go.dev/log/slog)
- [Logback (Java)](http://logback.qos.ch/)
- [OpenTelemetry](https://opentelemetry.io/)
- [JSON Logging Best Practices](https://www.kartar.net/2015/12/structured-logging/)

---

## Summary

**Logging is MANDATORY. Every project MUST have:**

- ✅ Centralized configuration
- ✅ Multiple backend support
- ✅ Proper rotation & retention
- ✅ Structured logging (JSON)
- ✅ All critical events logged
- ✅ Full error context
- ✅ Telemetry/metrics
- ✅ Accessible for debugging
- ✅ No sensitive data in logs

**Logging verification required before marking work complete.**

---

**Last Updated:** 2026-07-11  
**Requirement Status:** MANDATORY FOR ALL CODE  
**Verification:** REQUIRED BEFORE COMPLETING WORK  
**See Also:** LOGGING_STANDARDS.md, COMPLETION_CHECKLIST.md
