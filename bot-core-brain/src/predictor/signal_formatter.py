"""
Signal Formatter - Format predictions for Telegram
★ INDEPENDENT - Does not import from core trading logic ★
"""

import logging
from typing import Dict, Any, List

from . import Direction, SignalStrength, PredictionSignal

logger = logging.getLogger(__name__)


class SignalFormatter:
    """
    Format prediction signals for various outputs
    - Telegram messages
    - Console logging
    - JSON export
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def format_telegram_message(self, signal: PredictionSignal) -> str:
        """
        Format signal as Telegram message
        
        Args:
            signal: PredictionSignal to format
        
        Returns:
            Formatted message string
        """
        # Direction emoji
        if signal.direction == Direction.LONG:
            direction_emoji = "🟢 LONG"
            direction_color = "📈"
        elif signal.direction == Direction.SHORT:
            direction_emoji = "🔴 SHORT"
            direction_color = "📉"
        else:
            direction_emoji = "⚪ NEUTRAL"
            direction_color = "➖"
        
        # Strength indicator
        strength_stars = self._get_strength_stars(signal.strength)
        
        # Format indicators
        indicators_text = self._format_indicators(signal.indicators_summary)
        
        # Format reasoning
        reasoning_text = self._format_list(signal.reasoning, "💡")
        
        # Format warnings
        warnings_text = self._format_list(signal.warnings, "⚠️") if signal.warnings else "None"
        
        message = f"""
🔮 BTC PREDICTION SIGNAL
═══════════════════════════

{direction_color} Direction: {direction_emoji}
⭐ Strength: {strength_stars} ({signal.strength.value})
⏰ Time: {signal.timestamp.strftime("%Y-%m-%d %H:%M:%S")} UTC

💰 ENTRY PARAMETERS
├── Current Price: ${signal.current_price:,.2f}
├── Suggested Entry: ${signal.suggested_entry:,.2f}
├── Take Profit: ${signal.suggested_tp:,.2f} (+{signal.tp_percent:.2f}%)
├── Stop Loss: ${signal.suggested_sl:,.2f} (-{signal.sl_percent:.2f}%)
├── Leverage: {signal.suggested_leverage}x
└── Position Size: ${signal.position_size_usd:,.2f}

📈 POTENTIAL OUTCOME
├── Profit if TP: +${signal.potential_profit:,.2f}
├── Loss if SL: -${signal.potential_loss:,.2f}
└── Risk:Reward: 1:{signal.risk_reward_ratio:.1f}

🎯 CONFIDENCE METRICS
├── Overall Confidence: {signal.confidence:.1f}%
├── Win Probability: {signal.win_probability:.1f}%
└── Signal Score: {signal.overall_score:.1f}

📊 KEY INDICATORS
{indicators_text}

🧠 REASONING
{reasoning_text}

⚠️ WARNINGS
{warnings_text}

─────────────────────────
🆔 {signal.prediction_id}
⚡ SUGGESTION ONLY - Not auto-executed
"""
        return message.strip()
    
    def format_short_message(self, signal: PredictionSignal) -> str:
        """Format a shorter summary message"""
        if signal.direction == Direction.LONG:
            emoji = "🟢"
            action = "LONG"
        elif signal.direction == Direction.SHORT:
            emoji = "🔴"
            action = "SHORT"
        else:
            emoji = "⚪"
            action = "NEUTRAL"
        
        return f"""
🔮 BTC Prediction: {emoji} {action}
├── Price: ${signal.current_price:,.2f}
├── TP: ${signal.suggested_tp:,.2f} (+{signal.tp_percent:.1f}%)
├── SL: ${signal.suggested_sl:,.2f} (-{signal.sl_percent:.1f}%)
├── Confidence: {signal.confidence:.0f}%
└── Win Rate: {signal.win_probability:.0f}%

⚡ Suggestion only
"""
    
    def format_console(self, signal: PredictionSignal) -> str:
        """Format for console logging"""
        return (
            f"PREDICTION: {signal.direction.value} | "
            f"Confidence: {signal.confidence:.1f}% | "
            f"Win Prob: {signal.win_probability:.1f}% | "
            f"Score: {signal.overall_score:.1f}"
        )
    
    def _get_strength_stars(self, strength: SignalStrength) -> str:
        """Convert strength to star rating"""
        mapping = {
            SignalStrength.VERY_STRONG: "⭐⭐⭐⭐⭐",
            SignalStrength.STRONG: "⭐⭐⭐⭐",
            SignalStrength.MODERATE: "⭐⭐⭐",
            SignalStrength.WEAK: "⭐⭐"
        }
        return mapping.get(strength, "⭐")
    
    def _format_indicators(self, indicators: Dict[str, float]) -> str:
        """Format indicators dictionary"""
        if not indicators:
            return "└── No indicator data"
        
        lines = []
        indicator_names = list(indicators.keys())
        
        for i, (name, value) in enumerate(indicators.items()):
            is_last = (i == len(indicator_names) - 1)
            prefix = "└──" if is_last else "├──"
            
            # Format based on indicator type
            if name == 'RSI':
                status = self._get_rsi_status(value)
                lines.append(f"{prefix} RSI: {value:.1f} ({status})")
            elif name == 'MACD':
                status = "Bullish" if value > 0 else "Bearish" if value < 0 else "Neutral"
                lines.append(f"{prefix} MACD: {status}")
            elif name == 'EMA':
                lines.append(f"{prefix} EMA9: ${value:,.0f}")
            elif name == 'BB':
                lines.append(f"{prefix} BB Position: {value:.0f}%")
            elif name == 'ADX':
                status = self._get_adx_status(value)
                lines.append(f"{prefix} ADX: {value:.1f} ({status})")
            elif name == 'Funding':
                lines.append(f"{prefix} Funding: {value:.4f}%")
            elif name == 'Volume':
                lines.append(f"{prefix} Volume: {value:.1f}x avg")
            else:
                lines.append(f"{prefix} {name}: {value:.2f}")
        
        return "\n".join(lines)
    
    def _get_rsi_status(self, rsi: float) -> str:
        """Get RSI status text"""
        if rsi > 70:
            return "Overbought"
        elif rsi < 30:
            return "Oversold"
        elif rsi > 60:
            return "High"
        elif rsi < 40:
            return "Low"
        return "Neutral"
    
    def _get_adx_status(self, adx: float) -> str:
        """Get ADX trend status"""
        if adx > 40:
            return "Strong trend"
        elif adx > 25:
            return "Trending"
        elif adx > 15:
            return "Weak trend"
        return "No trend"
    
    def _format_list(self, items: List[str], prefix: str = "•") -> str:
        """Format list items"""
        if not items:
            return f"└── None"
        
        lines = []
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            tree_prefix = "└──" if is_last else "├──"
            lines.append(f"{tree_prefix} {item}")
        
        return "\n".join(lines)

