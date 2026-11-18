"""Before/after quality metrics and reject reasons."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils.helpers import project_path


@dataclass
class QualityReport:
    input_count: int = 0
    output_count: int = 0
    rejected_count: int = 0
    stage_stats: list[dict[str, Any]] = field(default_factory=list)
    reject_reasons: dict[str, int] = field(default_factory=dict)

    def add_stage(self, name: str, stats: dict[str, Any], rejected: list[dict[str, Any]]) -> None:
        self.stage_stats.append({"cleaner": name, **stats})
        reasons = Counter(str(r.get("_reject_reason") or "unknown") for r in rejected)
        for key, value in reasons.items():
            self.reject_reasons[key] = self.reject_reasons.get(key, 0) + value

    def finalize(self, input_count: int, output_count: int) -> None:
        self.input_count = input_count
        self.output_count = output_count
        self.rejected_count = max(0, input_count - output_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_count": self.input_count,
            "output_count": self.output_count,
            "rejected_count": self.rejected_count,
            "reject_reasons": self.reject_reasons,
            "stage_stats": self.stage_stats,
        }

    def write(self, filename: str = "quality_report.json") -> Path:
        out_dir = project_path("data", "processed")
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / filename
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path
