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
    minor=0,
    patch=8,
    build_date="2026-01-01",
    changelog=[
        "🔧 [FIX] Fixed inline keyboard - reply_markup as dict not JSON string",
        "🔧 [FIX] Added extensive debug logging for polling & commands",
        "🔧 [FIX] Improved chat_id comparison logic",
        "✨ [NEW] Menu buttons hiện ngay khi bot start",
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

