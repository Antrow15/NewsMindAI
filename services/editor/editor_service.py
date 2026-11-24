"""Editor desk — review queue, pitch duplicates, assign suggest, rework."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from dao.article_dao import ArticleDAO
from dao.content_dao import ContentDAO
from dao.evidence_dao import EvidenceDAO
from dao.news_dao import NewsDAO
from dao.notification_dao import NotificationDAO
from dao.story_pitch_dao import StoryPitchDAO
from database.connection import db_cursor
from entities.content.article import Article
from entities.content.content import Content
from entities.content.evidence import Evidence
from entities.content.news import News
from ml.common import normalize, similar_pairs
from ml.editor import predict_editor_queue_urgency
from utils.errors import ValidationError
from utils.validators import require_nonempty, require_optional_str, require_positive_id, require_title

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
        articles: ArticleDAO | None = None,
        evidence: EvidenceDAO | None = None,
        notifications: NotificationDAO | None = None,
    ) -> None:
        self.pitches = pitches or StoryPitchDAO()
        self.content = content or ContentDAO()
        self.articles = articles or ArticleDAO()
        self.news = NewsDAO()
        self.evidence = evidence or EvidenceDAO()
        self.notifications = notifications or NotificationDAO()

    def _resolve_journalist(self, assignee_user_id: int) -> int:
        with db_cursor() as cur:
            cur.execute(
                "SELECT journalist_id FROM journalist WHERE user_id = %s",
                (assignee_user_id,),
            )
            hit = cur.fetchone()
        if not hit:
            raise ValidationError("Assignee is not a journalist desk user.")
        return int(hit["journalist_id"])

    def _assigner_label(self, user_id: int | None) -> str:
        if not user_id:
            return "Editor"
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''), u.username) AS name
                FROM users u
                LEFT JOIN employee e ON e.employee_id = u.employee_id
                WHERE u.user_id = %s
                """,
                (user_id,),
            )
            hit = cur.fetchone()
        return str((hit or {}).get("name") or "Editor")

    def _notify_assignment(
        self,
        *,
        assignee_user_id: int,
        title: str,
        assigner_user_id: int | None,
        content_id: int,
        due_at: datetime | None,
        note: str,
    ) -> None:
        assigner = self._assigner_label(assigner_user_id)
        due_txt = due_at.strftime("%Y-%m-%d %H:%M UTC") if due_at else "No deadline set"
        self.notifications.create(
            user_id=assignee_user_id,
            type="assignment",
            title=f"New assignment: {title}",
            body=f"Assigned by {assigner}. Deadline: {due_txt}."
            + (f" Note: {note}" if note else ""),
            payload={
                "content_id": content_id,
                "assigner_user_id": assigner_user_id,
                "due_at": due_at.isoformat() if due_at else None,
            },
        )

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

    # Soft full load — one open story must NOT read as "at capacity".
    DESK_CAPACITY_FULL = 8

    @classmethod
    def capacity_score(cls, open_workload: int) -> float:
        """1.0 = empty desk, 0.0 = at/over soft capacity (~8 open items)."""
        w = max(0, int(open_workload or 0))
        return round(max(0.0, 1.0 - (w / float(cls.DESK_CAPACITY_FULL))), 4)

    def suggest_journalists(
        self,
        *,
        topic: str = "",
        title: str = "",
        limit: int = 3,
    ) -> dict[str, Any]:
        """Rank journalists by specialty match + remaining desk capacity + availability.

        Open workload = active desk items (draft / submitted / rework). Capacity is
        relative to a soft full load of ~8 items — a single assignment is light load.
        Returns the top ``limit`` matches (default 3).
        """
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
                JOIN role r ON r.role_id = u.role_id
                LEFT JOIN employee e ON e.employee_id = u.employee_id
                WHERE j.status = 'active'
                  AND u.account_status = 'active'
                  AND r.role_code = 'journalist'
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
            # Remaining capacity vs soft full load (not 1/(1+n), which marks 1 item as 50%).
            workload_score = self.capacity_score(workload)
            load_pct = min(
                100,
                round(100.0 * workload / float(self.DESK_CAPACITY_FULL)),
            )
            availability = str(row.get("availability_status") or "available").lower()
            avail_score = {
                "available": 1.0,
                "busy": 0.45,
                "away": 0.15,
                "leave": 0.0,
            }.get(availability, 0.3)

            # Specialty leads; capacity still matters but one story is not "full".
            score = round(
                specialty_score * 0.50 + workload_score * 0.35 + avail_score * 0.15,
                4,
            )
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
                    "capacity_full_at": self.DESK_CAPACITY_FULL,
                    "load_pct": load_pct,
                    "specialty_score": round(specialty_score, 4),
                    "workload_score": workload_score,
                    "availability_score": round(avail_score, 4),
                    "score": score,
                    "reason": (
                        f"specialty={specialty_score:.2f}, "
                        f"open={workload}/{self.DESK_CAPACITY_FULL} "
                        f"(capacity left={workload_score:.0%}), "
                        f"availability={availability}"
                    ),
                }
            )

        # Best overall score first; ties prefer lighter workload.
        ranked.sort(key=lambda r: (-r["score"], r["open_workload"], r["journalist_id"]))
        top_n = max(1, min(int(limit), 50))
        top = ranked[:top_n]
        for i, row in enumerate(top, start=1):
            row["rank"] = i
        return {
            "suggestions": top,
            "topic": topic or title,
            "method": "specialty_match + remaining_desk_capacity + availability",
            "capacity_full_at": self.DESK_CAPACITY_FULL,
            "scored_count": len(ranked),
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
        remarks = require_optional_str(remarks, "Remarks") or ""
        author_id = row.get("author_id")
        if author_id:
            with db_cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM journalist WHERE journalist_id = %s",
                    (int(author_id),),
                )
                hit = cur.fetchone()
            if hit and hit.get("user_id"):
                self.notifications.create(
                    user_id=int(hit["user_id"]),
                    type="rework",
                    title=f"Rework requested: {row.get('title') or 'Untitled'}",
                    body=remarks or "An editor sent this story back for rework.",
                    payload={"content_id": content_id},
                )
        return {
            **row,
            "remarks": remarks,
            "next_step": "Journalist updates content then resubmits (status=submitted)",
        }

    def assign_content(
        self,
        content_id: int,
        assignee_user_id: int,
        note: str = "",
        *,
        due_at: datetime | None = None,
        assigner_user_id: int | None = None,
    ) -> dict[str, Any]:
        content_id = require_positive_id(content_id, "Content ID")
        assignee_user_id = require_positive_id(assignee_user_id, "Assignee user ID")
        self.content.require(content_id)
        journalist_id = self._resolve_journalist(assignee_user_id)
        note = require_optional_str(note, "Note") or ""
        now = datetime.utcnow()
        self.content.update(
            content_id,
            author_id=journalist_id,
            assigned_by_user_id=assigner_user_id,
            assigned_at=now,
            due_at=due_at,
            assignment_note=note or None,
        )
        updated = self.content.require(content_id)
        self._notify_assignment(
            assignee_user_id=assignee_user_id,
            title=str(updated.get("title") or "Untitled"),
            assigner_user_id=assigner_user_id,
            content_id=content_id,
            due_at=due_at,
            note=note,
        )
        return {
            "content_id": content_id,
            "assignee_user_id": assignee_user_id,
            "journalist_id": journalist_id,
            "note": note,
            "due_at": due_at.isoformat() if due_at else None,
            "assigner": self._assigner_label(assigner_user_id),
            "content": updated,
        }

    def assign_pitch(
        self,
        story_pitch_id: int,
        assignee_user_id: int,
        *,
        assigner_user_id: int | None = None,
        note: str = "",
        due_at: datetime | None = None,
        auto_approve: bool = True,
    ) -> dict[str, Any]:
        """Approve (optional) + create draft article from pitch and assign to journalist."""
        pitch_id = require_positive_id(story_pitch_id, "Story pitch ID")
        assignee_user_id = require_positive_id(assignee_user_id, "Assignee user ID")
        pitch = self.pitches.require(pitch_id)
        status = str(pitch.get("status") or "").lower()
        if status == "rejected":
            raise ValidationError("Cannot assign a rejected pitch.")
        if status != "approved" and auto_approve:
            pitch = self.approve_pitch(pitch_id, assigner_user_id)
        elif status != "approved":
            raise ValidationError("Pitch must be approved before assignment.")

        journalist_id = self._resolve_journalist(assignee_user_id)
        note = require_optional_str(note, "Note") or ""
        title = require_title(pitch.get("title") or "Untitled pitch")
        summary = require_optional_str(pitch.get("summary"), "Summary") or ""
        body = (
            summary
            or f"Draft brief from approved story pitch “{title}”. Expand into a full article."
        )
        if len(body) < 40:
            body = (body + " " + ("Please develop this brief into a complete newsroom article.")).strip()
        now = datetime.utcnow()
        content_id = self.content.create(
            Content(
                author_id=journalist_id,
                title=title,
                summary=summary,
                raw_body=body,
                content_body=body,
                status="draft",
                content_kind="article",
                source_type="pitch_assignment",
            )
        )
        self.content.update(
            content_id,
            assigned_by_user_id=assigner_user_id,
            assigned_at=now,
            due_at=due_at,
            assignment_note=note or None,
        )
        article_id = self.articles.create(
            Article(
                content_id=content_id,
                story_pitch_id=pitch_id,
                article_type="feature",
                estimated_read_time=5,
            )
        )
        evidence_id = self.evidence.create(
            Evidence(
                content_id=content_id,
                title="Editor brief",
                evidence_type="brief",
                source_url="",
                body_text=summary or title,
                uploaded_by=journalist_id,
            )
        )
        self._notify_assignment(
            assignee_user_id=assignee_user_id,
            title=title,
            assigner_user_id=assigner_user_id,
            content_id=content_id,
            due_at=due_at,
            note=note,
        )
        return {
            "story_pitch_id": pitch_id,
            "content_id": content_id,
            "article_id": article_id,
            "evidence_id": evidence_id,
            "assignee_user_id": assignee_user_id,
            "journalist_id": journalist_id,
            "due_at": due_at.isoformat() if due_at else None,
            "assigner": self._assigner_label(assigner_user_id),
            "note": note,
            "pitch": _annotate_pitch_source(self.pitches.require(pitch_id)),
            "content": self.content.require(content_id),
        }

    def create_and_assign(
        self,
        *,
        kind: str,
        title: str,
        body: str,
        summary: str = "",
        assignee_user_id: int,
        assigner_user_id: int | None = None,
        note: str = "",
        due_at: datetime | None = None,
        event_type: str = "city",
        event_location: str = "",
        severity: str = "medium",
        breaking: bool = False,
        article_type: str = "feature",
        read_time: int = 5,
        evidence_title: str = "",
    ) -> dict[str, Any]:
        """Editor creates news/article as a draft and assigns it to a journalist."""
        kind_norm = str(kind or "").strip().lower()
        if kind_norm not in {"news", "article"}:
            raise ValidationError("kind must be 'news' or 'article'.")
        title = require_title(title)
        body = require_nonempty(body, "Body")
        if len(body) < 40:
            raise ValidationError("Body must be at least 40 characters.")
        summary = require_optional_str(summary, "Summary") or ""
        assignee_user_id = require_positive_id(assignee_user_id, "Assignee user ID")
        journalist_id = self._resolve_journalist(assignee_user_id)
        note = require_optional_str(note, "Note") or ""
        now = datetime.utcnow()

        content_id = self.content.create(
            Content(
                author_id=journalist_id,
                title=title,
                summary=summary,
                raw_body=body,
                content_body=body,
                status="draft",
                content_kind=kind_norm,
                source_type="editor_assignment",
            )
        )
        self.content.update(
            content_id,
            assigned_by_user_id=assigner_user_id,
            assigned_at=now,
            due_at=due_at,
            assignment_note=note or None,
        )
        news_id = None
        article_id = None
        if kind_norm == "news":
            news_id = self.news.create(
                News(
                    content_id=content_id,
                    event_title=title,
                    event_type=require_nonempty(event_type or "city", "Event type"),
                    event_location=require_optional_str(event_location, "Event location") or "",
                    severity=str(severity or "medium"),
                    breaking_news_flag=bool(breaking),
                )
            )
        else:
            article_id = self.articles.create(
                Article(
                    content_id=content_id,
                    article_type=str(article_type or "feature"),
                    estimated_read_time=max(1, int(read_time or 5)),
                )
            )

        ev_title = require_optional_str(evidence_title, "Evidence title") or f"Editor brief · {title}"
        evidence_id = self.evidence.create(
            Evidence(
                content_id=content_id,
                title=ev_title[:200],
                evidence_type="document",
                source_url="",
                body_text=note or summary or body[:500],
                uploaded_by=journalist_id,
            )
        )
        self._notify_assignment(
            assignee_user_id=assignee_user_id,
            title=title,
            assigner_user_id=assigner_user_id,
            content_id=content_id,
            due_at=due_at,
            note=note,
        )
        return {
            "content_id": content_id,
            "news_id": news_id,
            "article_id": article_id,
            "evidence_id": evidence_id,
            "kind": kind_norm,
            "assignee_user_id": assignee_user_id,
            "journalist_id": journalist_id,
            "due_at": due_at.isoformat() if due_at else None,
            "assigner": self._assigner_label(assigner_user_id),
            "note": note,
            "content": self.content.require(content_id),
        }
