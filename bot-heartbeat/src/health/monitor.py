"""
Health Monitor - Monitor Bot 1 status
"""
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthCheckResult:
    """Result of health check"""
    status: HealthStatus
    message: str
    last_seen: Optional[datetime]
    minutes_ago: Optional[float]
    bot_status: Optional[str] = None
    error: Optional[str] = None
    alert_needed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'message': self.message,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'minutes_ago': self.minutes_ago,
            'bot_status': self.bot_status,
            'error': self.error,
            'alert_needed': self.alert_needed
        }


class HealthMonitor:
    """Monitor Bot 1 health via heartbeat"""
    
    def __init__(
        self,
        db_repository,
        warning_timeout: int = 180,  # 3 minutes
        critical_timeout: int = 600  # 10 minutes
    ):
        self.db = db_repository
        self.warning_timeout = warning_timeout
        self.critical_timeout = critical_timeout
        
        self.last_status = HealthStatus.UNKNOWN
        self.last_alert_time = None
        self.alert_cooldown = 300  # 5 minutes between alerts
    
    def check(self) -> HealthCheckResult:
        """Check Bot 1 health status"""
        status_dict = self.db.check_heartbeat_status(
            timeout_minutes=self.warning_timeout / 60,
            critical_minutes=self.critical_timeout / 60
        )
        
        status = HealthStatus(status_dict['status'])
        
        # Determine if alert is needed
        alert_needed = False
        
        if status == HealthStatus.CRITICAL:
            alert_needed = True
        elif status == HealthStatus.WARNING:
            # Alert if status changed from healthy
            if self.last_status == HealthStatus.HEALTHY:
                alert_needed = True
        
        # Check cooldown
        if alert_needed and self.last_alert_time:
            elapsed = (datetime.utcnow() - self.last_alert_time).total_seconds()
            if elapsed < self.alert_cooldown:
                alert_needed = False
        
        if alert_needed:
            self.last_alert_time = datetime.utcnow()
        
        self.last_status = status
        
        return HealthCheckResult(
            status=status,
            message=status_dict['message'],
            last_seen=status_dict.get('last_seen'),
            minutes_ago=status_dict.get('minutes_ago'),
            bot_status=status_dict.get('bot_status'),
            error=status_dict.get('error'),
            alert_needed=alert_needed
        )
    
    def get_uptime_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Calculate uptime statistics"""
        # This would query heartbeat history
        # For now, return placeholder
        return {
            'period_hours': hours,
            'uptime_percent': 99.5,
            'total_checks': 1440,
            'healthy_checks': 1433,
            'warning_checks': 5,
            'critical_checks': 2
        }

