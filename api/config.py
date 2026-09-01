"""Configuration loader with priority: toml > env vars > defaults."""

import os
from dataclasses import dataclass
from pathlib import Path

import tomllib

_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.toml"


def _get_env(key: str, default: str | None = None) -> str | None:
    """Get value from environment variable with MINESTATUS_ prefix."""
    return os.environ.get(f"MINESTATUS_{key}", default)


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 3000


@dataclass(frozen=True)
class CacheConfig:
    ttl: int = 600
    max_size: int = 100


@dataclass(frozen=True)
class QueryConfig:
    timeout: int = 8


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    cache: CacheConfig
    query: QueryConfig


def _load_toml() -> dict:
    """Load config.toml if it exists, return empty dict otherwise."""
    if _CONFIG_FILE.is_file():
        with open(_CONFIG_FILE, "rb") as f:
            return tomllib.load(f)
    return {}


def load_config() -> AppConfig:
    """Load configuration with priority: toml > env vars > defaults."""
    raw = _load_toml()

    # Server config
    server_section = raw.get("server", {})
    host = server_section.get("host") or _get_env("HOST") or "0.0.0.0"
    port_str = server_section.get("port") or _get_env("PORT")
    port = int(port_str) if port_str else 3000

    # Cache config
    cache_section = raw.get("cache", {})
    ttl_str = cache_section.get("ttl") or _get_env("CACHE_TTL")
    ttl = int(ttl_str) if ttl_str else 600
    max_size_str = cache_section.get("max_size") or _get_env("CACHE_MAX_SIZE")
    max_size = int(max_size_str) if max_size_str else 100

    # Query config
    query_section = raw.get("query", {})
    timeout_str = query_section.get("timeout") or _get_env("TIMEOUT")
    timeout = int(timeout_str) if timeout_str else 8

    return AppConfig(
        server=ServerConfig(host=host, port=port),
        cache=CacheConfig(ttl=ttl, max_size=max_size),
        query=QueryConfig(timeout=timeout),
    )


# Singleton
config = load_config()
