"""
Bot Version Information
Updated after each bug fix or feature update
"""
from dataclasses import dataclass
from typing import List
from datetime import datetime


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
    patch=7,
    build_date="2026-01-01",
    changelog=[
        "🔧 [FIX] Fixed inline keyboard - removed double JSON serialization",
        "🔧 [FIX] Improved chat_id comparison logic",
        "🔧 [FIX] Added debug logging for command handling",
        "✨ [NEW] Menu buttons hiện ngay khi bot start",
    ]
)

# Version history
VERSION_HISTORY = [
    VersionInfo(
        major=5,
        minor=0,
        patch=2,
        build_date="2026-01-01",
        changelog=[
            "🔴 [CRITICAL] Fixed: Gate 2 validates direction vs regime",
            "🔴 [CRITICAL] Fixed: Strategies respect regime direction",
            "🟡 [HIGH] Fixed: AI mock prediction logic",
            "✨ [NEW] Added: /version command",
        ]
    ),
    VersionInfo(
        major=5,
        minor=0,
        patch=1,
        build_date="2025-12-30",
        changelog=[
            "Initial v5.0 release",
            "5-Gate System implementation",
            "100 BTC-specific features",
            "Ensemble AI model (XGB + LGB + LR)",
        ]
    ),
    VersionInfo(
        major=5,
        minor=0,
        patch=0,
        build_date="2025-12-28",
        changelog=[
            "Bot architecture redesign",
            "Split into Core Brain + Heartbeat",
        ]
    ),
]


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


def format_version_message() -> str:
    """Format version info for Telegram message"""
    lines = [
        f"🤖 **BTC Trading Bot**",
        f"📦 Version: `{CURRENT_VERSION.full_version}`",
        "",
        "📝 **Changelog:**"
    ]
    
    for item in CURRENT_VERSION.changelog:
        lines.append(f"  • {item}")
    
    lines.extend([
        "",
        f"🕐 Build Date: {CURRENT_VERSION.build_date}",
        f"🔧 Core Brain + Heartbeat Architecture"
    ])
    
    return "\n".join(lines)

