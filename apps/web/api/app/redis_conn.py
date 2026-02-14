from __future__ import annotations

import os

import redis


def get_redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def get_redis_connection() -> redis.Redis:
    return redis.from_url(get_redis_url())

