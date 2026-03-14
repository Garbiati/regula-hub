from pydantic import BaseModel


class DependencyCheck(BaseModel):
    status: str
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "regulahub"
    version: str
    uptime_seconds: float
    timestamp: str
    checks: dict[str, DependencyCheck] = {}
