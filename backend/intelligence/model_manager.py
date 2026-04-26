"""
Trained Models Manager for ARCOS

Provides easy access to all three trained ML models:
- Acceptance Classifier
- Price Predictor  
- Success Probability Predictor
"""

import json
from pathlib import Path
from typing import Any

# Heavy ML imports moved inside methods to speed up startup
JOBLIB_AVAILABLE = True # Assume available if in requirements
XGBOOST_AVAILABLE = True


class ModelManager:
    """Manages loading and access to all trained models."""
    
    def __init__(self, models_dir: Path | None = None):
        if models_dir is None:
            models_dir = Path(__file__).parent.parent / "models"
        
        self.models_dir = Path(models_dir)
        self.acceptance_model = None
        self.price_model = None
        self.price_scaler = None
        self.success_model = None
        self.feature_schemas = {}
        
        self._load_all_models()
    
    def _load_all_models(self) -> None:
        """Load all available trained models."""
        if not self.models_dir.exists():
            return
        
        # Local imports for performance
        try:
            import xgboost as xgb
        except ImportError:
            xgb = None
            
        try:
            import joblib
        except ImportError:
            joblib = None
        
        # Load acceptance model
        acceptance_path = self.models_dir / "acceptance_xgboost.json"
        if acceptance_path.exists() and xgb:
            try:
                self.acceptance_model = xgb.Booster()
                self.acceptance_model.load_model(str(acceptance_path))
                print("✓ Loaded acceptance classifier")
            except Exception as e:
                print(f"⚠️  Failed to load acceptance model: {e}")
        
        # Load price model
        price_path = self.models_dir / "price_logistic_regression.pkl"
        if price_path.exists() and joblib:
            try:
                self.price_model = joblib.load(price_path)
                print("✓ Loaded price predictor")
            except Exception as e:
                print(f"⚠️  Failed to load price model: {e}")
        
        # Load price scaler
        scaler_path = self.models_dir / "price_scaler.pkl"
        if scaler_path.exists() and joblib:
            try:
                self.price_scaler = joblib.load(scaler_path)
            except Exception as e:
                print(f"⚠️  Failed to load price scaler: {e}")
        
        # Load success model
        success_path = self.models_dir / "success_xgboost.json"
        if success_path.exists() and xgb:
            try:
                self.success_model = xgb.Booster()
                self.success_model.load_model(str(success_path))
                print("✓ Loaded success predictor")
            except Exception as e:
                print(f"⚠️  Failed to load success model: {e}")
        
        # Load feature schemas
        for schema_file in self.models_dir.glob("*_schema.json"):
            model_name = schema_file.stem.replace("_schema", "")
            try:
                schema = json.loads(schema_file.read_text())
                self.feature_schemas[model_name] = schema
            except Exception as e:
                print(f"⚠️  Failed to load {model_name} schema: {e}")
    
    def predict_acceptance(self, features_array) -> dict[str, Any]:
        """
        Predict job acceptance decision using trained classifier.
        
        Args:
            features_array: numpy array of features in correct order
        
        Returns:
            dict with prediction and probability
        """
        if self.acceptance_model is None:
            return {"error": "Acceptance model not loaded"}
        
        try:
            import xgboost as xgb
            dmatrix = xgb.DMatrix(features_array.reshape(1, -1))
            prediction = self.acceptance_model.predict(dmatrix)
            
            class_idx = int(prediction[0].argmax())
            confidence = float(prediction[0].max())
            
            return {
                "prediction": class_idx,  # 0=reject, 1=accept, 2=prioritize
                "confidence": confidence,
                "labels": {0: "reject", 1: "accept", 2: "prioritize"}
            }
        except Exception as e:
            return {"error": str(e)}
    
    def predict_price(self, features_array) -> dict[str, Any]:
        """
        Predict optimal price using trained regressor.
        
        Args:
            features_array: numpy array of features (will be scaled)
        
        Returns:
            dict with predicted price tier
        """
        if self.price_model is None or self.price_scaler is None:
            return {"error": "Price model not loaded"}
        
        try:
            import numpy as np
            features_scaled = self.price_scaler.transform(features_array.reshape(1, -1))
            prediction = self.price_model.predict(features_scaled)
            
            price_tier = int(prediction[0])
            probabilities = self.price_model.predict_proba(features_scaled)[0]
            
            return {
                "price_tier": price_tier,  # 0-4 representing price ranges
                "probabilities": probabilities.tolist(),
                "tier_labels": ["very_low", "low", "medium", "high", "very_high"]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def predict_success(self, features_array) -> dict[str, Any]:
        """
        Predict success probability using trained classifier.
        
        Args:
            features_array: numpy array of features in correct order
        
        Returns:
            dict with success probability and confidence
        """
        if self.success_model is None:
            return {"error": "Success model not loaded"}
        
        try:
            import xgboost as xgb
            dmatrix = xgb.DMatrix(features_array.reshape(1, -1))
            prediction = self.success_model.predict(dmatrix)
            
            success_probability = float(prediction[0][1])  # Probability of success (class 1)
            
            return {
                "success_probability": success_probability,
                "fail_probability": 1.0 - success_probability
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_feature_order(self, model_name: str) -> list[str]:
        """Get the feature order for a specific model."""
        schema = self.feature_schemas.get(model_name, {})
        return schema.get("feature_columns", [])
    
    def is_ready(self) -> bool:
        """Check if all models are loaded and ready."""
        return (
            self.acceptance_model is not None and
            self.price_model is not None and
            self.success_model is not None
        )


# Global instance
_model_manager = None

def get_model_manager() -> ModelManager:
    """Get or create the global model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
