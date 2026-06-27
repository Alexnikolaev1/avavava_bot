from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PendingJob:
    user_id: int
    action: str
    payload: dict[str, Any]
    cost_text: str


class PendingStore:
    """In-memory хранилище задач, ожидающих подтверждения стоимости."""

    def __init__(self) -> None:
        self._jobs: dict[str, PendingJob] = {}

    def put(self, job: PendingJob) -> str:
        token = uuid.uuid4().hex[:12]
        self._jobs[token] = job
        return token

    def pop(self, token: str, user_id: int) -> PendingJob | None:
        job = self._jobs.pop(token, None)
        if job is None or job.user_id != user_id:
            return None
        return job

    def get(self, token: str, user_id: int) -> PendingJob | None:
        job = self._jobs.get(token)
        if job is None or job.user_id != user_id:
            return None
        return job
