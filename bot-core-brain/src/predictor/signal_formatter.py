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
        """Format indicators dictionary with detailed annotations"""
        if not indicators:
            return "└── No indicator data"
        
        lines = []
        indicator_names = list(indicators.keys())
        
        for i, (name, value) in enumerate(indicators.items()):
            is_last = (i == len(indicator_names) - 1)
            prefix = "└──" if is_last else "├──"
            
            # Format based on indicator type with detailed annotations
            if name == 'RSI':
                signal, annotation = self._get_rsi_annotation(value)
                lines.append(f"{prefix} RSI: {value:.1f} {signal}")
                lines.append(f"    {annotation}")
            elif name == 'MACD':
                signal, annotation = self._get_macd_annotation(value)
                lines.append(f"{prefix} MACD: {signal}")
                lines.append(f"    {annotation}")
            elif name == 'EMA':
                lines.append(f"{prefix} EMA9: ${value:,.0f}")
                lines.append(f"    📗 EMA9 > EMA21 > EMA50 = LONG")
                lines.append(f"    📕 EMA9 < EMA21 < EMA50 = SHORT")
            elif name == 'BB':
                signal, annotation = self._get_bb_annotation(value)
                lines.append(f"{prefix} BB: {value:.0f}% {signal}")
                lines.append(f"    {annotation}")
            elif name == 'ADX':
                signal, annotation = self._get_adx_annotation(value)
                lines.append(f"{prefix} ADX: {value:.1f} {signal}")
                lines.append(f"    {annotation}")
            elif name == 'Funding':
                signal, annotation = self._get_funding_annotation(value)
                lines.append(f"{prefix} Funding: {value:.4f}% {signal}")
                lines.append(f"    {annotation}")
            elif name == 'Volume':
                signal, annotation = self._get_volume_annotation(value)
                lines.append(f"{prefix} Volume: {value:.1f}x {signal}")
                lines.append(f"    {annotation}")
            elif name == 'Structure':
                lines.append(f"{prefix} Structure: {value:.0f}")
                lines.append(f"    📗 HH+HL (Higher High/Low) = LONG")
                lines.append(f"    📕 LH+LL (Lower High/Low) = SHORT")
            elif name == 'SR_Level':
                signal, annotation = self._get_sr_annotation(value)
                lines.append(f"{prefix} S/R Level: {value:.0f}% {signal}")
                lines.append(f"    {annotation}")
            elif name == 'LS_Ratio':
                signal, annotation = self._get_ls_ratio_annotation(value)
                lines.append(f"{prefix} L/S Ratio: {value:.2f} {signal}")
                lines.append(f"    {annotation}")
            elif name == 'OI_Change':
                lines.append(f"{prefix} OI Change: {value:+.1f}%")
                lines.append(f"    📗 OI↑ + Price↑ = LONG tiếp tục")
                lines.append(f"    📕 OI↑ + Price↓ = SHORT tiếp tục")
            else:
                lines.append(f"{prefix} {name}: {value:.2f}")
        
        return "\n".join(lines)
    
    def _get_rsi_annotation(self, rsi: float) -> tuple:
        """Get RSI signal and annotation"""
        if rsi < 30:
            return "🟢 LONG", "📗 RSI < 30 = Oversold → LONG | 📕 RSI > 70 = Overbought → SHORT"
        elif rsi < 40:
            return "🟡 Gần LONG", "📗 RSI < 30 = Oversold → LONG | 📕 RSI > 70 = Overbought → SHORT"
        elif rsi > 70:
            return "🔴 SHORT", "📗 RSI < 30 = Oversold → LONG | 📕 RSI > 70 = Overbought → SHORT"
        elif rsi > 60:
            return "🟡 Gần SHORT", "📗 RSI < 30 = Oversold → LONG | 📕 RSI > 70 = Overbought → SHORT"
        else:
            return "⚪ Neutral", "📗 RSI < 30 = Oversold → LONG | 📕 RSI > 70 = Overbought → SHORT"
    
    def _get_macd_annotation(self, value: float) -> tuple:
        """Get MACD signal and annotation"""
        if value > 0:
            return "🟢 Bullish", "📗 MACD > Signal + Histogram↑ = LONG | 📕 MACD < Signal + Histogram↓ = SHORT"
        elif value < 0:
            return "🔴 Bearish", "📗 MACD > Signal + Histogram↑ = LONG | 📕 MACD < Signal + Histogram↓ = SHORT"
        else:
            return "⚪ Neutral", "📗 MACD > Signal + Histogram↑ = LONG | 📕 MACD < Signal + Histogram↓ = SHORT"
    
    def _get_bb_annotation(self, value: float) -> tuple:
        """Get Bollinger Bands signal and annotation"""
        if value < 20:
            return "🟢 LONG", "📗 BB < 20% (gần lower) = LONG | 📕 BB > 80% (gần upper) = SHORT"
        elif value < 30:
            return "🟡 Gần LONG", "📗 BB < 20% (gần lower) = LONG | 📕 BB > 80% (gần upper) = SHORT"
        elif value > 80:
            return "🔴 SHORT", "📗 BB < 20% (gần lower) = LONG | 📕 BB > 80% (gần upper) = SHORT"
        elif value > 70:
            return "🟡 Gần SHORT", "📗 BB < 20% (gần lower) = LONG | 📕 BB > 80% (gần upper) = SHORT"
        else:
            return "⚪ Middle", "📗 BB < 20% (gần lower) = LONG | 📕 BB > 80% (gần upper) = SHORT"
    
    def _get_adx_annotation(self, value: float) -> tuple:
        """Get ADX signal and annotation"""
        if value > 40:
            return "💪 Strong Trend", "📊 ADX > 25 = Có trend | ADX < 20 = Sideway | ADX > 40 = Trend mạnh"
        elif value > 25:
            return "📈 Trending", "📊 ADX > 25 = Có trend | ADX < 20 = Sideway | ADX > 40 = Trend mạnh"
        elif value > 15:
            return "〰️ Weak", "📊 ADX > 25 = Có trend | ADX < 20 = Sideway | ADX > 40 = Trend mạnh"
        else:
            return "➖ No Trend", "📊 ADX > 25 = Có trend | ADX < 20 = Sideway | ADX > 40 = Trend mạnh"
    
    def _get_funding_annotation(self, value: float) -> tuple:
        """Get Funding Rate signal and annotation (contrarian)"""
        if value > 0.05:
            return "🔴 SHORT", "📗 Funding < -0.05% = LONG (contrarian) | 📕 Funding > 0.05% = SHORT (contrarian)"
        elif value > 0.01:
            return "🟡 Gần SHORT", "📗 Funding < -0.05% = LONG (contrarian) | 📕 Funding > 0.05% = SHORT (contrarian)"
        elif value < -0.05:
            return "🟢 LONG", "📗 Funding < -0.05% = LONG (contrarian) | 📕 Funding > 0.05% = SHORT (contrarian)"
        elif value < -0.01:
            return "🟡 Gần LONG", "📗 Funding < -0.05% = LONG (contrarian) | 📕 Funding > 0.05% = SHORT (contrarian)"
        else:
            return "⚪ Neutral", "📗 Funding < -0.05% = LONG (contrarian) | 📕 Funding > 0.05% = SHORT (contrarian)"
    
    def _get_volume_annotation(self, value: float) -> tuple:
        """Get Volume signal and annotation"""
        if value > 1.5:
            return "📊 High", "📊 Vol > 1.5x = Xác nhận trend | Vol < 0.5x = Không đáng tin"
        elif value > 1.0:
            return "📊 Normal", "📊 Vol > 1.5x = Xác nhận trend | Vol < 0.5x = Không đáng tin"
        elif value > 0.5:
            return "📉 Low", "📊 Vol > 1.5x = Xác nhận trend | Vol < 0.5x = Không đáng tin"
        else:
            return "⚠️ Very Low", "📊 Vol > 1.5x = Xác nhận trend | Vol < 0.5x = Không đáng tin"
    
    def _get_sr_annotation(self, value: float) -> tuple:
        """Get Support/Resistance level annotation"""
        if value < 20:
            return "🟢 Gần Support", "📗 < 30% (gần support) = LONG | 📕 > 70% (gần resistance) = SHORT"
        elif value < 40:
            return "🟡 Lower Zone", "📗 < 30% (gần support) = LONG | 📕 > 70% (gần resistance) = SHORT"
        elif value > 80:
            return "🔴 Gần Resistance", "📗 < 30% (gần support) = LONG | 📕 > 70% (gần resistance) = SHORT"
        elif value > 60:
            return "🟡 Upper Zone", "📗 < 30% (gần support) = LONG | 📕 > 70% (gần resistance) = SHORT"
        else:
            return "⚪ Middle", "📗 < 30% (gần support) = LONG | 📕 > 70% (gần resistance) = SHORT"
    
    def _get_ls_ratio_annotation(self, value: float) -> tuple:
        """Get Long/Short Ratio annotation (contrarian)"""
        if value > 1.5:
            return "🔴 SHORT", "📗 L/S < 0.7 = LONG (contrarian) | 📕 L/S > 1.5 = SHORT (contrarian)"
        elif value > 1.2:
            return "🟡 Gần SHORT", "📗 L/S < 0.7 = LONG (contrarian) | 📕 L/S > 1.5 = SHORT (contrarian)"
        elif value < 0.67:
            return "🟢 LONG", "📗 L/S < 0.7 = LONG (contrarian) | 📕 L/S > 1.5 = SHORT (contrarian)"
        elif value < 0.8:
            return "🟡 Gần LONG", "📗 L/S < 0.7 = LONG (contrarian) | 📕 L/S > 1.5 = SHORT (contrarian)"
        else:
            return "⚪ Balanced", "📗 L/S < 0.7 = LONG (contrarian) | 📕 L/S > 1.5 = SHORT (contrarian)"
    
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

