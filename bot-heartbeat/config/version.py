"""
Bot Version Information - Heartbeat
Updated after each bug fix or feature update
"""
from dataclasses import dataclass
from typing import List


@dataclass
class VersionInfo:
    """Version information for the bot"""
    major: int
    minor: int
    patch: int
    build_date: str
    changelog: List[str]
    
    @property
    def version_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    @property
    def full_version(self) -> str:
        return f"v{self.version_string} ({self.build_date})"


# Current version - UPDATE THIS AFTER EACH RELEASE
CURRENT_VERSION = VersionInfo(
    major=5,
    minor=1,
    patch=0,
    build_date="2026-01-01",
    changelog=[
        "🔧 [OPTIMIZE] Giảm 60% thông báo - chỉ giữ 6 loại quan trọng",
        "🔧 [OPTIMIZE] Gộp trade result + daily progress vào 1 message",
        "🔧 [FIX] Fixed inline keyboard buttons",
        "✨ [NEW] Thêm send_new_day, send_daily_complete, send_alert",
    ]
)


def get_version() -> str:
    """Get current version string"""
    return CURRENT_VERSION.version_string


def get_full_version() -> str:
    """Get full version with date"""
    return CURRENT_VERSION.full_version


def get_version_info() -> VersionInfo:
    """Get current version info object"""
    return CURRENT_VERSION


def get_changelog() -> List[str]:
    """Get current version changelog"""
    return CURRENT_VERSION.changelog

