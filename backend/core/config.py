from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

logger = logging.getLogger("ARCOS.Config")

_ENV_LOADED = False
_ENV_PATH: Path | None = None
_VALIDATION_CACHE: dict[str, Any] | None = None

_BOOLEAN_TRUE = {"1", "true", "yes", "on"}
_HEX_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_HEX_PRIVATE_KEY_RE = re.compile(r"^(0x)?[a-fA-F0-9]{64}$")
_SAFE_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_environment(env_path: str | None = None) -> bool:
    global _ENV_LOADED, _ENV_PATH, _VALIDATION_CACHE
    backend_root = Path(__file__).resolve().parents[1]
    resolved_path = Path(env_path) if env_path else backend_root / ".env"
    _ENV_PATH = resolved_path
    _VALIDATION_CACHE = None
    if resolved_path.exists():
        if load_dotenv is not None:
            load_dotenv(resolved_path, override=False)
        else:
            for line in resolved_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                os.environ.setdefault(key.strip(), _strip_env_value(value))
        _ENV_LOADED = True
    else:
        _ENV_LOADED = False
    return _ENV_LOADED


def _strip_env_value(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'"}:
        return cleaned[1:-1]
    return cleaned


def get_env(key: str, default: Any = None) -> Any:
    value = os.getenv(key)
    if value is None or value == "":
        return default
    return value


def get_bool(key: str, default: bool = False) -> bool:
    value = get_env(key, None)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in _BOOLEAN_TRUE


def get_int(key: str, default: int = 0) -> int:
    value = get_env(key, None)
    if value is None:
        return int(default)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return int(default)


def get_float(key: str, default: float = 0.0) -> float:
    value = get_env(key, None)
    if value is None:
        return float(default)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float(default)


def _warning(section: str, key: str, value: Any, message: str, severity: str = "warning") -> dict[str, Any]:
    payload = {
        "section": section,
        "key": key,
        "value": value,
        "message": message,
        "severity": severity,
    }
    log_method = logger.warning if severity == "warning" else logger.info
    log_method("config_validation %s", payload)
    return payload


def _coerce_str(key: str, default: str = "") -> str:
    return str(get_env(key, default) or default).strip()


def _coerce_int(
    key: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
    warnings: list[dict[str, Any]],
    section: str,
) -> int:
    raw = get_env(key, None)
    if raw is None:
        value = int(default)
    else:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError):
            warnings.append(_warning(section, key, raw, f"invalid integer; using default {default}"))
            value = int(default)
    if minimum is not None and value < minimum:
        warnings.append(_warning(section, key, value, f"value below minimum {minimum}; using {minimum}"))
        value = minimum
    if maximum is not None and value > maximum:
        warnings.append(_warning(section, key, value, f"value above maximum {maximum}; using {maximum}"))
        value = maximum
    return value


def _coerce_float(
    key: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    warnings: list[dict[str, Any]],
    section: str,
) -> float:
    raw = get_env(key, None)
    if raw is None:
        value = float(default)
    else:
        try:
            value = float(str(raw).strip())
        except (TypeError, ValueError):
            warnings.append(_warning(section, key, raw, f"invalid float; using default {default}"))
            value = float(default)
    if minimum is not None and value < minimum:
        warnings.append(_warning(section, key, value, f"value below minimum {minimum}; using {minimum}"))
        value = minimum
    if maximum is not None and value > maximum:
        warnings.append(_warning(section, key, value, f"value above maximum {maximum}; using {maximum}"))
        value = maximum
    return value


def _coerce_bool(key: str, default: bool) -> bool:
    return get_bool(key, default)


def _coerce_csv(key: str, default: str = "") -> list[str]:
    raw = _coerce_str(key, default)
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _validate_url(
    section: str,
    key: str,
    value: str,
    *,
    warnings: list[dict[str, Any]],
    required: bool = False,
    allowed_schemes: set[str] | None = None,
) -> str:
    value = value.strip()
    if not value:
        if required:
            warnings.append(_warning(section, key, value, "missing required URL value"))
        return value
    parsed = urlparse(value)
    schemes = allowed_schemes or {"http", "https"}
    if parsed.scheme not in schemes or not parsed.netloc:
        warnings.append(_warning(section, key, value, f"invalid URL; expected schemes {sorted(schemes)}"))
    return value


def _validate_choice(
    section: str,
    key: str,
    value: str,
    *,
    allowed: set[str],
    warnings: list[dict[str, Any]],
    fallback: str,
) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed:
        warnings.append(_warning(section, key, value, f"invalid option; using {fallback}"))
        return fallback
    return normalized


def _validate_address(section: str, key: str, value: str, warnings: list[dict[str, Any]]) -> str:
    if value and not _HEX_ADDRESS_RE.fullmatch(value):
        warnings.append(_warning(section, key, value, "invalid address format"))
    return value


def _validate_key(
    section: str,
    key: str,
    value: str,
    warnings: list[dict[str, Any]],
    *,
    allow_empty: bool = True,
) -> str:
    if not value:
        if not allow_empty:
            warnings.append(_warning(section, key, value, "missing required key"))
        return value
    if not _HEX_PRIVATE_KEY_RE.fullmatch(value):
        warnings.append(_warning(section, key, "***", "invalid private key format"))
    return value


def _validate_table_name(section: str, key: str, value: str, warnings: list[dict[str, Any]]) -> str:
    if value and not _SAFE_TABLE_RE.fullmatch(value):
        warnings.append(_warning(section, key, value, "invalid SQL identifier-like table name"))
    return value


def validate_config(force_refresh: bool = False) -> dict[str, Any]:
    global _VALIDATION_CACHE
    if _VALIDATION_CACHE is not None and not force_refresh:
        return _VALIDATION_CACHE

    warnings: list[dict[str, Any]] = []

    arc = {
        "rpc_url": _validate_url("ARC", "ARC_RPC_URL", _coerce_str("ARC_RPC_URL", "http://127.0.0.1:8545"), warnings=warnings),
        "chain_id": _coerce_int("ARC_CHAIN_ID", 31337, minimum=1, maximum=2**31 - 1, warnings=warnings, section="ARC"),
        "usdc_contract_address": _validate_address(
            "ARC",
            "ARC_USDC_CONTRACT_ADDRESS",
            _coerce_str("ARC_USDC_CONTRACT_ADDRESS", "0x3600000000000000000000000000000000000000"),
            warnings,
        ),
        "sender_private_key": _validate_key("ARC", "ARC_SENDER_PRIVATE_KEY", _coerce_str("ARC_SENDER_PRIVATE_KEY", ""), warnings),
    }

    circle = {
        "api_key": _coerce_str("CIRCLE_API_KEY", ""),
        "wallet_api_url": _validate_url(
            "CIRCLE",
            "CIRCLE_WALLET_API_URL",
            _coerce_str("CIRCLE_WALLET_API_URL", "https://api.circle.com/v1/w3s/developer/wallets"),
            warnings=warnings,
        ),
        "wallet_set_id": _coerce_str("CIRCLE_WALLET_SET_ID", ""),
        "entity_secret_ciphertext": _coerce_str("CIRCLE_ENTITY_SECRET_CIPHERTEXT", ""),
        "arc_blockchain": _coerce_str("CIRCLE_ARC_BLOCKCHAIN", "EVM-ARC"),
        "gateway_api_url": _validate_url("CIRCLE", "CIRCLE_GATEWAY_API_URL", _coerce_str("CIRCLE_GATEWAY_API_URL", ""), warnings=warnings),
        "gateway_api_key": _coerce_str("CIRCLE_GATEWAY_API_KEY", ""),
        "nanopayments_enabled": _coerce_bool("CIRCLE_NANOPAYMENTS_ENABLED", False),
    }

    payments = {
        "settlement_mode": _validate_choice(
            "PAYMENTS",
            "SETTLEMENT_MODE",
            _coerce_str("SETTLEMENT_MODE", "simulated"),
            allowed={"simulated", "arc", "hybrid"},
            warnings=warnings,
            fallback="simulated",
        ),
        "settlement_retries": _coerce_int("ARC_SETTLEMENT_RETRIES", 3, minimum=1, maximum=10, warnings=warnings, section="PAYMENTS"),
        "micropayment_cap": _coerce_int("ARC_MICROPAYMENT_CAP", 10_000, minimum=1, maximum=10_000_000, warnings=warnings, section="PAYMENTS"),
        "escrow_enabled": _coerce_bool("ARCOS_ESCROW_ENABLED", True),
        "streaming_payments_enabled": _coerce_bool("ARCOS_STREAMING_PAYMENTS_ENABLED", True),
        "seed_balance": _coerce_int("ARCOS_SEED_BALANCE", 250_000_000, minimum=0, maximum=10_000_000_000, warnings=warnings, section="PAYMENTS"),
    }

    intelligence = {
        "use_ml_model": _coerce_bool("USE_ML_MODEL", False),
        "scout_mode": _validate_choice(
            "INTELLIGENCE",
            "SCOUT_MODE",
            _coerce_str("SCOUT_MODE", "lightweight"),
            allowed={"lightweight", "standard", "deep"},
            warnings=warnings,
            fallback="lightweight",
        ),
    }

    economy = {
        "min_price_micro_usdc": _coerce_int("ARCOS_MIN_PRICE_MICRO_USDC", 500, minimum=1, maximum=10_000_000, warnings=warnings, section="ECONOMY"),
        "max_price_micro_usdc": _coerce_int("ARCOS_MAX_PRICE_MICRO_USDC", 10_000, minimum=100, maximum=10_000_000, warnings=warnings, section="ECONOMY"),
        "max_transactions": _coerce_int("ARCOS_MAX_TRANSACTIONS", 10_000, minimum=100, maximum=1_000_000, warnings=warnings, section="ECONOMY"),
        "max_events": _coerce_int("ARCOS_MAX_EVENTS", 5_000, minimum=100, maximum=1_000_000, warnings=warnings, section="ECONOMY"),
        "event_subscriber_queue_size": _coerce_int("ARCOS_EVENT_SUBSCRIBER_QUEUE_SIZE", 200, minimum=10, maximum=100_000, warnings=warnings, section="ECONOMY"),
        "demand_threshold": _coerce_float("ARCOS_DEMAND_THRESHOLD", 1.1, minimum=0.1, maximum=100.0, warnings=warnings, section="ECONOMY"),
        "max_compute_agents": _coerce_int("ARCOS_MAX_COMPUTE_AGENTS", 10, minimum=1, maximum=1_000, warnings=warnings, section="ECONOMY"),
        "max_tx_per_second": _coerce_int("ARCOS_MAX_TX_PER_SECOND", 100, minimum=1, maximum=100_000, warnings=warnings, section="ECONOMY"),
        "compute_agent_keys": _coerce_csv("ARCOS_COMPUTE_AGENT_KEYS"),
    }
    if economy["min_price_micro_usdc"] > economy["max_price_micro_usdc"]:
        warnings.append(
            _warning(
                "ECONOMY",
                "ARCOS_MIN_PRICE_MICRO_USDC",
                economy["min_price_micro_usdc"],
                "minimum price exceeded maximum; clamping to maximum",
            )
        )
        economy["min_price_micro_usdc"] = economy["max_price_micro_usdc"]

    database = {
        "db_mode": _validate_choice(
            "DATABASE",
            "DB_MODE",
            _coerce_str("DB_MODE", "memory"),
            allowed={"memory", "sqlite", "supabase", "hybrid"},
            warnings=warnings,
            fallback="memory",
        ),
        "sqlite_path": _coerce_str("ARCOS_SQLITE_PATH", ""),
        "use_supabase": _coerce_bool("USE_SUPABASE", False),
        "supabase_url": _validate_url("DATABASE", "SUPABASE_URL", _coerce_str("SUPABASE_URL", ""), warnings=warnings),
        "supabase_anon_key": _coerce_str("SUPABASE_ANON_KEY", ""),
        "supabase_service_key": _coerce_str("SUPABASE_SERVICE_KEY", ""),
        "supabase_table_transactions": _validate_table_name(
            "DATABASE",
            "SUPABASE_TABLE_TRANSACTIONS",
            _coerce_str("SUPABASE_TABLE_TRANSACTIONS", "transactions"),
            warnings,
        ),
        "persistence_queue_size": _coerce_int(
            "ARCOS_PERSISTENCE_QUEUE_SIZE",
            2_000,
            minimum=100,
            maximum=100_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_batch_size": _coerce_int(
            "SUPABASE_BATCH_SIZE",
            50,
            minimum=1,
            maximum=1_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_flush_interval_ms": _coerce_int(
            "SUPABASE_FLUSH_INTERVAL_MS",
            500,
            minimum=50,
            maximum=30_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_max_queue_size": _coerce_int(
            "SUPABASE_MAX_QUEUE_SIZE",
            5_000,
            minimum=100,
            maximum=200_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_max_retries": _coerce_int(
            "SUPABASE_MAX_RETRIES",
            4,
            minimum=1,
            maximum=10,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_retry_base_ms": _coerce_int(
            "SUPABASE_RETRY_BASE_MS",
            100,
            minimum=10,
            maximum=10_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_request_timeout_sec": _coerce_float(
            "SUPABASE_REQUEST_TIMEOUT_SEC",
            5.0,
            minimum=0.5,
            maximum=60.0,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_write_enabled": _coerce_bool("SUPABASE_WRITE_ENABLED", False),
        "supabase_compact_mode": _coerce_bool("SUPABASE_COMPACT_MODE", True),
        "supabase_drop_explanation": _coerce_bool("SUPABASE_DROP_EXPLANATION", True),
        "supabase_write_sampling_rate": _coerce_float(
            "SUPABASE_WRITE_SAMPLING_RATE",
            1.0,
            minimum=0.0,
            maximum=1.0,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_max_writes_per_sec": _coerce_int(
            "SUPABASE_MAX_WRITES_PER_SEC",
            20,
            minimum=1,
            maximum=10_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_max_row_size_bytes": _coerce_int(
            "SUPABASE_MAX_ROW_SIZE_BYTES",
            2_000,
            minimum=128,
            maximum=1_000_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "supabase_max_batch_bytes": _coerce_int(
            "SUPABASE_MAX_BATCH_BYTES",
            64_000,
            minimum=512,
            maximum=10_000_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "max_persistence_backlog": _coerce_int(
            "ARCOS_MAX_PERSISTENCE_BACKLOG",
            3_000,
            minimum=100,
            maximum=200_000,
            warnings=warnings,
            section="DATABASE",
        ),
        "enable_backpressure": _coerce_bool("ARCOS_ENABLE_BACKPRESSURE", True),
    }
    if database["use_supabase"] or database["supabase_write_enabled"]:
        if not database["supabase_url"]:
            warnings.append(_warning("DATABASE", "SUPABASE_URL", "", "Supabase writes enabled without SUPABASE_URL"))
        if not database["supabase_service_key"]:
            warnings.append(_warning("DATABASE", "SUPABASE_SERVICE_KEY", "", "Supabase writes enabled without SUPABASE_SERVICE_KEY"))

    demo = {
        "environment": _coerce_str("ENV", "development"),
        "debug": _coerce_bool("DEBUG", True),
        "port": _coerce_int("PORT", 8000, minimum=1, maximum=65535, warnings=warnings, section="DEMO"),
        "demo_mode": _coerce_bool("DEMO_MODE", True),
        "frontend_origin": _validate_url(
            "DEMO",
            "FRONTEND_ORIGIN",
            _coerce_str("FRONTEND_ORIGIN", "http://localhost:3000"),
            warnings=warnings,
        ),
    }
    logging_config = {
        "level": _validate_choice(
            "LOGGING",
            "LOG_LEVEL",
            _coerce_str("LOG_LEVEL", "INFO"),
            allowed={"debug", "info", "warning", "error", "critical"},
            warnings=warnings,
            fallback="info",
        ),
        "enable_detailed_logs": _coerce_bool("ENABLE_DETAILED_LOGS", False),
    }

    config = {
        "ARC": arc,
        "CIRCLE": circle,
        "PAYMENTS": payments,
        "INTELLIGENCE": intelligence,
        "ECONOMY": economy,
        "DATABASE": database,
        "DEMO": demo,
        "LOGGING": logging_config,
    }
    result = {
        "valid": not warnings,
        "warning_count": len(warnings),
        "warnings": warnings,
        "config": config,
    }
    _VALIDATION_CACHE = result
    return result


def env_status() -> dict[str, Any]:
    validation = validate_config()
    return {
        "loaded": _ENV_LOADED,
        "env_path": str(_ENV_PATH) if _ENV_PATH else None,
        "demo_mode": validation["config"]["DEMO"]["demo_mode"],
        "environment": validation["config"]["DEMO"]["environment"],
        "debug": validation["config"]["DEMO"]["debug"],
        "valid": validation["valid"],
        "warning_count": validation["warning_count"],
        "warnings": validation["warnings"],
        "groups": validation["config"],
    }


load_environment()
