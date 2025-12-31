"""
AI Model - Ensemble prediction for trade confirmation
XGBoost (40%) + LightGBM (40%) + Logistic Regression (20%)
"""
import os
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)

# Optional imports - these may not be installed
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    logger.warning("XGBoost not installed. Using mock predictions.")

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    logger.warning("LightGBM not installed. Using mock predictions.")

try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("Scikit-learn not installed. Using mock predictions.")


@dataclass
class AIResult:
    """AI prediction result"""
    confidence: float  # 0-1
    direction: str  # LONG, SHORT, NO_TRADE
    risk_factors: List[str]
    feature_importance: Dict[str, float]
    model_agreement: float  # % of models agreeing
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'confidence': self.confidence,
            'direction': self.direction,
            'risk_factors': self.risk_factors,
            'feature_importance': self.feature_importance,
            'model_agreement': self.model_agreement
        }


class AIModel:
    """
    Ensemble AI Model for trade prediction.
    
    Architecture:
    - XGBoost: 40% weight
    - LightGBM: 40% weight  
    - Logistic Regression: 20% weight
    
    Confidence threshold: 65%
    """
    
    def __init__(
        self,
        model_path: str = "models/",
        xgb_weight: float = 0.40,
        lgb_weight: float = 0.40,
        lr_weight: float = 0.20,
        confidence_threshold: float = 0.65
    ):
        self.model_path = model_path
        self.xgb_weight = xgb_weight
        self.lgb_weight = lgb_weight
        self.lr_weight = lr_weight
        self.confidence_threshold = confidence_threshold
        
        # Models
        self.xgb_model = None
        self.lgb_model = None
        self.lr_model = None
        self.scaler = None
        
        # Feature names (100 features)
        self.feature_names = self._get_feature_names()
        
        # Load or initialize models
        self._load_models()
    
    def _get_feature_names(self) -> List[str]:
        """Get list of feature names"""
        names = []
        
        # Technical (20)
        names.extend([
            'rsi_7', 'rsi_14', 'ema_9', 'ema_21', 'ema_50', 'ema_200',
            'macd_line', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_lower', 'bb_position',
            'atr_14', 'atr_percentile', 'adx', 'plus_di', 'minus_di',
            'stoch_k', 'stoch_d', 'vwap'
        ])
        
        # Price Action (15)
        names.extend([
            'body_percent', 'upper_wick_ratio', 'lower_wick_ratio',
            'range_expansion', 'breakout_strength',
            'swing_high_dist', 'swing_low_dist',
            'hh_count', 'll_count', 'hl_count', 'lh_count',
            'trend_structure', 'consolidation_bars', 'volatility_contraction',
            'key_level_distance'
        ])
        
        # MTF (15)
        names.extend([
            'tf_15m_trend', 'tf_15m_strength', 'tf_15m_rsi',
            'tf_5m_trend', 'tf_5m_strength', 'tf_5m_rsi',
            'tf_3m_momentum', 'tf_1m_momentum',
            'mtf_alignment', 'mtf_confluence_score',
            'htf_support_dist', 'htf_resistance_dist',
            'tf_divergence', 'momentum_acceleration', 'trend_age_bars'
        ])
        
        # On-chain (20)
        names.extend([
            'exchange_inflow', 'exchange_outflow', 'exchange_netflow',
            'flow_velocity', 'flow_percentile',
            'large_tx_count', 'whale_accumulation', 'whale_distribution',
            'smart_money_flow', 'whale_activity_score',
            'miner_reserve', 'miner_outflow', 'hash_rate_trend',
            'active_addresses', 'transaction_count',
            'nvt_ratio', 'sopr', 'puell_multiple',
            'supply_on_exchange', 'stablecoin_supply_ratio'
        ])
        
        # Liquidation (10)
        names.extend([
            'long_liq_density_1pct', 'long_liq_density_2pct',
            'short_liq_density_1pct', 'short_liq_density_2pct',
            'distance_to_long_liq', 'distance_to_short_liq',
            'liq_imbalance', 'recent_liq_volume_1h',
            'recent_liq_volume_24h', 'liq_cascade_risk'
        ])
        
        # Funding (8)
        names.extend([
            'funding_current', 'funding_predicted',
            'funding_trend_8h', 'funding_trend_24h',
            'funding_extreme', 'funding_vs_price_div',
            'time_to_funding', 'funding_percentile'
        ])
        
        # Microstructure (12)
        names.extend([
            'cvd', 'cvd_trend', 'orderbook_imbalance', 'orderbook_imbalance_10',
            'large_order_flow', 'tape_speed', 'aggressor_ratio',
            'spread_current', 'spread_percentile', 'depth_ratio',
            'vwap_distance', 'poc_distance'
        ])
        
        return names
    
    def _load_models(self):
        """Load saved models or initialize new ones"""
        os.makedirs(self.model_path, exist_ok=True)
        
        # Load XGBoost
        xgb_path = os.path.join(self.model_path, "xgb_model.pkl")
        if os.path.exists(xgb_path) and HAS_XGB:
            with open(xgb_path, "rb") as f:
                self.xgb_model = pickle.load(f)
            logger.info("Loaded XGBoost model")
        
        # Load LightGBM
        lgb_path = os.path.join(self.model_path, "lgb_model.pkl")
        if os.path.exists(lgb_path) and HAS_LGB:
            with open(lgb_path, "rb") as f:
                self.lgb_model = pickle.load(f)
            logger.info("Loaded LightGBM model")
        
        # Load Logistic Regression
        lr_path = os.path.join(self.model_path, "lr_model.pkl")
        if os.path.exists(lr_path) and HAS_SKLEARN:
            with open(lr_path, "rb") as f:
                self.lr_model = pickle.load(f)
            logger.info("Loaded Logistic Regression model")
        
        # Load scaler
        scaler_path = os.path.join(self.model_path, "scaler.pkl")
        if os.path.exists(scaler_path) and HAS_SKLEARN:
            with open(scaler_path, "rb") as f:
                self.scaler = pickle.load(f)
            logger.info("Loaded feature scaler")
    
    def save_models(self):
        """Save models to disk"""
        if self.xgb_model and HAS_XGB:
            with open(os.path.join(self.model_path, "xgb_model.pkl"), "wb") as f:
                pickle.dump(self.xgb_model, f)
        
        if self.lgb_model and HAS_LGB:
            with open(os.path.join(self.model_path, "lgb_model.pkl"), "wb") as f:
                pickle.dump(self.lgb_model, f)
        
        if self.lr_model and HAS_SKLEARN:
            with open(os.path.join(self.model_path, "lr_model.pkl"), "wb") as f:
                pickle.dump(self.lr_model, f)
        
        if self.scaler and HAS_SKLEARN:
            with open(os.path.join(self.model_path, "scaler.pkl"), "wb") as f:
                pickle.dump(self.scaler, f)
        
        logger.info("Models saved")
    
    def predict(self, features) -> AIResult:
        """
        Make ensemble prediction.
        
        Args:
            features: AllFeatures object or feature vector
        
        Returns:
            AIResult with prediction
        """
        # Convert to feature vector if needed
        if hasattr(features, 'to_feature_vector'):
            feature_vector = features.to_feature_vector()
        else:
            feature_vector = features
        
        # Ensure correct shape
        X = np.array(feature_vector).reshape(1, -1)
        
        # Get predictions from each model
        predictions = []
        probabilities = []
        
        # XGBoost prediction
        if self.xgb_model and HAS_XGB:
            try:
                xgb_proba = self.xgb_model.predict_proba(X)[0]
                predictions.append(('xgb', np.argmax(xgb_proba), max(xgb_proba)))
                probabilities.append(xgb_proba)
            except Exception as e:
                logger.error(f"XGBoost prediction failed: {e}")
        
        # LightGBM prediction
        if self.lgb_model and HAS_LGB:
            try:
                lgb_proba = self.lgb_model.predict_proba(X)[0]
                predictions.append(('lgb', np.argmax(lgb_proba), max(lgb_proba)))
                probabilities.append(lgb_proba)
            except Exception as e:
                logger.error(f"LightGBM prediction failed: {e}")
        
        # Logistic Regression prediction
        if self.lr_model and HAS_SKLEARN:
            try:
                # Scale features for LR
                if self.scaler:
                    X_scaled = self.scaler.transform(X)
                else:
                    X_scaled = X
                lr_proba = self.lr_model.predict_proba(X_scaled)[0]
                predictions.append(('lr', np.argmax(lr_proba), max(lr_proba)))
                probabilities.append(lr_proba)
            except Exception as e:
                logger.error(f"Logistic Regression prediction failed: {e}")
        
        # If no models available, return mock prediction
        if not predictions:
            return self._mock_prediction(feature_vector)
        
        # Calculate weighted ensemble
        weights = [self.xgb_weight, self.lgb_weight, self.lr_weight][:len(probabilities)]
        weights = np.array(weights) / sum(weights)  # Normalize
        
        ensemble_proba = np.zeros(probabilities[0].shape)
        for i, proba in enumerate(probabilities):
            ensemble_proba += weights[i] * proba
        
        # Get final prediction
        pred_class = np.argmax(ensemble_proba)
        confidence = max(ensemble_proba)
        
        # Map class to direction
        direction_map = {0: "NO_TRADE", 1: "LONG", 2: "SHORT"}
        direction = direction_map.get(pred_class, "NO_TRADE")
        
        # Calculate model agreement
        if len(predictions) > 1:
            pred_classes = [p[1] for p in predictions]
            agreement = pred_classes.count(pred_class) / len(predictions)
        else:
            agreement = 1.0
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(feature_vector, confidence)
        
        # Get feature importance
        importance = self._get_feature_importance()
        
        return AIResult(
            confidence=confidence,
            direction=direction,
            risk_factors=risk_factors,
            feature_importance=importance,
            model_agreement=agreement
        )
    
    def _mock_prediction(self, feature_vector: List[float]) -> AIResult:
        """Generate mock prediction when models aren't available"""
        # Simple heuristic based on key features
        rsi = feature_vector[1] if len(feature_vector) > 1 else 50  # rsi_14
        adx = feature_vector[14] if len(feature_vector) > 14 else 20  # adx
        
        # Determine direction based on RSI
        if rsi < 35:
            direction = "LONG"
            confidence = 0.6 + (35 - rsi) / 100
        elif rsi > 65:
            direction = "SHORT"
            confidence = 0.6 + (rsi - 65) / 100
        else:
            direction = "NO_TRADE"
            confidence = 0.5
        
        # Adjust for ADX
        if adx > 25:
            confidence += 0.1
        
        confidence = min(0.95, max(0.3, confidence))
        
        return AIResult(
            confidence=confidence,
            direction=direction,
            risk_factors=["Using mock prediction - no trained models"],
            feature_importance={},
            model_agreement=1.0
        )
    
    def _identify_risk_factors(self, features: List[float], confidence: float) -> List[str]:
        """Identify potential risk factors"""
        risks = []
        
        if len(features) < 20:
            return risks
        
        # RSI extreme
        rsi = features[1]  # rsi_14
        if rsi > 80:
            risks.append(f"RSI overbought ({rsi:.1f})")
        elif rsi < 20:
            risks.append(f"RSI oversold ({rsi:.1f})")
        
        # High volatility
        atr_percentile = features[13]  # atr_percentile
        if atr_percentile > 90:
            risks.append(f"Extreme volatility (ATR {atr_percentile:.0f}%)")
        
        # Weak trend
        adx = features[14]  # adx
        if adx < 20:
            risks.append(f"Weak trend (ADX {adx:.1f})")
        
        # Low confidence
        if confidence < 0.7:
            risks.append(f"Low confidence ({confidence:.0%})")
        
        return risks
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from models"""
        importance = {}
        
        if self.xgb_model and HAS_XGB:
            try:
                xgb_imp = self.xgb_model.feature_importances_
                for i, name in enumerate(self.feature_names[:len(xgb_imp)]):
                    importance[name] = float(xgb_imp[i])
            except:
                pass
        
        # Sort by importance
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return importance
    
    def train(
        self, 
        X: np.ndarray, 
        y: np.ndarray,
        validation_split: float = 0.2
    ):
        """
        Train all models on historical data.
        
        Args:
            X: Feature matrix (n_samples, 100)
            y: Labels (0=NO_TRADE, 1=LONG, 2=SHORT)
            validation_split: Fraction for validation
        """
        logger.info(f"Training models on {len(X)} samples...")
        
        # Split data
        n_val = int(len(X) * validation_split)
        X_train, X_val = X[:-n_val], X[-n_val:]
        y_train, y_val = y[:-n_val], y[-n_val:]
        
        # Train XGBoost
        if HAS_XGB:
            self.xgb_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective='multi:softprob',
                num_class=3,
                use_label_encoder=False,
                eval_metric='mlogloss'
            )
            self.xgb_model.fit(X_train, y_train)
            logger.info("XGBoost trained")
        
        # Train LightGBM
        if HAS_LGB:
            self.lgb_model = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective='multiclass',
                num_class=3,
                verbose=-1
            )
            self.lgb_model.fit(X_train, y_train)
            logger.info("LightGBM trained")
        
        # Train Logistic Regression
        if HAS_SKLEARN:
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            
            self.lr_model = LogisticRegression(
                max_iter=1000,
                multi_class='multinomial',
                solver='lbfgs'
            )
            self.lr_model.fit(X_train_scaled, y_train)
            logger.info("Logistic Regression trained")
        
        # Save models
        self.save_models()
        
        logger.info("All models trained and saved")

