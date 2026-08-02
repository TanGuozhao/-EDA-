from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from redis import Redis


load_dotenv()


@dataclass(frozen=True)
class TimingRedisKeys:
    """Versioned Redis key names for the timing-analysis challenge service."""

    namespace: str = "timing:v1"

    def challenge(self, challenge_id: str) -> str:
        return f"{self.namespace}:challenge:{challenge_id}"

    def current(self, chapter_key: str) -> str:
        return f"{self.namespace}:current:{chapter_key}"

    def ready_pool(self, chapter_key: str) -> str:
        return f"{self.namespace}:pool:ready:{chapter_key}"

    def generation_lock(self, chapter_key: str) -> str:
        return f"{self.namespace}:lock:generate:{chapter_key}"

    def assignment(self, session_id: str, chapter_key: str) -> str:
        return f"{self.namespace}:assignment:{session_id}:{chapter_key}"


def get_redis_client() -> Redis:
    """Create the synchronous client used by repository and background-job code."""

    return Redis.from_url(
        os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


class TimingChallengeCache:
    """Redis operations for immutable challenge payloads and generation coordination."""

    CHALLENGE_TTL_SECONDS = 7 * 24 * 60 * 60
    ASSIGNMENT_TTL_SECONDS = 15 * 60
    GENERATION_LOCK_TTL_SECONDS = 5 * 60

    def __init__(self, client: Redis, keys: TimingRedisKeys | None = None):
        self.client = client
        self.keys = keys or TimingRedisKeys()

    def get_challenge(self, challenge_id: str) -> dict[str, Any] | None:
        payload = self.client.get(self.keys.challenge(challenge_id))
        return json.loads(payload) if payload is not None else None

    def set_challenge(self, challenge_id: str, payload: dict[str, Any]) -> None:
        self.client.set(
            self.keys.challenge(challenge_id),
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            ex=self.CHALLENGE_TTL_SECONDS,
        )

    def invalidate_challenges(self, challenge_ids: list[str]) -> None:
        if not challenge_ids:
            return
        self.client.delete(*(self.keys.challenge(challenge_id) for challenge_id in challenge_ids))

    def clear_assignments_for_challenges(self, chapter_key: str, challenge_ids: list[str]) -> None:
        """Remove sticky sessions only for forcibly retired legacy challenges."""

        retired_ids = set(challenge_ids)
        if not retired_ids:
            return
        assignment_pattern = f"{self.keys.namespace}:assignment:*:{chapter_key}"
        for key in self.client.scan_iter(match=assignment_pattern, count=100):
            if self.client.get(key) in retired_ids:
                self.client.delete(key)

    def get_current_challenge_id(self, chapter_key: str) -> str | None:
        return self.client.get(self.keys.current(chapter_key))

    def set_current_challenge_id(self, chapter_key: str, challenge_id: str) -> None:
        self.client.set(self.keys.current(chapter_key), challenge_id)

    def get_assignment(self, session_id: str, chapter_key: str) -> str | None:
        return self.client.get(self.keys.assignment(session_id, chapter_key))

    def set_assignment(self, session_id: str, chapter_key: str, challenge_id: str) -> None:
        self.client.set(
            self.keys.assignment(session_id, chapter_key),
            challenge_id,
            ex=self.ASSIGNMENT_TTL_SECONDS,
        )

    def enqueue_ready_challenge(self, chapter_key: str, challenge_id: str) -> None:
        key = self.keys.ready_pool(chapter_key)
        self.client.lrem(key, 0, challenge_id)
        self.client.rpush(key, challenge_id)

    def dequeue_ready_challenge(self, chapter_key: str) -> str | None:
        return self.client.lpop(self.keys.ready_pool(chapter_key))

    def replace_chapter_state(
        self,
        chapter_key: str,
        current_challenge_id: str,
        ready_challenge_ids: list[str],
    ) -> None:
        """Rebuild the Redis pointer and future-question queue from durable storage."""

        pool_key = self.keys.ready_pool(chapter_key)
        with self.client.pipeline(transaction=True) as pipeline:
            pipeline.delete(pool_key)
            if ready_challenge_ids:
                pipeline.rpush(pool_key, *ready_challenge_ids)
            pipeline.set(self.keys.current(chapter_key), current_challenge_id)
            pipeline.execute()

    def enqueue_and_advance_current(self, chapter_key: str, challenge_id: str) -> tuple[str | None, str]:
        """Append one generated challenge and atomically publish the next queued challenge."""

        script = """
        local previous = redis.call('get', KEYS[1])
        redis.call('lrem', KEYS[2], 0, ARGV[1])
        redis.call('rpush', KEYS[2], ARGV[1])
        local next_id = redis.call('lpop', KEYS[2])
        redis.call('set', KEYS[1], next_id)
        return {previous or '', next_id}
        """
        previous, current = self.client.eval(
            script,
            2,
            self.keys.current(chapter_key),
            self.keys.ready_pool(chapter_key),
            challenge_id,
        )
        return (previous or None, current)

    def try_acquire_generation_lock(self, chapter_key: str, owner_token: str) -> bool:
        return bool(
            self.client.set(
                self.keys.generation_lock(chapter_key),
                owner_token,
                nx=True,
                ex=self.GENERATION_LOCK_TTL_SECONDS,
            )
        )

    def release_generation_lock(self, chapter_key: str, owner_token: str) -> bool:
        """Release only the lock owned by this job, never a later job's lock."""

        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        end
        return 0
        """
        return bool(self.client.eval(script, 1, self.keys.generation_lock(chapter_key), owner_token))
