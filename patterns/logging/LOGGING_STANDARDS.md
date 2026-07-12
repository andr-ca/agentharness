---
name: logging-telemetry-standards
description: Mandatory logging and telemetry standards - centrally configured, multi-backend support
complexity: medium
frameworks: all
languages: all
---

# Logging & Telemetry Standards

Comprehensive logging and telemetry requirements for all code. Logging is MANDATORY and must be verified before marking work complete.

## 🚨 CRITICAL REQUIREMENT

**ALL CODE MUST HAVE PROPER LOGGING AND TELEMETRY**

This is non-negotiable:
- ✅ **Everything must be logged** (application events, errors, state changes)
- ✅ **Centrally configured** (one place to manage all logging)
- ✅ **Multiple backends supported** (local files, OTEL, terminal, etc.)
- ✅ **Proper rotation & segmentation** (by time, size, functionality, criticality)
- ✅ **Detailed debugging always available** (logs enable root cause analysis)
- ✅ **Sensible defaults** (works without configuration, optimizes with configuration)
- ✅ **Must be checked before marking work complete** (logging verification required)

**Code shipped without logging and telemetry WILL NOT BE ACCEPTED.**

---

## Why Logging is Non-Negotiable

### The Problem Without Proper Logging

- ❌ Production issues are a mystery (no visibility)
- ❌ Debugging takes days (no audit trail)
- ❌ Can't reproduce issues (no context)
- ❌ Performance problems invisible (no metrics)
- ❌ Security incidents undetected (no audit logs)
- ❌ User issues unverifiable (no activity logs)

### What Proper Logging Solves

- ✅ Issues diagnosed in minutes (detailed logs)
- ✅ Root cause analysis (full context available)
- ✅ Issues reproducible with logs (audit trail)
- ✅ Performance visible (metrics logged)
- ✅ Security incidents detected (audit logs)
- ✅ User issues verifiable (activity logs)
- ✅ System health monitored (telemetry)

---

## Logging Architecture

### Components

```
Application Code
     ↓
   Logger (local capture)
     ↓
    Formatter (JSON, structured text, etc.)
     ↓
   Processors (add context, trace IDs, etc.)
     ↓
┌─────────────────────────────────────────┐
│         Central Configuration           │
│  (defines backends, rotation, levels)  │
└─────────────────────────────────────────┘
     ↓
  ┌──────────────────────────────────────────┐
  │       Multiple Backends (configured)     │
  ├──────────────────────────────────────────┤
  │ • Local files (with rotation)           │
  │ • OpenTelemetry (OTEL)                  │
  │ • Terminal/console                      │
  │ • Cloud logging (CloudLogging, etc.)    │
  │ • Metrics collector                     │
  └──────────────────────────────────────────┘
     ↓
  ┌──────────────────────────────────────────┐
  │    Aggregation & Visualization           │
  ├──────────────────────────────────────────┤
  │ • Logs: ELK, Loki, CloudLogging         │
  │ • Traces: Jaeger, DataDog, NewRelic     │
  │ • Metrics: Prometheus, CloudMonitoring   │
  │ • Dashboards: Grafana, CloudConsole      │
  └──────────────────────────────────────────┘
```

---

## Log Levels (Standard)

### Severity Hierarchy

```
TRACE    - Most detailed (variable values, flow tracking)
DEBUG    - Detailed information (useful during development)
INFO     - General informational messages (important events)
WARN     - Warning messages (something unexpected)
ERROR    - Error messages (operation failed)
CRITICAL - Critical errors (system failure)
```

### When to Use Each Level

#### TRACE (Development Only)
```python
logger.trace("Entering process_payment() with amount=${amount}, user_id=${user_id}")
logger.trace("After validation: status=${status}, items=${len(items)}")
```
**Use for:** Variable inspection, function entry/exit, detailed flow

#### DEBUG (Development & Troubleshooting)
```python
logger.debug("Payment processor initialized with gateway=stripe")
logger.debug("Attempting payment with retry_count=3")
logger.debug("Response from payment gateway: status_code=${status}, time_ms=${duration}")
```
**Use for:** Configuration, decisions, detailed context

#### INFO (Normal Operation)
```python
logger.info("User logged in", {"user_id": "123", "method": "password"})
logger.info("Payment processed", {"order_id": "456", "amount": 99.99, "status": "success"})
logger.info("Daily batch job completed", {"records_processed": 10000, "duration_s": 45})
```
**Use for:** Major milestones, important events, state changes

#### WARN (Unusual but Handled)
```python
logger.warning("Rate limit approaching", {"current": 45000, "limit": 50000})
logger.warning("Retry after failure", {"attempt": 2, "delay_ms": 1000})
logger.warning("Database connection slow", {"query_time_ms": 5000, "threshold_ms": 1000})
```
**Use for:** Unusual situations, degraded performance, recovering from issues

#### ERROR (Operation Failed)
```python
logger.error("Payment failed", {"order_id": "456", "reason": "card_declined", "error": str(e)})
logger.error("Database query failed", {"query": "SELECT...", "error": str(e)})
logger.error("API request failed", {"url": url, "status_code": 500, "retry": true})
```
**Use for:** Operations that failed, errors caught and handled

#### CRITICAL (System Failure)
```python
logger.critical("Out of memory", {"used_gb": 15.8, "available_gb": 0.2})
logger.critical("Database unavailable", {"host": "db.example.com", "error": str(e)})
logger.critical("Authentication system down", {"affected_services": 5})
```
**Use for:** System-level failures, unrecoverable errors, manual intervention required

---

## Structured Logging (Mandatory)

### Always Use Structured Logging

**DON'T:** Unstructured string logging
```python
# ❌ WRONG: Can't parse or search
logger.info(f"User 123 logged in at {datetime.now()} from IP 192.168.1.1")
logger.error(f"Failed to process order {order_id}: {error_message}")
```

**DO:** Structured logging with fields
```python
# ✅ RIGHT: Machine-readable, searchable
logger.info("user_login", {
    "user_id": "123",
    "timestamp": datetime.now().isoformat(),
    "ip_address": "192.168.1.1",
    "method": "password"
})

logger.error("order_processing_failed", {
    "order_id": order_id,
    "error": str(error),
    "error_code": error.code,
    "user_id": user_id
})
```

### Structured Logging Benefits

- ✅ **Searchable** – Query by field value
- ✅ **Parseable** – JSON or key=value format
- ✅ **Consistent** – Standard structure
- ✅ **Rich** – Multiple fields per log
- ✅ **Aggregate-able** – Count errors by type

---

## Central Configuration

### Configuration File (Single Source of Truth)

Create `config/logging.yaml` (or `.toml`, `.json`):

```yaml
# logging.yaml - Central logging configuration
# All logging configuration in one place
# Environment variables override defaults

logging:
  # Default log level (can be overridden per logger)
  level: ${LOG_LEVEL:-INFO}
  
  # Log format (JSON for machine, text for humans)
  format: ${LOG_FORMAT:-json}
  
  # Include structured fields in every log
  context:
    environment: ${ENVIRONMENT:-development}
    service: ${SERVICE_NAME:-my-app}
    version: ${APP_VERSION:-unknown}
    hostname: ${HOSTNAME}
  
  # Backends (where logs go)
  backends:
    # Local file logging
    file:
      enabled: true
      path: ${LOG_FILE_PATH:-./logs}
      filename_pattern: "app-{date}.log"
      rotation:
        type: "daily"              # daily, size, or both
        max_size_mb: 100          # Max file size before rotation
        max_age_days: 30          # Keep logs for 30 days
        max_backups: 10           # Keep 10 backup files
      
    # OTEL (OpenTelemetry)
    otel:
      enabled: ${OTEL_ENABLED:-false}
      endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:-localhost:4317}
      protocol: ${OTEL_EXPORTER_OTLP_PROTOCOL:-grpc}
      batch_size: 1024
      export_interval_ms: 5000
    
    # Terminal/console logging
    console:
      enabled: ${LOG_CONSOLE:-true}
      level: ${LOG_CONSOLE_LEVEL:-DEBUG}
      colorize: ${LOG_COLORIZE:-true}
    
    # Cloud logging (GCP, AWS, Azure)
    cloud:
      enabled: ${CLOUD_LOGGING_ENABLED:-false}
      provider: ${CLOUD_PROVIDER:-gcp}  # gcp, aws, azure
      # Provider-specific config
      gcp:
        project_id: ${GCP_PROJECT_ID}
        log_name: ${SERVICE_NAME}
      aws:
        log_group: ${LOG_GROUP:-/aws/lambda/my-function}
        log_stream: ${LOG_STREAM:-latest}
  
  # Segmentation by functionality/criticality
  loggers:
    # Auth logging (high criticality)
    auth:
      level: DEBUG
      backend: [file, otel, cloud]
      retention_days: 90
      fields:
        - user_id
        - ip_address
        - action
        - result
    
    # Database logging (high criticality)
    database:
      level: INFO
      backend: [file, otel]
      retention_days: 30
      fields:
        - query_time_ms
        - rows_affected
        - error
    
    # API logging (medium criticality)
    api:
      level: INFO
      backend: [file, console]
      retention_days: 7
      fields:
        - method
        - path
        - status_code
        - response_time_ms
    
    # Business logic (medium criticality)
    business:
      level: INFO
      backend: [file, console]
      retention_days: 30
      fields:
        - operation
        - result
        - user_id
    
    # Third-party libs (low criticality)
    external:
      level: WARN
      backend: [file]
      retention_days: 7
  
  # Metrics/Telemetry
  metrics:
    enabled: true
    backend: otel
    interval_seconds: 60
    include:
      - request_duration
      - error_rate
      - cpu_usage
      - memory_usage
      - active_connections
```

### Environment-Based Configuration

```bash
# development.env
LOG_LEVEL=DEBUG
LOG_FORMAT=text
LOG_CONSOLE=true
OTEL_ENABLED=false

# staging.env
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_CONSOLE=false
OTEL_ENABLED=true
CLOUD_LOGGING_ENABLED=true

# production.env
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_CONSOLE=false
OTEL_ENABLED=true
CLOUD_LOGGING_ENABLED=true
LOG_FILE_PATH=/var/log/app
```

---

## Implementation by Language

### Python

```python
import logging
import logging.config
import json
from pythonjsonlogger import jsonlogger
import yaml
import os

# Load configuration
with open('config/logging.yaml') as f:
    config = yaml.safe_load(f)

# Substitute environment variables
def substitute_env(value):
    if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
        parts = value[2:-1].split(':-')
        return os.getenv(parts[0], parts[1] if len(parts) > 1 else '')
    return value

# Setup logging from config
logging.config.dictConfig(config['logging'])

# Get logger for a module
logger = logging.getLogger('business')

# Usage
logger.info("operation_completed", extra={
    "operation": "payment_processing",
    "status": "success",
    "amount": 99.99,
    "duration_ms": 1234
})

logger.error("operation_failed", extra={
    "operation": "payment_processing",
    "error": str(e),
    "error_code": "card_declined"
})
```

**Setup (requirements.txt):**
```
python-json-logger>=2.0.0
pyyaml>=6.0
opentelemetry-api>=1.0.0
opentelemetry-sdk>=1.0.0
opentelemetry-exporter-otlp>=1.0.0
```

### TypeScript/Node.js

```typescript
import winston from 'winston';
import * as fs from 'fs';
import * as yaml from 'js-yaml';
import path from 'path';

// Load configuration
const configPath = path.join(process.cwd(), 'config', 'logging.yaml');
const config = yaml.load(fs.readFileSync(configPath, 'utf8')) as any;

// Substitute environment variables
function substituteEnv(value: any): any {
  if (typeof value === 'string' && value.match(/^\$\{.*\}$/)) {
    const [key, defaultValue] = value.slice(2, -1).split(':-');
    return process.env[key] || defaultValue || '';
  }
  return value;
}

// Create logger
const logger = winston.createLogger({
  level: substituteEnv(config.logging.level),
  format: winston.format.json(),
  defaultMeta: {
    service: substituteEnv(config.logging.context.service),
    version: substituteEnv(config.logging.context.version)
  },
  transports: [
    // File transport
    new winston.transports.File({
      filename: path.join(substituteEnv(config.logging.backends.file.path), 'error.log'),
      level: 'error'
    }),
    // Combined transport
    new winston.transports.File({
      filename: path.join(substituteEnv(config.logging.backends.file.path), 'combined.log')
    })
  ]
});

// Console in development
if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.simple()
  }));
}

// Usage
logger.info('Operation completed', {
  operation: 'payment_processing',
  status: 'success',
  amount: 99.99,
  duration_ms: 1234
});

logger.error('Operation failed', {
  operation: 'payment_processing',
  error: error.message,
  error_code: 'card_declined'
});

export default logger;
```

**Setup (package.json):**
```json
{
  "dependencies": {
    "winston": "^3.8.0",
    "js-yaml": "^4.1.0"
  },
  "devDependencies": {
    "@types/node": "^18.0.0"
  }
}
```

### Go

```go
package main

import (
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/go-logr/logr"
	"gopkg.in/yaml.v3"
	"go.opentelemetry.io/otel"
)

// LogConfig represents logging configuration
type LogConfig struct {
	Level string `yaml:"level"`
	Format string `yaml:"format"`
	Backends struct {
		File struct {
			Enabled bool `yaml:"enabled"`
			Path string `yaml:"path"`
		} `yaml:"file"`
		Console struct {
			Enabled bool `yaml:"enabled"`
		} `yaml:"console"`
		OTEL struct {
			Enabled bool `yaml:"enabled"`
			Endpoint string `yaml:"endpoint"`
		} `yaml:"otel"`
	} `yaml:"backends"`
}

// LoadConfig loads logging configuration
func LoadConfig(path string) (*LogConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var config LogConfig
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, err
	}

	return &config, nil
}

// SetupLogging initializes structured logging
func SetupLogging(config *LogConfig) logr.Logger {
	// Create JSON handler
	opts := &slog.HandlerOptions{
		Level: getLevel(config.Level),
	}

	// Use default handler
	handler := slog.NewJSONHandler(os.Stdout, opts)
	logger := slog.New(handler)
	slog.SetDefault(logger)

	return nil // Go 1.21+ uses slog directly
}

func getLevel(level string) slog.Level {
	switch level {
	case "DEBUG":
		return slog.LevelDebug
	case "INFO":
		return slog.LevelInfo
	case "WARN":
		return slog.LevelWarn
	case "ERROR":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}

// Usage
func main() {
	config, err := LoadConfig("config/logging.yaml")
	if err != nil {
		slog.Error("Failed to load config", "error", err)
		os.Exit(1)
	}

	SetupLogging(config)

	// Structured logging
	slog.Info("operation_completed", 
		"operation", "payment_processing",
		"status", "success",
		"amount", 99.99,
		"duration_ms", 1234,
	)

	slog.Error("operation_failed",
		"operation", "payment_processing",
		"error", "card_declined",
	)
}
```

**Setup (go.mod):**
```
require (
    gopkg.in/yaml.v3 v3.0.0
)
```

### Java

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.core.util.FileUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import net.logstash.logback.encoder.LogstashEncoder;

public class LoggingSetup {
    private static final Logger logger = LoggerFactory.getLogger("business");

    public static void initialize() {
        // Logback is configured via logback-spring.xml or logback.xml
        // See: src/main/resources/logback-spring.xml
    }

    public static void main(String[] args) {
        initialize();

        // Structured logging
        logger.info("Operation completed: {}", new ObjectMapper().writeValueAsString(Map.of(
            "operation", "payment_processing",
            "status", "success",
            "amount", 99.99,
            "duration_ms", 1234
        )));

        logger.error("Operation failed: {}", new ObjectMapper().writeValueAsString(Map.of(
            "operation", "payment_processing",
            "error", "card_declined"
        )));
    }
}
```

**Configuration (src/main/resources/logback-spring.xml):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <!-- File appender with rotation -->
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>logs/app.log</file>
        <encoder class="net.logstash.logback.encoder.LogstashEncoder"/>
        
        <rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
            <fileNamePattern>logs/app-%d{yyyy-MM-dd}.%i.log.gz</fileNamePattern>
            <maxFileSize>100MB</maxFileSize>
            <maxHistory>30</maxHistory>
        </rollingPolicy>
    </appender>

    <!-- Console appender -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="ch.qos.logback.classic.encoder.PatternLayoutEncoder">
            <pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>

    <!-- Root logger -->
    <root level="${LOG_LEVEL:-INFO}">
        <appender-ref ref="FILE"/>
        <appender-ref ref="CONSOLE"/>
    </root>
</configuration>
```

---

## What to Log

### ALWAYS Log These Events

#### Authentication & Security
```
✅ User login attempt (success & failure)
✅ User logout
✅ Password change
✅ Permission change
✅ API key generated/revoked
✅ Authentication failure reason
✅ Unusual access patterns
```

#### Operations & State Changes
```
✅ Major operation started (with ID for tracing)
✅ Operation completed (with duration, result)
✅ Operation failed (with error, retry info)
✅ State transitions
✅ Configuration changes
✅ Data modifications (PII-safe logging)
```

#### Performance & Errors
```
✅ Slow operations (with duration threshold)
✅ Errors & exceptions (full stack trace)
✅ Database query failures
✅ API call failures
✅ Resource exhaustion (memory, connections)
✅ Performance degradation
```

#### Integration Points
```
✅ External API calls (request & response)
✅ Database operations
✅ Cache hits/misses
✅ Message queue operations
✅ Third-party service calls
```

### NEVER Log These (Security)

```
❌ Passwords
❌ API keys / secrets
❌ Credit card numbers
❌ Social security numbers
❌ Private keys
❌ Sensitive PII (unless absolutely necessary & sanitized)
❌ Full request/response bodies with secrets
```

### How to Handle Sensitive Data

```python
# ✅ Log sanitized version
logger.info("user_authentication", {
    "user_id": "123",
    "method": "password",
    # Don't log the password!
    "success": True,
    "ip_address": "192.168.1.1"
})

# ✅ Mask sensitive fields
def mask_sensitive(data):
    if 'credit_card' in data:
        data['credit_card'] = data['credit_card'][-4:].rjust(len(data['credit_card']), '*')
    if 'api_key' in data:
        data['api_key'] = '[REDACTED]'
    return data

logger.info("api_request", mask_sensitive(request_data))
```

---

## Log Rotation & Retention

### File Rotation Strategy

```yaml
rotation:
  # Daily rotation
  type: daily
  filename_pattern: "app-{yyyy-MM-dd}.log"
  
  # OR size-based rotation
  type: size
  max_size_mb: 100
  filename_pattern: "app.{increment}.log"
  
  # OR combined
  type: combined
  max_size_mb: 100
  max_age_days: 1
  
  # Retention policy
  max_age_days: 30      # Delete logs older than 30 days
  max_backups: 10       # Keep max 10 backup files
  compress: true        # Compress archived logs
```

### Retention by Severity

```
CRITICAL:  90 days (keep longer for auditing)
ERROR:     30 days
WARN:      14 days
INFO:      7 days
DEBUG:     1 day (development only)
TRACE:     Never (development only)
```

### Retention by Functionality

```
Authentication:  90 days (compliance)
Database:       30 days
API:            7 days
Business Logic: 30 days
Third-party:    7 days
```

---

## Telemetry & Metrics

### What to Measure

```yaml
Metrics:
  # Request/Response
  - request_count (total requests)
  - request_duration_ms (histogram)
  - request_error_rate (percentage)
  - response_size_bytes
  
  # Database
  - query_count
  - query_duration_ms (histogram)
  - query_error_count
  - connection_pool_usage (gauge)
  
  # Business
  - operations_total (counter)
  - operations_failed_total (counter)
  - operations_duration_ms (histogram)
  
  # System
  - cpu_usage_percent (gauge)
  - memory_usage_bytes (gauge)
  - disk_usage_bytes (gauge)
  - active_connections (gauge)
```

### Exporting to OTEL

```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Setup OTEL
exporter = OTLPMetricExporter(endpoint="localhost:4317")
reader = PeriodicExportingMetricReader(exporter)
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

# Get meter
meter = metrics.get_meter(__name__)

# Create metrics
request_counter = meter.create_counter("http_requests_total")
request_duration = meter.create_histogram("http_request_duration_seconds")

# Record metrics
request_counter.add(1, {"method": "GET", "path": "/api/users"})
request_duration.record(0.123, {"method": "GET", "path": "/api/users"})
```

---

## Logging Checklist (Before Marking Work Complete)

### ✅ Logging Configuration

- [ ] Logging configuration file created (`config/logging.yaml` or equivalent)
- [ ] All settings are configurable via environment variables
- [ ] Sensible defaults provided (works without configuration)
- [ ] Multiple backends configured (file, OTEL, console, etc.)
- [ ] Log rotation configured (daily or size-based)
- [ ] Retention policies set (by severity and functionality)
- [ ] Log levels appropriate for each logger

### ✅ Logging Implementation

- [ ] All entry points logged (function entry/exit for critical paths)
- [ ] All state changes logged
- [ ] All errors & exceptions logged with context
- [ ] All external API calls logged (request & response)
- [ ] All database operations logged
- [ ] Sensitive data NOT logged (passwords, secrets, PII)
- [ ] Structured logging used (JSON or key=value)
- [ ] Trace IDs used for distributed tracing
- [ ] Request context preserved in logs

### ✅ Telemetry

- [ ] Key metrics identified and configured
- [ ] Metrics exported to OTEL (if enabled)
- [ ] Performance metrics included (duration, throughput)
- [ ] Error rates tracked
- [ ] System metrics collected (CPU, memory)

### ✅ Testing

- [ ] Logs tested in development (can see output)
- [ ] Log files created and rotated correctly
- [ ] Sensitive data sanitized in logs
- [ ] OTEL export tested (if configured)
- [ ] Log parsing verified (JSON valid, parseable)

### ✅ Documentation

- [ ] Logging configuration documented
- [ ] How to access logs documented
- [ ] How to configure logging documented
- [ ] What each logger logs documented
- [ ] How to debug using logs documented

---

## Complete Logging Example

### Configuration (config/logging.yaml)

```yaml
logging:
  level: ${LOG_LEVEL:-INFO}
  format: ${LOG_FORMAT:-json}
  
  context:
    environment: ${ENVIRONMENT:-development}
    service: ${SERVICE_NAME:-api}
    version: ${APP_VERSION:-1.0.0}
  
  backends:
    file:
      enabled: true
      path: ${LOG_PATH:-./logs}
      rotation:
        type: daily
        max_age_days: 30
        compress: true
    
    console:
      enabled: true
      level: ${CONSOLE_LOG_LEVEL:-DEBUG}
    
    otel:
      enabled: ${OTEL_ENABLED:-false}
      endpoint: ${OTEL_ENDPOINT:-localhost:4317}
  
  loggers:
    auth:
      level: DEBUG
      retention_days: 90
    database:
      level: INFO
      retention_days: 30
    api:
      level: INFO
      retention_days: 7
```

### Implementation (Python)

```python
import logging
import yaml
import os
from pythonjsonlogger import jsonlogger

# Load config
def load_logging_config():
    with open('config/logging.yaml') as f:
        return yaml.safe_load(f)

config = load_logging_config()

# Setup root logger
root_logger = logging.getLogger()
root_logger.setLevel(config['logging']['level'])

# File handler
file_handler = logging.FileHandler(
    os.path.join(config['logging']['backends']['file']['path'], 'app.log')
)
file_handler.setFormatter(jsonlogger.JsonFormatter())
root_logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
root_logger.addHandler(console_handler)

# Get logger
logger = logging.getLogger('api')

# Usage
def process_order(order_id):
    logger.info("order_processing_started", extra={
        "order_id": order_id,
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        # Process order
        result = validate_order(order_id)
        
        logger.info("order_validated", extra={
            "order_id": order_id,
            "status": "valid"
        })
        
        return result
        
    except Exception as e:
        logger.error("order_processing_failed", extra={
            "order_id": order_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        })
        raise
```

---

## Never Ship Without Logging

**Acceptance Criteria for Production Deployment:**

- ✅ Centralized logging configured and working
- ✅ All critical paths logged
- ✅ All errors logged with full context
- ✅ Telemetry/metrics configured
- ✅ Logs accessible for debugging
- ✅ Log rotation working
- ✅ OTEL export working (if configured)
- ✅ Sensitive data NOT in logs
- ✅ Log levels appropriate
- ✅ Dashboards/alerts configured for key metrics

**If ANY of these are missing, the code is NOT READY FOR PRODUCTION.**

---

## Debugging with Logs

### Finding a Bug in Production

```bash
# 1. Search logs for error
grep "operation_failed" logs/app-*.log

# 2. Get context around error
grep -B5 -A5 "order_id=123" logs/app-*.log

# 3. Follow trace ID across services
grep "trace_id=abc123" logs/*.log

# 4. Check metrics at time of error
# Look at dashboard for CPU, memory, errors at that timestamp

# 5. Reconstruct user actions
grep "user_id=456" logs/app-*.log | sort by timestamp
```

### Example: Debugging a Payment Failure

```
1. Error log:
   ERROR operation_failed order_id=789 error=payment_declined

2. Search for context:
   grep -B10 "order_id=789" logs/app-2024-01-15.log
   
   Shows:
   - Payment initiated at 10:34:22
   - User from IP 192.168.1.1
   - Amount $99.99
   - Using Stripe gateway
   - Attempt 1 failed at 10:34:25
   - Retry at 10:34:30
   - Attempt 2 failed at 10:34:35
   
3. Check telemetry:
   - Gateway response time: 2.5s (normal)
   - Gateway error rate: 2% (abnormal)
   - Currency mismatch? No
   - Card valid? No (in metadata)
   
4. Root cause: Card was declined by bank
   User should retry with different card
```

---

## Summary

**Logging is MANDATORY. Never ship code without:**

- ✅ Centralized configuration
- ✅ Multiple backend support
- ✅ Proper rotation & retention
- ✅ Structured logging
- ✅ All critical events logged
- ✅ Full error context
- ✅ Telemetry/metrics
- ✅ Accessible for debugging
- ✅ No sensitive data in logs

**Verification required before marking work complete.**

---

**Last Updated:** 2026-07-11  
**Requirement Status:** MANDATORY, NON-NEGOTIABLE  
**Verification:** REQUIRED BEFORE MARKING WORK COMPLETE  
**See Also:** COMPLETION_CHECKLIST.md, CODING_GUIDELINES.md
