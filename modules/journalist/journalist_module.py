"""Journalist tools façade — capability check, then call a service."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from config.constants import CAP_JOURNALIST_TOOLS
from dao.journalist_dao import JournalistDAO
from dao.notification_dao import NotificationDAO
from database.connection import db_cursor
from services.access import require_capability_session
from services.content import ContentService
from services.journalist import (
    assess_credibility,
    find_duplicates,
    validate_article,
)
from utils.errors import ValidationError


class JournalistModule:
    def __init__(
        self,
        session_token: str | None = None,
        content: ContentService | None = None,
        notifications: NotificationDAO | None = None,
    ) -> None:
        self.session_token = session_token
        self.content = content or ContentService()
        self.notifications = notifications or NotificationDAO()

    def _user(self) -> dict[str, Any]:
        return require_capability_session(CAP_JOURNALIST_TOOLS, self.session_token)

    def _author_id(self, user: dict[str, Any]) -> int | None:
        """content.author_id FK → journalist.journalist_id (not users.user_id)."""
        profiles = user.get("profiles") or {}
        journalist_id = profiles.get("journalist_id")
        if journalist_id:
            return int(journalist_id)
        return JournalistDAO().ensure_for_user(int(user["user_id"]))

    def duplicates(
        self,
        documents: Sequence[Mapping[str, Any]] | None = None,
        *,
        threshold: float = 0.5,
        limit: int = 20,
    ) -> dict[str, Any]:
        user = self._user()
        pairs = find_duplicates(documents, threshold=threshold, limit=limit)
        return {"actor": user["username"], "pairs": pairs}

    def validate(self, record: Mapping[str, Any] | None = None) -> dict[str, Any]:
        user = self._user()
        return {"actor": user["username"], **validate_article(record)}

    def credibility(self, content_id: int, *, limit: int = 5) -> dict[str, Any]:
        """Evaluate a news/article using only its own attached evidence."""
        user = self._user()
        row = self.content.get_content(int(content_id))
        text = str(row.get("content_body") or row.get("raw_body") or row.get("summary") or "").strip()
        if not text:
            raise ValidationError("Content has no body to assess.")
        attached = self.content.list_evidence(int(content_id))
        if not attached:
            raise ValidationError("Attach evidence before credibility assessment.")
        evidence_docs = [
            {
                "id": item.get("evidence_id"),
                "title": item.get("title") or "",
                "text": item.get("body_text") or item.get("ocr_text") or "",
            }
            for item in attached
        ]
        report = assess_credibility(text, evidence_docs, limit=limit)
        return {
            "actor": user["username"],
            "content_id": int(content_id),
            "evidence_count": len(evidence_docs),
            **report,
        }

    # ── Desk content (parity with console journalist menu) ─────────────────

    def add_news(self, **kwargs: Any) -> dict[str, Any]:
        user = self._user()
        kwargs.setdefault("author_id", self._author_id(user))
        created = self.content.add_news(**kwargs)
        return {"actor": user["username"], **created}

    def add_article(self, **kwargs: Any) -> dict[str, Any]:
        user = self._user()
        kwargs.setdefault("author_id", self._author_id(user))
        created = self.content.add_article(**kwargs)
        return {"actor": user["username"], **created}

    def list_content(self, limit: int = 20, status: str | None = None) -> dict[str, Any]:
        user = self._user()
        author_id = self._author_id(user)
        items = self.content.list_content(
            limit=limit,
            status=status,
            author_id=author_id,
        )
        return {"actor": user["username"], "items": items}

    def _assigner_name(self, user_id: int | None) -> str:
        if not user_id:
            return "Unassigned"
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(NULLIF(TRIM(CONCAT(e.first_name, ' ', e.last_name)), ''), u.username) AS name
                FROM users u
                LEFT JOIN employee e ON e.employee_id = u.employee_id
                WHERE u.user_id = %s
                """,
                (int(user_id),),
            )
            hit = cur.fetchone()
        return str((hit or {}).get("name") or "Editor")

    def _pitch_title(self, content_id: int) -> str | None:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT sp.title
                FROM article a
                JOIN story_pitch sp ON sp.story_pitch_id = a.story_pitch_id
                WHERE a.content_id = %s
                """,
                (int(content_id),),
            )
            hit = cur.fetchone()
        return str(hit["title"]) if hit and hit.get("title") else None

    def _assignment_card(self, row: dict[str, Any]) -> dict[str, Any]:
        cid = int(row["content_id"])
        due = row.get("due_at")
        return {
            "key": cid,
            "title": row.get("title") or "Untitled",
            "status": row.get("status"),
            "kind": row.get("content_kind") or "article",
            "summary": row.get("summary") or "",
            "assigned_by": self._assigner_name(row.get("assigned_by_user_id")),
            "deadline": due.isoformat() if hasattr(due, "isoformat") else due,
            "note": row.get("assignment_note") or "",
            "brief_from_pitch": self._pitch_title(cid),
            "updated_at": (
                row["updated_at"].isoformat()
                if hasattr(row.get("updated_at"), "isoformat")
                else row.get("updated_at")
            ),
        }

    def list_assignments(self, limit: int = 50) -> dict[str, Any]:
        user = self._user()
        author_id = self._author_id(user)
        rows = self.content.list_content(
            limit=limit,
            author_id=author_id,
            assigned_only=True,
        )
        return {
            "actor": user["username"],
            "assignments": [self._assignment_card(r) for r in rows],
        }

    def list_notifications(
        self,
        *,
        unread_only: bool = False,
        limit: int = 50,
    ) -> dict[str, Any]:
        user = self._user()
        uid = int(user["user_id"])
        items = self.notifications.list_for_user(uid, unread_only=unread_only, limit=limit)
        cards = []
        for n in items:
            cards.append(
                {
                    "key": int(n["notification_id"]),
                    "type": n.get("type"),
                    "title": n.get("title"),
                    "body": n.get("body") or "",
                    "unread": n.get("read_at") is None,
                    "created_at": (
                        n["created_at"].isoformat()
                        if hasattr(n.get("created_at"), "isoformat")
                        else n.get("created_at")
                    ),
                }
            )
        return {
            "actor": user["username"],
            "unread_count": self.notifications.unread_count(uid),
            "notifications": cards,
        }

    def mark_notification_read(self, notification_id: int) -> dict[str, Any]:
        user = self._user()
        changed = self.notifications.mark_read(int(notification_id), int(user["user_id"]))
        return {"ok": changed > 0, "notification_id": int(notification_id)}

    def mark_all_notifications_read(self) -> dict[str, Any]:
        user = self._user()
        changed = self.notifications.mark_all_read(int(user["user_id"]))
        return {"ok": True, "marked": changed}

    def dashboard(self) -> dict[str, Any]:
        user = self._user()
        author_id = self._author_id(user)
        counts = self.content.repo.content.count_by_author_status(int(author_id)) if author_id else {}
        assignments = self.list_assignments(limit=8)["assignments"]
        notifs = self.list_notifications(unread_only=True, limit=8)
        upcoming = [a for a in assignments if a.get("deadline")][:5]
        return {
            "actor": user["username"],
            "metrics": {
                "drafts": counts.get("draft", 0),
                "submitted": counts.get("submitted", 0),
                "rework": counts.get("rework", 0),
                "approved": counts.get("approved", 0),
                "published": counts.get("published", 0),
                "open_assignments": len(assignments),
                "unread_notifications": notifs.get("unread_count", 0),
            },
            "assignments": assignments,
            "upcoming_deadlines": upcoming,
            "notifications": notifs.get("notifications") or [],
        }

    def related_content(
        self,
        title: str = "",
        text: str = "",
        *,
        limit: int = 8,
    ) -> dict[str, Any]:
        from ml.knowledge import score_content_relevancy

        user = self._user()
        result = score_content_relevancy(title, text, limit=limit)
        size = int(result.get("corpus_size") or result.get("knowledge_base_size") or 0)
        return {
            "actor": user["username"],
            "matches": result.get("matches") or [],
            "relevancy": result.get("relevancy") or "none",
            "best_score": float(result.get("best_score") or 0.0),
            "corpus_size": size,
            "knowledge_base_size": size,
            "source": result.get("source") or "content",
            "method": result.get("method") or "tfidf_cosine",
        }

    def get_content(self, content_id: int) -> dict[str, Any]:
        user = self._user()
        return {"actor": user["username"], "content": self.content.get_content(content_id)}

    def list_news(self, limit: int = 20) -> dict[str, Any]:
        user = self._user()
        return {"actor": user["username"], "items": self.content.list_news(limit=limit)}

    def add_evidence(self, **kwargs: Any) -> dict[str, Any]:
        user = self._user()
        if not kwargs.get("content_id"):
            raise ValidationError("content_id is required — evidence must attach to a news/article.")
        evidence_id = self.content.add_evidence(**kwargs)
        return {"actor": user["username"], "evidence_id": evidence_id}

    def list_evidence(self, content_id: int) -> dict[str, Any]:
        user = self._user()
        items = self.content.list_evidence(content_id)
        return {"actor": user["username"], "content_id": content_id, "items": items}

    def update_content_status(self, content_id: int, status: str) -> dict[str, Any]:
        user = self._user()
        updated = self.content.update_content_status(content_id, status)
        return {"actor": user["username"], **updated}
