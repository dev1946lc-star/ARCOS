"""
Example: Using Trained ML Models with ARCOS Agents

This example shows how to leverage the three trained models in your agents:
1. ResearchAgent - use price predictor for intelligent pricing
2. ComputeAgent - use success predictor for risk assessment
3. Job evaluation - use acceptance classifier for decision-making
"""

import numpy as np
from intelligence.model_manager import get_model_manager
from intelligence.feature_engineering import FeatureEngineering


def example_research_agent_pricing():
    """
    Example: Use price predictor in ResearchAgent to set optimal prices.
    """
    print("\n" + "="*60)
    print("Example 1: Intelligent Job Pricing (ResearchAgent)")
    print("="*60)
    
    # Get model manager and feature engineering
    model_mgr = get_model_manager()
    feature_eng = FeatureEngineering()
    
    if not model_mgr.is_ready():
        print("Models not loaded. Make sure you've run: python train_models.py")
        return
    
    # Simulate a job offer
    job_params = {
        "required_compute": 50.0,
        "price_offer": 45.0,  # Initial offer
        "queue_depth": 8,
        "completed_jobs": 120,
        "active_compute_agents": 5,
        "recent_offers": [44.0, 46.0, 43.5],
        "recent_workloads": [48.0, 52.0, 49.5],
        "success_rate": 0.85,
    }
    
    # Generate features
    feature_vector = feature_eng.generate(**job_params)
    
    # Prepare features for model (in correct order)
    feature_order = model_mgr.get_feature_order("price")
    features_array = np.array([
        feature_vector.values.get(feat, 0.0) for feat in feature_order
    ])
    
    # Predict optimal price
    result = model_mgr.predict_price(features_array)
    
    print(f"\nJob Parameters:")
    print(f"  Required Compute: {job_params['required_compute']}")
    print(f"  Initial Price Offer: ${job_params['price_offer']:.2f}")
    print(f"  Queue Depth: {job_params['queue_depth']}")
    print(f"  Active Agents: {job_params['active_compute_agents']}")
    
    print(f"\nPrice Prediction:")
    print(f"  Recommended Tier: {result.get('price_tier')} ({result.get('tier_labels', [])[result.get('price_tier', 0)]})")
    print(f"  Tier Probabilities: {[f'{p:.3f}' for p in result.get('probabilities', [])]}")


def example_compute_agent_risk():
    """
    Example: Use success predictor in ComputeAgent for risk assessment.
    """
    print("\n" + "="*60)
    print("Example 2: Job Success Risk Assessment (ComputeAgent)")
    print("="*60)
    
    model_mgr = get_model_manager()
    feature_eng = FeatureEngineering()
    
    if not model_mgr.is_ready():
        print("Models not loaded. Make sure you've run: python train_models.py")
        return
    
    # Simulate job conditions
    job_params = {
        "required_compute": 120.0,  # Large job
        "price_offer": 85.0,
        "queue_depth": 15,  # High queue pressure
        "completed_jobs": 200,
        "active_compute_agents": 3,
        "recent_offers": [84.0, 86.0, 85.5],
        "recent_workloads": [118.0, 122.0, 119.5],
        "success_rate": 0.75,  # Lower success rate
    }
    
    feature_vector = feature_eng.generate(**job_params)
    
    # Prepare features for model
    feature_order = model_mgr.get_feature_order("success")
    features_array = np.array([
        feature_vector.values.get(feat, 0.0) for feat in feature_order
    ])
    
    # Predict success probability
    result = model_mgr.predict_success(features_array)
    
    success_prob = result.get('success_probability', 0.0)
    risk_level = "HIGH" if success_prob < 0.5 else "MEDIUM" if success_prob < 0.75 else "LOW"
    
    print(f"\nJob Parameters:")
    print(f"  Required Compute: {job_params['required_compute']}")
    print(f"  Price: ${job_params['price_offer']:.2f}")
    print(f"  Queue Depth: {job_params['queue_depth']}")
    print(f"  Base Success Rate: {job_params['success_rate']:.2%}")
    
    print(f"\nSuccess Prediction:")
    print(f"  Predicted Success Probability: {success_prob:.2%}")
    print(f"  Predicted Failure Probability: {result.get('fail_probability', 0.0):.2%}")
    print(f"  Risk Level: {risk_level}")
    
    if success_prob < 0.6:
        print(f"  ⚠️  Recommendation: Consider negotiating better terms or declining")
    elif success_prob > 0.8:
        print(f"  ✓ Recommendation: Good candidate for acceptance")


def example_acceptance_classification():
    """
    Example: Use acceptance classifier for job acceptance decisions.
    """
    print("\n" + "="*60)
    print("Example 3: Job Acceptance Classification")
    print("="*60)
    
    model_mgr = get_model_manager()
    feature_eng = FeatureEngineering()
    
    if not model_mgr.is_ready():
        print("Models not loaded. Make sure you've run: python train_models.py")
        return
    
    # Test three different job scenarios
    scenarios = [
        {
            "name": "High-Value Job",
            "params": {
                "required_compute": 30.0,
                "price_offer": 60.0,  # High price relative to compute
                "queue_depth": 2,
                "completed_jobs": 50,
                "active_compute_agents": 8,
                "recent_offers": [58.0, 61.0],
                "recent_workloads": [28.0, 31.0],
                "success_rate": 0.9,
            }
        },
        {
            "name": "Medium Job",
            "params": {
                "required_compute": 100.0,
                "price_offer": 70.0,
                "queue_depth": 8,
                "completed_jobs": 120,
                "active_compute_agents": 5,
                "recent_offers": [68.0, 72.0],
                "recent_workloads": [98.0, 102.0],
                "success_rate": 0.75,
            }
        },
        {
            "name": "Low-Margin Job",
            "params": {
                "required_compute": 200.0,
                "price_offer": 50.0,  # Low price relative to compute
                "queue_depth": 20,
                "completed_jobs": 300,
                "active_compute_agents": 2,
                "recent_offers": [48.0, 52.0],
                "recent_workloads": [198.0, 202.0],
                "success_rate": 0.6,
            }
        },
    ]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}:")
        print(f"  Compute: {scenario['params']['required_compute']}, Price: ${scenario['params']['price_offer']}")
        
        feature_vector = feature_eng.generate(**scenario['params'])
        
        feature_order = model_mgr.get_feature_order("acceptance")
        features_array = np.array([
            feature_vector.values.get(feat, 0.0) for feat in feature_order
        ])
        
        result = model_mgr.predict_acceptance(features_array)
        
        prediction = result.get('prediction', -1)
        confidence = result.get('confidence', 0.0)
        labels = result.get('labels', {})
        
        decision = labels.get(prediction, "unknown")
        
        print(f"  Decision: {decision.upper()} (confidence: {confidence:.2%})")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("TRAINED ML MODELS - USAGE EXAMPLES")
    print("="*70)
    
    print("\nNote: These examples assume the models have been trained.")
    print("If models are not loaded, run: python train_models.py")
    
    try:
        example_research_agent_pricing()
        example_compute_agent_risk()
        example_acceptance_classification()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("INTEGRATION NOTES:")
    print("="*70)
    print("""
1. ResearchAgent should use price predictor when setting offers:
   result = model_mgr.predict_price(features_array)
   
2. ComputeAgent should use success predictor for risk assessment:
   result = model_mgr.predict_success(features_array)
   
3. Both agents can use the acceptance classifier as a secondary signal:
   result = model_mgr.predict_acceptance(features_array)

4. Always prepare features using FeatureEngineering in correct order
5. Handle model loading failures gracefully (models can be None)
6. Consider weighting ML predictions with heuristics (60/40 split)
""")


if __name__ == "__main__":
    main()
