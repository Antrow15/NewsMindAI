"""Editor review actions on adaptation drafts."""

from __future__ import annotations

from typing import Any

from dao.adaptation_dao import AdaptationDAO
from ml.adaptation import format_output, predict_sentences, validate_facts
from utils.errors import ValidationError
from utils.validators import require_nonempty, require_title


class ReviewService:
    def __init__(self, dao: AdaptationDAO | None = None) -> None:
        self.dao = dao or AdaptationDAO()

    def require_draft(self, draft_id: int) -> dict[str, Any]:
        return self.dao.require_draft(draft_id)

    def approve(self, draft_id: int, reviewer_id: int | None, remarks: str | None = None) -> dict[str, Any]:
        draft = self.dao.require_draft(draft_id)
        self.dao.update_draft_status(draft_id, "APPROVED")
        self.dao.add_review(
            draft_id=draft_id,
            action="APPROVE",
            reviewed_by=reviewer_id,
            remarks=remarks,
        )
        return self.dao.require_draft(draft_id)

    def reject(self, draft_id: int, reviewer_id: int | None, remarks: str) -> dict[str, Any]:
        remarks = require_nonempty(remarks, "Remarks")
        if len(remarks) < 3:
            raise ValidationError("Remarks must be at least 3 characters.")
        self.dao.require_draft(draft_id)
        self.dao.update_draft_status(draft_id, "REJECTED")
        self.dao.add_review(
            draft_id=draft_id,
            action="REJECT",
            reviewed_by=reviewer_id,
            remarks=remarks,
        )
        return self.dao.require_draft(draft_id)

    def regenerate(
        self,
        draft_id: int,
        reviewer_id: int | None,
        remarks: str,
    ) -> dict[str, Any]:
        remarks = require_nonempty(remarks, "Remarks")
        draft = self.dao.require_draft(draft_id)
        request = self.dao.require_request(int(draft["request_id"]))
        text = remarks.lower()
        threshold_delta = 0.10 if "shorter" in text else (-0.10 if ("longer" in text or "more detail" in text) else 0.0)
        sentence_delta = -1 if "shorter" in text else (2 if ("longer" in text or "more detail" in text) else 0)

        selected, meta, threshold = predict_sentences(
            str(request["original_title"]),
            str(request["original_content"]),
            str(draft["platform"]),
            threshold_delta,
            sentence_delta,
            "quote" in text,
            ("number" in text or "figure" in text),
        )
        new_title, content = format_output(str(draft["platform"]), str(request["original_title"]), selected)
        flags = validate_facts(str(request["original_content"]), content)
        versions = self.dao.list_versions(int(draft["request_id"]), str(draft["platform"]))
        next_version = max((int(v["version_number"]) for v in versions), default=0) + 1
        child_id = self.dao.create_draft(
            request_id=int(draft["request_id"]),
            platform=str(draft["platform"]),
            version_number=next_version,
            adapted_title=new_title,
            adapted_content=content,
            model_version=str(meta.get("version", "heuristic-1.0.0")),
            status="PENDING_REVIEW" if flags.get("passed") else "REQUIRES_MANUAL_REVIEW",
            parent_draft_id=draft_id,
            generation_parameters={
                "threshold": threshold,
                "remarks": remarks,
                "selected_sentence_indexes": [row[0] for row in selected],
            },
            validation_flags=flags,
        )
        self.dao.update_draft_status(draft_id, "REGENERATION_REQUESTED")
        self.dao.add_review(
            draft_id=draft_id,
            action="REGENERATE",
            reviewed_by=reviewer_id,
            remarks=remarks,
        )
        return self.dao.require_draft(child_id)

    def finalize(
        self,
        draft_id: int,
        reviewer_id: int | None,
        final_title: str,
        final_content: str,
        remarks: str | None = None,
    ) -> dict[str, Any]:
        draft = self.dao.require_draft(draft_id)
        if str(draft.get("status")) == "FINALIZED":
            raise ValidationError("Draft is already finalized.")
        existing = self.dao.get_final_for_draft(draft_id)
        if existing:
            raise ValidationError("Draft is already finalized.")

        request = self.dao.require_request(int(draft["request_id"]))
        title = require_title(final_title)
        content = require_nonempty(final_content, "Final content")
        flags = validate_facts(str(request["original_content"]), content)
        if not flags.get("passed"):
            raise ValidationError(
                "Final content contains unsupported numeric facts: "
                + str(flags)
            )

        self.dao.update_draft_status(draft_id, "FINALIZED")
        self.dao.add_review(
            draft_id=draft_id,
            action="FINALIZE",
            reviewed_by=reviewer_id,
            remarks=remarks,
        )
        self.dao.save_final(
            draft_id=draft_id,
            final_title=title,
            final_content=content,
            finalized_by=reviewer_id,
            remarks=remarks,
        )
        return self.dao.require_draft(draft_id)

    def versions(self, draft_id: int) -> list[dict[str, Any]]:
        draft = self.dao.require_draft(draft_id)
        return self.dao.list_versions(int(draft["request_id"]), str(draft["platform"]))
