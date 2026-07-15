"""Policy evidence storage — persist and retrieve gate verification records.

Evidence is written atomically under
.agentharness-local/evidence/<policy-hash>/<gate>/record.json.
"""

from __future__ import annotations

import json
import tempfile
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvidenceRecord:
    """A single gate verification evidence record."""

    policy_hash: str
    gate: str
    outcome: str
    args: list[str]
    output: str


class EvidenceStore:
    """Reads and writes evidence records under a project root."""

    def __init__(self, root: Path) -> None:
        self._base = root / ".agentharness-local" / "evidence"

    def _record_path(self, policy_hash: str, gate: str) -> Path:
        return self._base / policy_hash / gate / "record.json"

    def write(self, record: EvidenceRecord) -> None:
        """Write *record* atomically to the evidence store."""
        path = self._record_path(record.policy_hash, record.gate)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(
            {
                "policy_hash": record.policy_hash,
                "gate": record.gate,
                "outcome": record.outcome,
                "args": record.args,
                "output": record.output,
            },
            sort_keys=True,
        )
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(data)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def read(self, policy_hash: str, gate: str) -> EvidenceRecord | None:
        """Return the evidence record for *policy_hash*/*gate*, or None."""
        path = self._record_path(policy_hash, gate)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return EvidenceRecord(
                policy_hash=data["policy_hash"],
                gate=data["gate"],
                outcome=data["outcome"],
                args=data["args"],
                output=data["output"],
            )
        except (json.JSONDecodeError, KeyError):
            return None
