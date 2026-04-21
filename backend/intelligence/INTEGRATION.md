# ARCOS Intelligence Integration

## What was copied

ARCOS now includes lightweight adaptations of these AURORA concepts:

- `Predictor` from `backend/ml/predictor.py`
- `FeatureEngineering` from `backend/data/feature_engineering.py`
- `DecisionEngine` from `backend/engine/decision_engine.py`
- `RiskAgent` from `backend/agents/risk_agent.py`
- `AnalystAgent` + `StrategyAnalyzer` logic merged into `backend/intelligence/strategy_analyzer.py`

## What was modified

- Removed trading actions, exchange dependencies, blockchain hooks, and database coupling.
- Replaced buy/sell outputs with ARCOS-friendly decisions:
  - `prioritize`
  - `accept`
  - `reject`
- Made ML model loading optional. If no model artifacts or optional libraries exist, ARCOS uses heuristic scoring instead of failing.
- Reframed features around job economics, queue pressure, workload, offer momentum, and profitability rather than candles/orders.

## How ARCOS uses it

- `ResearchAgent` builds feature vectors for each new job and uses the predictor to set a more intelligent `price_offer`.
- `ComputeAgent` evaluates jobs with `RiskAgent` and `DecisionEngine` before accepting them.
- Every integration is wrapped so failures fall back to ARCOS's original behavior.

## How to extend further

- Add model artifacts and a feature schema if you want `Predictor` to use a trained classifier.
- Feed real historical execution outcomes into `RiskAgent.circuit_breaker.record_outcome(...)`.
- Add a dedicated `StrategyAgent` if you want centralized job ranking across multiple compute agents.
- Adapt `ReputationTracker` later using ARCOS completion metrics only, without bringing over AURORA's database or blockchain workflow.
