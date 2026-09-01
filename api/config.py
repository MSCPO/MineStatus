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
    host = server_section.get("host")
    if host is None:
        host = _get_env("HOST")
    if host is None:
        host = "0.0.0.0"

    port_raw = server_section.get("port")
    if port_raw is None:
        port_raw = _get_env("PORT")
    port = int(port_raw) if port_raw is not None else 3000

    # Cache config
    cache_section = raw.get("cache", {})
    ttl_raw = cache_section.get("ttl")
    if ttl_raw is None:
        ttl_raw = _get_env("CACHE_TTL")
    ttl = int(ttl_raw) if ttl_raw is not None else 600

    max_size_raw = cache_section.get("max_size")
    if max_size_raw is None:
        max_size_raw = _get_env("CACHE_MAX_SIZE")
    max_size = int(max_size_raw) if max_size_raw is not None else 100

    # Query config
    query_section = raw.get("query", {})
    timeout_raw = query_section.get("timeout")
    if timeout_raw is None:
        timeout_raw = _get_env("TIMEOUT")
    timeout = int(timeout_raw) if timeout_raw is not None else 8

    return AppConfig(
        server=ServerConfig(host=host, port=port),
        cache=CacheConfig(ttl=ttl, max_size=max_size),
        query=QueryConfig(timeout=timeout),
    )


# Singleton
config = load_config()
