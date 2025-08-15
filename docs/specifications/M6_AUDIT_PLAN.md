# 🔍 M6 - Audit & Advanced Logging Implementation Plan

**Date**: August 13, 2025  
**Status**: 🚧 PLANNING

## 📋 M6 Tasks Breakdown

### Task 6.1: Enhanced User/Action Audit Logging
- **Current State**: Basic audit in `rate_limit_and_policy.py` 
- **Enhancement**: Add detailed per-user, per-action tracking
- **Components**:
  - User session tracking with unique IDs
  - Action categorization (file ops, code exec, admin)
  - Response time and resource usage logging
  - Failed/successful operation tracking

### Task 6.2: Admin Interface for Audit Logs
- **Component**: New `/admin/audit` endpoints
- **Features**:
  - View logs with filtering (user, date, action type)
  - Search functionality across audit entries
  - Real-time log streaming for monitoring
  - User activity summaries and reports

### Task 6.3: CSV/JSON Export Capabilities
- **Export Formats**: CSV and JSON for audit logs
- **Filtering**: By date range, user, action type, status
- **Features**:
  - Bulk export for compliance reporting
  - Scheduled exports via admin API
  - Compression for large datasets

### Task 6.4: Prometheus Audit Metrics Integration
- **Current**: Basic system metrics in `/metrics`
- **Enhancement**: Add audit-specific metrics
- **Metrics**:
  - Actions per user/hour counters
  - Failed operation rates by type
  - Average response times by endpoint
  - Admin action frequency tracking

## 🏗️ Technical Implementation Strategy

### Phase A: Database Schema Enhancement
```sql
-- Enhanced audit_logs table with detailed tracking
CREATE TABLE IF NOT EXISTS audit_logs_v2 (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(255),
    client_ip INET,
    action_type VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    request_size INTEGER,
    response_size INTEGER,
    response_time_ms INTEGER,
    status_code INTEGER,
    success BOOLEAN,
    resource_usage JSON,
    metadata JSON,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX (user_id, timestamp),
    INDEX (action_type, timestamp),
    INDEX (session_id)
);
```

### Phase B: Enhanced Middleware
- Extend `RateLimitAndPolicyMiddleware` with detailed logging
- Add session tracking and action categorization
- Implement resource usage measurement
- Create audit metrics collection points

### Phase C: Admin API Endpoints
```python
@app.get("/admin/audit/logs")     # View/search logs
@app.get("/admin/audit/export")   # Export logs 
@app.get("/admin/audit/users")    # User activity summary
@app.get("/admin/audit/metrics")  # Real-time audit metrics
@app.get("/admin/audit/stream")   # Live log streaming
```

### Phase D: Prometheus Integration
- Add audit counters to existing `/metrics` endpoint
- Include user activity rates, error rates, response times
- Maintain backward compatibility with current metrics

## 🎯 Success Criteria

1. **Comprehensive Logging**: Every API action logged with full context
2. **Admin Dashboard**: Easy access to audit data via web interface
3. **Export Capability**: Generate compliance reports in CSV/JSON
4. **Monitoring Integration**: Audit metrics in Prometheus format
5. **Performance**: <5ms overhead per request for audit logging

## 🔧 Integration Points

- **Database**: PostgreSQL with enhanced audit tables
- **Current Middleware**: Extend existing audit functionality
- **Metrics System**: Add to current Prometheus `/metrics` endpoint
- **Admin Auth**: Use existing token-based authentication
- **Quotas**: Integrate with M5.x quota system for resource tracking

## 📊 Expected Deliverables

1. Enhanced audit logging middleware
2. Admin interface for log management
3. CSV/JSON export functionality
4. Prometheus audit metrics
5. Database schema migration
6. Documentation and testing

---

**Ready to implement M6 - starting with database schema and middleware enhancements!**
