"""Editor desk — review queue, pitch duplicates, assign suggest, rework."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from dao.content_dao import ContentDAO
from dao.story_pitch_dao import StoryPitchDAO
from database.connection import db_cursor
from ml.common import normalize, similar_pairs
from ml.editor import predict_editor_queue_urgency
from utils.validators import require_optional_str, require_positive_id, require_title

# Lower number = show earlier in the editor queue
URGENCY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
def _urgency_rank(level: str | None) -> int:
    return URGENCY_ORDER.get(str(level or "medium").lower(), 4)


def _annotate_pitch_source(pitch: dict[str, Any]) -> dict[str, Any]:
    source = str(pitch.get("source_type") or "").strip().upper() or "UNKNOWN"
    if source in {"AI_GENERATED", "AIA", "AI"}:
        created_by = "AIA"
        source_type = "AI_GENERATED"
    elif source in {"MANUAL", "EDITOR", "HUMAN"}:
        created_by = "MANUAL"
        source_type = "MANUAL"
    else:
        created_by = "UNKNOWN"
        source_type = source
    return {**pitch, "source_type": source_type, "created_by_desk": created_by}


class EditorService:
    def __init__(
        self,
        pitches: StoryPitchDAO | None = None,
        content: ContentDAO | None = None,
    ) -> None:
        self.pitches = pitches or StoryPitchDAO()
        self.content = content or ContentDAO()

    def score_editor_queue_urgency(self, title: str, summary: str = "") -> dict[str, Any]:
        """Score how urgent a headline is for the editor review queue."""
        headline = require_title(title)
        body = require_optional_str(summary, "Summary") or ""
        return predict_editor_queue_urgency(headline, body)

    def list_pitches(self, status: str = "submitted", limit: int = 100) -> dict[str, Any]:
        rows = self.pitches.list_by_status(status, limit=limit)
        return {"pitches": [_annotate_pitch_source(r) for r in rows]}

    def find_duplicate_pitches(
        self,
        *,
        title: str | None = None,
        summary: str = "",
        status: str = "submitted",
        threshold: float = 0.45,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Near-duplicate pitches among open queue (shows AIA vs manual source)."""
        open_pitches = [_annotate_pitch_source(p) for p in self.pitches.list_by_status(status, limit=300)]
        docs = [
            {
                "id": p.get("story_pitch_id"),
                "title": p.get("title") or "",
                "text": f"{p.get('title') or ''}. {p.get('summary') or ''}",
                "source_type": p.get("source_type"),
                "created_by_desk": p.get("created_by_desk"),
                "pitch_importance": p.get("priority"),
            }
            for p in open_pitches
        ]
        by_id = {d["id"]: d for d in docs}

        if title:
            query_doc = {
                "id": "query",
                "title": title,
                "text": f"{title}. {summary or ''}",
            }
            corpus = [query_doc, *docs]
            pairs = similar_pairs(corpus, threshold=threshold, limit=limit * 3)
            matches = []
            for pair in pairs:
                left, right = pair.get("left_id"), pair.get("right_id")
                other_id = right if left == "query" else left if right == "query" else None
                if other_id is None or other_id == "query":
                    continue
                other = by_id.get(other_id) or {}
                matches.append(
                    {
                        "story_pitch_id": other_id,
                        "title": other.get("title"),
                        "score": pair.get("score"),
                        "source_type": other.get("source_type"),
                        "created_by_desk": other.get("created_by_desk"),
                        "pitch_importance": other.get("pitch_importance"),
                    }
                )
            matches = matches[:limit]
            return {
                "query_title": title,
                "matches": matches,
                "match_count": len(matches),
                "scanned": len(docs),
            }

        pairs = similar_pairs(docs, threshold=threshold, limit=limit)
        enriched = []
        for pair in pairs:
            left = by_id.get(pair.get("left_id")) or {}
            right = by_id.get(pair.get("right_id")) or {}
            enriched.append(
                {
                    **pair,
                    "left_source_type": left.get("source_type"),
                    "left_created_by_desk": left.get("created_by_desk"),
                    "right_source_type": right.get("source_type"),
                    "right_created_by_desk": right.get("created_by_desk"),
                }
            )
        return {"pairs": enriched, "pair_count": len(enriched), "scanned": len(docs)}

    def suggest_journalists(
        self,
        *,
        topic: str = "",
        title: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Rank journalists by specialty match + inverse workload + availability."""
        needle = normalize(f"{topic} {title}")
        needle_tokens = set(needle.split()) if needle else set()

        with db_cursor() as cur:
            cur.execute(
                """
                SELECT j.journalist_id, j.user_id, j.primary_specialization,
                       j.secondary_specialization, j.availability_status, j.status,
                       u.username,
                       COALESCE(NULLIF(TRIM(e.first_name || ' ' || e.last_name), ''), u.username) AS full_name,
                       (
                         SELECT COUNT(*) FROM content c
                         WHERE c.author_id = j.journalist_id
                           AND c.status IN ('draft', 'submitted', 'rework')
                       ) AS open_workload
                FROM journalist j
                JOIN users u ON u.user_id = j.user_id
                LEFT JOIN employee e ON e.employee_id = u.employee_id
                WHERE j.status = 'active'
                ORDER BY j.journalist_id
                """,
            )
            rows = [dict(r) for r in cur.fetchall() or []]

        ranked: list[dict[str, Any]] = []
        for row in rows:
            primary = normalize(str(row.get("primary_specialization") or ""))
            secondary = normalize(str(row.get("secondary_specialization") or ""))
            specialty_tokens = set((primary + " " + secondary).split())
            overlap = len(needle_tokens & specialty_tokens) if needle_tokens else 0
            specialty_score = 0.0
            if needle and primary and primary in needle:
                specialty_score = 1.0
            elif needle and secondary and secondary in needle:
                specialty_score = 0.7
            elif overlap:
                specialty_score = min(1.0, overlap / max(len(needle_tokens), 1))
            elif not needle_tokens:
                specialty_score = 0.35

            workload = int(row.get("open_workload") or 0)
            workload_score = 1.0 / (1.0 + workload)
            availability = str(row.get("availability_status") or "available").lower()
            avail_score = {
                "available": 1.0,
                "busy": 0.45,
                "away": 0.15,
                "leave": 0.0,
            }.get(availability, 0.3)

            score = round(specialty_score * 0.55 + workload_score * 0.30 + avail_score * 0.15, 4)
            ranked.append(
                {
                    "journalist_id": row["journalist_id"],
                    "user_id": row["user_id"],
                    "username": row.get("username"),
                    "full_name": row.get("full_name"),
                    "primary_specialization": row.get("primary_specialization"),
                    "secondary_specialization": row.get("secondary_specialization"),
                    "availability_status": availability,
                    "open_workload": workload,
                    "specialty_score": round(specialty_score, 4),
                    "score": score,
                    "reason": (
                        f"specialty={specialty_score:.2f}, "
                        f"workload={workload}, availability={availability}"
                    ),
                }
            )

        ranked.sort(key=lambda r: (-r["score"], r["open_workload"], r["journalist_id"]))
        return {
            "suggestions": ranked[: max(1, min(int(limit), 50))],
            "topic": topic or title,
            "method": "specialty_match + inverse_workload + availability",
        }

    def list_content(self, status: str = "submitted", limit: int = 100) -> dict[str, Any]:
        items = self.content.list_by_status(status, limit=limit)
        scored: list[dict[str, Any]] = []
        for row in items:
            title = str(row.get("title") or "")
            body = str(row.get("summary") or row.get("content_body") or row.get("raw_body") or "")
            prediction = predict_editor_queue_urgency(title, body)
            scored.append(
                {
                    **row,
                    "editor_queue_urgency": prediction["urgency"],
                    "urgency_confidence": prediction.get("confidence"),
                    "urgency_source": prediction.get("source"),
                    "model_label": prediction.get("model_label"),
                }
            )
        scored.sort(
            key=lambda row: (
                _urgency_rank(row.get("editor_queue_urgency")),
                -int(row.get("content_id") or 0),
            )
        )
        return {"items": scored}

    def review_queue(
        self,
        *,
        pitch_status: str = "submitted",
        content_status: str = "submitted",
        limit: int = 100,
    ) -> dict[str, Any]:
        pitches = self.list_pitches(status=pitch_status, limit=limit)["pitches"]
        content = self.list_content(status=content_status, limit=limit)["items"]

        tasks: list[dict[str, Any]] = []
        for pitch in pitches:
            # Pitch importance comes from AIA formula / DB column "priority"
            tasks.append(
                {
                    "task_type": "pitch",
                    "task_id": pitch.get("story_pitch_id"),
                    "title": pitch.get("title"),
                    "summary": pitch.get("summary"),
                    "urgency": pitch.get("priority") or "medium",
                    "urgency_kind": "pitch_importance",
                    "status": pitch.get("status"),
                    "source_type": pitch.get("source_type"),
                    "created_by_desk": pitch.get("created_by_desk"),
                    "item": pitch,
                }
            )
        for item in content:
            # Content urgency comes from the editor queue urgency model
            tasks.append(
                {
                    "task_type": "content",
                    "task_id": item.get("content_id"),
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "urgency": item.get("editor_queue_urgency") or "medium",
                    "urgency_kind": "editor_queue_urgency",
                    "status": item.get("status"),
                    "source": item.get("urgency_source") or "model",
                    "confidence": item.get("urgency_confidence"),
                    "item": item,
                }
            )
        tasks.sort(
            key=lambda row: (
                _urgency_rank(str(row.get("urgency"))),
                0 if row.get("task_type") == "pitch" else 1,
                -int(row.get("task_id") or 0),
            )
        )
        return {
            "tasks": tasks,
            "pitch_count": len(pitches),
            "content_count": len(content),
        }

    def approve_pitch(self, story_pitch_id: int, reviewer_id: int | None) -> dict[str, Any]:
        pitch_id = require_positive_id(story_pitch_id, "Story pitch ID")
        self.pitches.require(pitch_id)
        self.pitches.update(
            pitch_id,
            status="approved",
            approved_by=reviewer_id,
            approved_at=datetime.utcnow(),
        )
        return _annotate_pitch_source(self.pitches.require(pitch_id))

    def reject_pitch(self, story_pitch_id: int, remarks: str = "") -> dict[str, Any]:
        pitch_id = require_positive_id(story_pitch_id, "Story pitch ID")
        self.pitches.require(pitch_id)
        self.pitches.update(pitch_id, status="rejected")
        row = _annotate_pitch_source(self.pitches.require(pitch_id))
        return {**row, "remarks": require_optional_str(remarks, "Remarks") or ""}

    def approve_content(self, content_id: int) -> dict[str, Any]:
        content_id = require_positive_id(content_id, "Content ID")
        self.content.require(content_id)
        self.content.update_status(content_id, "approved")
        return self.content.require(content_id)

    def reject_content(self, content_id: int, remarks: str = "") -> dict[str, Any]:
        content_id = require_positive_id(content_id, "Content ID")
        self.content.require(content_id)
        self.content.update_status(content_id, "rejected")
        row = self.content.require(content_id)
        return {**row, "remarks": require_optional_str(remarks, "Remarks") or ""}

    def send_content_rework(self, content_id: int, remarks: str = "") -> dict[str, Any]:
        """Editor → journalist rework loop."""
        content_id = require_positive_id(content_id, "Content ID")
        self.content.require(content_id)
        self.content.update_status(content_id, "rework")
        row = self.content.require(content_id)
        return {
            **row,
            "remarks": require_optional_str(remarks, "Remarks") or "",
            "next_step": "Journalist updates content then resubmits (status=submitted)",
        }

    def assign_content(
        self,
        content_id: int,
        assignee_user_id: int,
        note: str = "",
    ) -> dict[str, Any]:
        content_id = require_positive_id(content_id, "Content ID")
        assignee_user_id = require_positive_id(assignee_user_id, "Assignee user ID")
        row = self.content.require(content_id)

        journalist_id = None
        with db_cursor() as cur:
            cur.execute(
                "SELECT journalist_id FROM journalist WHERE user_id = %s",
                (assignee_user_id,),
            )
            hit = cur.fetchone()
            if hit:
                journalist_id = int(hit["journalist_id"])

        if journalist_id is not None:
            self.content.update(content_id, author_id=journalist_id)
        elif row.get("author_id") is None:
            # Fallback: store user_id only if no journalist desk row (legacy paths).
            self.content.update(content_id, author_id=assignee_user_id)

        updated = self.content.require(content_id)
        return {
            "content_id": content_id,
            "assignee_user_id": assignee_user_id,
            "journalist_id": journalist_id,
            "note": require_optional_str(note, "Note") or "",
            "content": updated,
        }
