"""
Admin API Endpoints for Audit Management - M6 Task 6.3
Date: August 13, 2025

Provides admin interface for:
- Viewing/searching audit logs with filtering
- Exporting audit data in CSV/JSON formats
- Real-time log streaming
- User activity summaries
- Admin action tracking
"""

import csv
import gzip
import io
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Import the database connection from our audit middleware
from advanced_audit_middleware import db_connection
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

# Create admin router
admin_router = APIRouter(prefix="/admin/audit", tags=["Admin Audit"])


# Pydantic models for responses
class AuditLogEntry(BaseModel):
    id: int
    session_id: Optional[str]
    user_id: Optional[str]
    request_id: str
    endpoint: str
    http_method: str
    action_type: str
    action_category: str
    client_ip: str
    user_agent: Optional[str]
    request_size: int
    response_size: int
    status_code: int
    success: bool
    response_time_ms: Optional[int]
    cpu_time_ms: Optional[int]
    memory_peak_mb: Optional[int]
    file_path: Optional[str]
    file_size_bytes: Optional[int]
    files_affected: int
    command_type: Optional[str]
    command_text: Optional[str]
    stdout_size: int
    stderr_size: int
    exit_code: Optional[int]
    quota_consumed: Optional[Dict]
    quota_remaining: Optional[Dict]
    quota_violation: bool
    metadata: Optional[Dict]
    error_details: Optional[str]
    timestamp: datetime


class AuditLogResponse(BaseModel):
    logs: List[AuditLogEntry]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    filters_applied: Dict[str, Any]


class UserActivitySummary(BaseModel):
    user_id: str
    user_email: Optional[str]
    total_actions: int
    successful_actions: int
    failed_actions: int
    file_operations: int
    code_executions: int
    admin_actions: int
    quota_violations: int
    first_activity: Optional[datetime]
    last_activity: Optional[datetime]
    avg_response_time_ms: float
    total_cpu_ms: int
    total_memory_mb: int
    unique_sessions: int
    top_endpoints: List[Dict[str, Any]]


class DailySummary(BaseModel):
    summary_date: str
    user_id: str
    total_actions: int
    successful_actions: int
    failed_actions: int
    file_operations: int
    code_executions: int
    admin_actions: int
    avg_response_time_ms: int
    max_response_time_ms: int
    quota_violations: int


class AdminActionEntry(BaseModel):
    id: int
    admin_user_id: str
    target_user_id: Optional[str]
    admin_action_type: str
    old_values: Optional[Dict]
    new_values: Optional[Dict]
    justification: Optional[str]
    timestamp: datetime


# Authentication dependency (placeholder - implement based on your auth system)
async def verify_admin_token(authorization: str = None):
    """Verify admin authorization - implement based on your auth system"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin authorization required")
    # Add your admin token verification logic here
    token = authorization.removeprefix("Bearer ").strip()
    if token != "admin_test_token":  # Replace with real admin verification
        raise HTTPException(status_code=403, detail="Admin access denied")
    return True


@admin_router.get("/logs", response_model=AuditLogResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    action_category: Optional[str] = Query(None, description="Filter by category"),
    endpoint: Optional[str] = Query(None, description="Filter by endpoint"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    quota_violation: Optional[bool] = Query(
        None, description="Filter quota violations"
    ),
    client_ip: Optional[str] = Query(None, description="Filter by client IP"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    search: Optional[str] = Query(
        None, description="Search in error details or metadata"
    ),
    admin_auth=Depends(verify_admin_token),
):
    """Get paginated audit logs with filtering"""

    # Build dynamic query
    where_conditions = []
    params = []
    param_count = 0

    if user_id:
        param_count += 1
        where_conditions.append(f"user_id = ${param_count}")
        params.append(user_id)

    if action_type:
        param_count += 1
        where_conditions.append(f"action_type = ${param_count}")
        params.append(action_type)

    if action_category:
        param_count += 1
        where_conditions.append(f"action_category = ${param_count}")
        params.append(action_category)

    if endpoint:
        param_count += 1
        where_conditions.append(f"endpoint ILIKE ${param_count}")
        params.append(f"%{endpoint}%")

    if success is not None:
        param_count += 1
        where_conditions.append(f"success = ${param_count}")
        params.append(success)

    if quota_violation is not None:
        param_count += 1
        where_conditions.append(f"quota_violation = ${param_count}")
        params.append(quota_violation)

    if client_ip:
        param_count += 1
        where_conditions.append(f"client_ip = ${param_count}")
        params.append(client_ip)

    if start_date:
        param_count += 1
        where_conditions.append(f"timestamp >= ${param_count}")
        params.append(start_date)

    if end_date:
        param_count += 1
        where_conditions.append(f"timestamp <= ${param_count}")
        params.append(end_date)

    if search:
        param_count += 1
        where_conditions.append(
            f"(error_details ILIKE ${param_count} OR metadata::text ILIKE ${param_count})"
        )
        params.append(f"%{search}%")

    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    # Get total count
    count_query = f"SELECT COUNT(*) FROM audit_actions {where_clause}"

    try:
        if not db_connection.pool:
            raise HTTPException(status_code=500, detail="Database not available")

        async with db_connection.pool.acquire() as conn:
            total_count = await conn.fetchval(count_query, *params)

            # Get logs with pagination
            offset = (page - 1) * page_size
            logs_query = f"""
                SELECT * FROM audit_actions 
                {where_clause}
                ORDER BY timestamp DESC 
                LIMIT {page_size} OFFSET {offset}
            """

            rows = await conn.fetch(logs_query, *params)

            logs = [AuditLogEntry(**dict(row)) for row in rows]

            return AuditLogResponse(
                logs=logs,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_next=(page * page_size) < total_count,
                filters_applied={
                    "user_id": user_id,
                    "action_type": action_type,
                    "action_category": action_category,
                    "endpoint": endpoint,
                    "success": success,
                    "quota_violation": quota_violation,
                    "client_ip": client_ip,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "search": search,
                },
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@admin_router.get("/export")
async def export_audit_logs(
    format: str = Query(
        "csv", regex="^(csv|json)$", description="Export format: csv or json"
    ),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    action_category: Optional[str] = Query(None, description="Filter by category"),
    compress: bool = Query(False, description="Compress output with gzip"),
    admin_auth=Depends(verify_admin_token),
):
    """Export audit logs in CSV or JSON format"""

    # Build query with filters
    where_conditions = []
    params = []
    param_count = 0

    if user_id:
        param_count += 1
        where_conditions.append(f"user_id = ${param_count}")
        params.append(user_id)

    if start_date:
        param_count += 1
        where_conditions.append(f"timestamp >= ${param_count}")
        params.append(start_date)

    if end_date:
        param_count += 1
        where_conditions.append(f"timestamp <= ${param_count}")
        params.append(end_date)

    if action_category:
        param_count += 1
        where_conditions.append(f"action_category = ${param_count}")
        params.append(action_category)

    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    try:
        if not db_connection.pool:
            raise HTTPException(status_code=500, detail="Database not available")

        async with db_connection.pool.acquire() as conn:
            query = f"""
                SELECT id, user_id, request_id, endpoint, http_method, action_type, 
                       action_category, client_ip, status_code, success, response_time_ms,
                       cpu_time_ms, memory_peak_mb, quota_violation, timestamp, error_details
                FROM audit_actions 
                {where_clause}
                ORDER BY timestamp DESC
            """

            rows = await conn.fetch(query, *params)

            if format == "csv":
                return await export_as_csv(rows, compress)
            else:
                return await export_as_json(rows, compress)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


async def export_as_csv(rows, compress: bool):
    """Export data as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    if rows:
        writer.writerow(rows[0].keys())

        # Write data
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row.values()])

    content = output.getvalue()
    output.close()

    if compress:
        content_bytes = content.encode("utf-8")
        compressed = gzip.compress(content_bytes)
        return Response(
            content=compressed,
            media_type="application/gzip",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv.gz"
            },
        )
    else:
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            },
        )


async def export_as_json(rows, compress: bool):
    """Export data as JSON"""
    data = []
    for row in rows:
        row_dict = dict(row)
        # Convert datetime to string for JSON serialization
        for key, value in row_dict.items():
            if isinstance(value, datetime):
                row_dict[key] = value.isoformat()
        data.append(row_dict)

    content = json.dumps(data, indent=2, default=str)

    if compress:
        content_bytes = content.encode("utf-8")
        compressed = gzip.compress(content_bytes)
        return Response(
            content=compressed,
            media_type="application/gzip",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.gz"
            },
        )
    else:
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            },
        )


@admin_router.get("/users", response_model=List[UserActivitySummary])
async def get_user_activity_summary(
    days: int = Query(7, ge=1, le=365, description="Days to analyze"),
    min_actions: int = Query(1, ge=0, description="Minimum actions to include user"),
    admin_auth=Depends(verify_admin_token),
):
    """Get user activity summaries"""

    start_date = datetime.utcnow() - timedelta(days=days)

    try:
        if not db_connection.pool:
            raise HTTPException(status_code=500, detail="Database not available")

        async with db_connection.pool.acquire() as conn:
            query = """
                SELECT 
                    aa.user_id,
                    u.email as user_email,
                    COUNT(*) as total_actions,
                    COUNT(*) FILTER (WHERE aa.success) as successful_actions,
                    COUNT(*) FILTER (WHERE NOT aa.success) as failed_actions,
                    COUNT(*) FILTER (WHERE aa.action_category = 'filesystem') as file_operations,
                    COUNT(*) FILTER (WHERE aa.action_category = 'execution') as code_executions,
                    COUNT(*) FILTER (WHERE aa.action_category = 'admin') as admin_actions,
                    COUNT(*) FILTER (WHERE aa.quota_violation) as quota_violations,
                    MIN(aa.timestamp) as first_activity,
                    MAX(aa.timestamp) as last_activity,
                    AVG(aa.response_time_ms)::int as avg_response_time_ms,
                    SUM(COALESCE(aa.cpu_time_ms, 0)) as total_cpu_ms,
                    SUM(COALESCE(aa.memory_peak_mb, 0)) as total_memory_mb,
                    COUNT(DISTINCT aa.session_id) as unique_sessions
                FROM audit_actions aa
                LEFT JOIN users u ON aa.user_id = u.id::text
                WHERE aa.timestamp >= $1
                GROUP BY aa.user_id, u.email
                HAVING COUNT(*) >= $2
                ORDER BY total_actions DESC
            """

            rows = await conn.fetch(query, start_date, min_actions)

            summaries = []
            for row in rows:
                # Get top endpoints for this user
                endpoints_query = """
                    SELECT endpoint, COUNT(*) as count
                    FROM audit_actions
                    WHERE user_id = $1 AND timestamp >= $2
                    GROUP BY endpoint
                    ORDER BY count DESC
                    LIMIT 5
                """
                endpoint_rows = await conn.fetch(
                    endpoints_query, row["user_id"], start_date
                )
                top_endpoints = [
                    {"endpoint": ep["endpoint"], "count": ep["count"]}
                    for ep in endpoint_rows
                ]

                summary = UserActivitySummary(
                    user_id=row["user_id"],
                    user_email=row["user_email"],
                    total_actions=row["total_actions"],
                    successful_actions=row["successful_actions"],
                    failed_actions=row["failed_actions"],
                    file_operations=row["file_operations"],
                    code_executions=row["code_executions"],
                    admin_actions=row["admin_actions"],
                    quota_violations=row["quota_violations"],
                    first_activity=row["first_activity"],
                    last_activity=row["last_activity"],
                    avg_response_time_ms=row["avg_response_time_ms"] or 0,
                    total_cpu_ms=row["total_cpu_ms"],
                    total_memory_mb=row["total_memory_mb"],
                    unique_sessions=row["unique_sessions"],
                    top_endpoints=top_endpoints,
                )
                summaries.append(summary)

            return summaries

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@admin_router.get("/daily-summaries", response_model=List[DailySummary])
async def get_daily_summaries(
    days: int = Query(30, ge=1, le=365, description="Days to retrieve"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    admin_auth=Depends(verify_admin_token),
):
    """Get daily audit summaries"""

    try:
        if not db_connection.pool:
            raise HTTPException(status_code=500, detail="Database not available")

        async with db_connection.pool.acquire() as conn:
            where_clause = (
                "WHERE summary_date >= CURRENT_DATE - INTERVAL '%s days'" % days
            )
            params = []

            if user_id:
                where_clause += " AND user_id = $1"
                params.append(user_id)

            query = f"""
                SELECT summary_date::text, user_id, total_actions, successful_actions,
                       failed_actions, file_operations, code_executions, admin_actions,
                       avg_response_time_ms, max_response_time_ms, quota_violations
                FROM audit_daily_summaries
                {where_clause}
                ORDER BY summary_date DESC, total_actions DESC
            """

            rows = await conn.fetch(query, *params)

            return [DailySummary(**dict(row)) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@admin_router.get("/admin-actions", response_model=List[AdminActionEntry])
async def get_admin_actions(
    days: int = Query(30, ge=1, le=365, description="Days to retrieve"),
    admin_user_id: Optional[str] = Query(None, description="Filter by admin user"),
    admin_auth=Depends(verify_admin_token),
):
    """Get admin action history"""

    start_date = datetime.utcnow() - timedelta(days=days)

    try:
        if not db_connection.pool:
            raise HTTPException(status_code=500, detail="Database not available")

        async with db_connection.pool.acquire() as conn:
            where_clause = "WHERE timestamp >= $1"
            params = [start_date]

            if admin_user_id:
                where_clause += " AND admin_user_id = $2"
                params.append(admin_user_id)

            query = f"""
                SELECT id, admin_user_id, target_user_id, admin_action_type,
                       old_values, new_values, justification, timestamp
                FROM audit_admin_actions
                {where_clause}
                ORDER BY timestamp DESC
            """

            rows = await conn.fetch(query, *params)

            return [AdminActionEntry(**dict(row)) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@admin_router.get("/metrics")
async def get_audit_metrics(admin_auth=Depends(verify_admin_token)):
    """Get real-time audit metrics in Prometheus format"""
    from advanced_audit_middleware import get_audit_metrics

    return Response(content=get_audit_metrics(), media_type="text/plain")


# Add to your main FastAPI app:
# app.include_router(admin_router)
