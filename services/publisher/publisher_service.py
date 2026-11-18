"""Publication queue — approve, template, preview, publish, schedule."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from config.constants import PUBLICATION_TEMPLATES
from dao.content_dao import ContentDAO
from dao.publication_dao import PublicationDAO
from utils.errors import ValidationError
from utils.validators import require_positive_id


class PublisherService:
    def __init__(
        self,
        publications: PublicationDAO | None = None,
        content: ContentDAO | None = None,
    ) -> None:
        self.publications = publications or PublicationDAO()
        self.content = content or ContentDAO()

    def list_articles(self, limit: int = 100) -> dict[str, Any]:
        return {"articles": self.publications.list_ready_articles(limit=limit)}

    def templates(self) -> dict[str, Any]:
        return {"templates": list(PUBLICATION_TEMPLATES)}

    def _pub_for_content(self, content_id: int) -> dict[str, Any]:
        content_id = require_positive_id(content_id, "Content ID")
        row = self.content.require(content_id)
        if str(row.get("status")) != "approved":
            raise ValidationError("Only approved content can enter the publication queue.")
        return self.publications.ensure_for_content(content_id)

    def approve(self, content_id: int) -> dict[str, Any]:
        pub = self._pub_for_content(content_id)
        updated = self.publications.update_fields(int(pub["publication_id"]), status="approved")
        return {"content_id": content_id, "publication": updated}

    def assign_template(self, content_id: int, template_code: str) -> dict[str, Any]:
        codes = {t["code"] for t in PUBLICATION_TEMPLATES}
        if template_code not in codes:
            raise ValidationError(
                f"Unknown template '{template_code}'. Allowed: {', '.join(sorted(codes))}"
            )
        pub = self._pub_for_content(content_id)
        updated = self.publications.update_fields(
            int(pub["publication_id"]),
            template_code=template_code,
        )
        return {"content_id": content_id, "publication": updated}

    def preview(self, content_id: int) -> dict[str, Any]:
        content = self.content.require(require_positive_id(content_id, "Content ID"))
        pub = self.publications.read_by_content_id(content_id) or {}
        template_code = pub.get("template_code") or "web_standard"
        template = next(
            (t for t in PUBLICATION_TEMPLATES if t["code"] == template_code),
            PUBLICATION_TEMPLATES[0],
        )
        body = content.get("content_body") or content.get("raw_body") or ""
        return {
            "content_id": content_id,
            "title": content.get("title"),
            "template": template,
            "preview_html": (
                f"<article data-template='{template['code']}'>"
                f"<h1>{content.get('title') or ''}</h1>"
                f"<p>{body}</p>"
                f"</article>"
            ),
            "publication_status": pub.get("status"),
        }

    def publish(self, content_id: int) -> dict[str, Any]:
        pub = self._pub_for_content(content_id)
        if not pub.get("template_code"):
            raise ValidationError("Assign a template before publishing.")
        updated = self.publications.update_fields(
            int(pub["publication_id"]),
            status="published",
            published_at=datetime.utcnow(),
            scheduled_at=None,
        )
        self.content.update_status(content_id, "published")
        return {"content_id": content_id, "publication": updated}

    def schedule(self, content_id: int, scheduled_at: datetime) -> dict[str, Any]:
        compare_at = scheduled_at.replace(tzinfo=None) if scheduled_at.tzinfo else scheduled_at
        if compare_at <= datetime.utcnow():
            raise ValidationError("scheduled_at must be in the future.")
        pub = self._pub_for_content(content_id)
        if not pub.get("template_code"):
            raise ValidationError("Assign a template before scheduling.")
        updated = self.publications.update_fields(
            int(pub["publication_id"]),
            status="scheduled",
            scheduled_at=scheduled_at,
        )
        return {"content_id": content_id, "publication": updated}

    def analytics(self) -> dict[str, Any]:
        return self.publications.analytics()
