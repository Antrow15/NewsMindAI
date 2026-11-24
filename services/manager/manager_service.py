"""Newsroom manager — ops overview, bottlenecks, business analytics."""

from __future__ import annotations

from typing import Any

from dao.content_dao import ContentDAO
from dao.publication_dao import PublicationDAO
from dao.story_pitch_dao import StoryPitchDAO
from database.connection import db_cursor
from services.editor.editor_service import EditorService


class ManagerService:
    def __init__(self) -> None:
        self.editor = EditorService()
        self.pitches = StoryPitchDAO()
        self.content = ContentDAO()
        self.publications = PublicationDAO()

    def overview(self) -> dict[str, Any]:
        submitted_pitches = self.pitches.list_by_status("submitted", limit=500)
        submitted_content = self.content.list_by_status("submitted", limit=500)
        approved_content = self.content.list_by_status("approved", limit=500)
        analytics = self.publications.analytics()
        return {
            "submitted_pitches": len(submitted_pitches),
            "submitted_content": len(submitted_content),
            "approved_content": len(approved_content),
            "publication": analytics,
        }

    def list_pitches(self, status: str = "submitted", limit: int = 100) -> dict[str, Any]:
        return self.editor.list_pitches(status=status, limit=limit)

    def list_content(self, status: str = "submitted", limit: int = 100) -> dict[str, Any]:
        return self.editor.list_content(status=status, limit=limit)

    def review_queue(
        self,
        *,
        pitch_status: str = "submitted",
        content_status: str = "submitted",
        limit: int = 100,
    ) -> dict[str, Any]:
        return self.editor.review_queue(
            pitch_status=pitch_status,
            content_status=content_status,
            limit=limit,
        )

    def approve_pitch(self, story_pitch_id: int, reviewer_id: int | None) -> dict[str, Any]:
        return self.editor.approve_pitch(story_pitch_id, reviewer_id)

    def reject_pitch(self, story_pitch_id: int, remarks: str = "") -> dict[str, Any]:
        return self.editor.reject_pitch(story_pitch_id, remarks=remarks)

    def approve_content(self, content_id: int) -> dict[str, Any]:
        return self.editor.approve_content(content_id)

    def reject_content(self, content_id: int, remarks: str = "") -> dict[str, Any]:
        return self.editor.reject_content(content_id, remarks=remarks)

    def assign_content(
        self,
        content_id: int,
        assignee_user_id: int,
        note: str = "",
        *,
        due_at=None,
        assigner_user_id: int | None = None,
    ) -> dict[str, Any]:
        return self.editor.assign_content(
            content_id,
            assignee_user_id,
            note=note,
            due_at=due_at,
            assigner_user_id=assigner_user_id,
        )

    def assign_pitch(
        self,
        story_pitch_id: int,
        assignee_user_id: int,
        *,
        assigner_user_id: int | None = None,
        note: str = "",
        due_at=None,
        auto_approve: bool = True,
    ) -> dict[str, Any]:
        return self.editor.assign_pitch(
            story_pitch_id,
            assignee_user_id,
            assigner_user_id=assigner_user_id,
            note=note,
            due_at=due_at,
            auto_approve=auto_approve,
        )

    def bottlenecks(self) -> dict[str, Any]:
        """Where work is piling up across the newsroom pipeline."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT status AS stage,
                       COUNT(*) AS item_count,
                       ROUND(AVG(EXTRACT(EPOCH FROM (NOW() - updated_at)) / 3600.0)::numeric, 2)
                         AS avg_hours_in_stage
                FROM content
                WHERE status NOT IN ('published', 'draft')
                GROUP BY status
                ORDER BY item_count DESC
                """
            )
            content_stages = [dict(r) for r in cur.fetchall() or []]

            cur.execute(
                """
                SELECT status AS stage,
                       COUNT(*) AS item_count
                FROM story_pitch
                GROUP BY status
                ORDER BY item_count DESC
                """
            )
            pitch_stages = [dict(r) for r in cur.fetchall() or []]

            cur.execute(
                """
                SELECT status AS stage,
                       COUNT(*) AS item_count
                FROM publication
                GROUP BY status
                ORDER BY item_count DESC
                """
            )
            publication_stages = [dict(r) for r in cur.fetchall() or []]

            try:
                cur.execute(
                    """
                    SELECT status AS stage,
                           COUNT(*) AS item_count
                    FROM adaptation_drafts
                    GROUP BY status
                    ORDER BY item_count DESC
                    """
                )
                adaptation_stages = [dict(r) for r in cur.fetchall() or []]
            except Exception:  # noqa: BLE001 — table may be missing in older DBs
                adaptation_stages = []

        hotspots = []
        for row in content_stages:
            if str(row.get("stage")) in {"submitted", "rejected"} and int(row.get("item_count") or 0) > 0:
                hotspots.append(
                    {
                        "area": "content",
                        "stage": row["stage"],
                        "item_count": int(row["item_count"]),
                        "avg_hours_in_stage": float(row.get("avg_hours_in_stage") or 0),
                        "note": "Editorial backlog — prioritize with /manager/queue",
                    }
                )
        for row in pitch_stages:
            if str(row.get("stage")) == "submitted" and int(row.get("item_count") or 0) > 0:
                hotspots.append(
                    {
                        "area": "story_pitch",
                        "stage": row["stage"],
                        "item_count": int(row["item_count"]),
                        "note": "Pitch review backlog",
                    }
                )

        return {
            "content_stages": content_stages,
            "pitch_stages": pitch_stages,
            "publication_stages": publication_stages,
            "adaptation_stages": adaptation_stages,
            "hotspots": hotspots,
        }

    def business_analytics(self) -> dict[str, Any]:
        """Whole-application business snapshot for the newsroom manager."""
        with db_cursor() as cur:
            cur.execute("SELECT status, COUNT(*) AS count FROM content GROUP BY status")
            content_by_status = {str(r["status"]): int(r["count"]) for r in cur.fetchall() or []}

            cur.execute("SELECT content_kind, COUNT(*) AS count FROM content GROUP BY content_kind")
            content_by_kind = {str(r["content_kind"]): int(r["count"]) for r in cur.fetchall() or []}

            cur.execute("SELECT status, COUNT(*) AS count FROM story_pitch GROUP BY status")
            pitches_by_status = {str(r["status"]): int(r["count"]) for r in cur.fetchall() or []}

            cur.execute("SELECT priority, COUNT(*) AS count FROM story_pitch GROUP BY priority")
            pitches_by_priority = {str(r["priority"]): int(r["count"]) for r in cur.fetchall() or []}

            cur.execute(
                """
                SELECT cleaning_status, COUNT(*) AS count
                FROM raw_ingest
                GROUP BY cleaning_status
                """
            )
            ingest_by_status = {str(r["cleaning_status"]): int(r["count"]) for r in cur.fetchall() or []}

            cur.execute("SELECT COUNT(*) AS count FROM users WHERE account_status = 'active'")
            active_users = int(cur.fetchone()["count"])

            cur.execute(
                """
                SELECT r.role_code, COUNT(u.user_id) AS count
                FROM role r
                LEFT JOIN users u ON u.role_id = r.role_id AND u.account_status = 'active'
                GROUP BY r.role_code
                ORDER BY r.role_code
                """
            )
            users_by_role = {str(r["role_code"]): int(r["count"]) for r in cur.fetchall() or []}

            cur.execute("SELECT COUNT(*) AS count FROM evidence")
            evidence_count = int(cur.fetchone()["count"])

            cur.execute("SELECT COUNT(*) AS count FROM ingest_file")
            ingest_files = int(cur.fetchone()["count"])

        publication = self.publications.analytics()
        bottlenecks = self.bottlenecks()
        workload = self.workload()
        deadline_risk = self.deadline_risk()
        resources = self.resources()

        return {
            "pipeline": {
                "raw_ingest": ingest_by_status,
                "content": content_by_status,
                "content_kinds": content_by_kind,
                "story_pitches": pitches_by_status,
                "pitch_priority": pitches_by_priority,
                "publication": publication,
            },
            "ops": {
                "active_users": active_users,
                "users_by_role": users_by_role,
                "evidence_items": evidence_count,
                "ingest_files": ingest_files,
            },
            "bottleneck_hotspots": bottlenecks.get("hotspots") or [],
            "workload_summary": {
                "journalist_count": len(workload.get("journalists") or []),
                "total_open_items": workload.get("total_open_items"),
            },
            "deadline_risk_summary": {
                "at_risk_count": deadline_risk.get("at_risk_count"),
                "thresholds_hours": deadline_risk.get("thresholds_hours"),
            },
            "resource_summary": resources.get("utilization"),
            "totals": {
                "content": sum(content_by_status.values()),
                "story_pitches": sum(pitches_by_status.values()),
                "publications": sum((publication.get("publications_by_status") or {}).values()),
            },
        }

    def workload(self) -> dict[str, Any]:
        """Per-journalist open workload + availability."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT j.journalist_id, j.user_id, u.username,
                       COALESCE(NULLIF(TRIM(e.first_name || ' ' || e.last_name), ''), u.username)
                         AS full_name,
                       j.primary_specialization, j.secondary_specialization,
                       j.availability_status,
                       COUNT(c.content_id) FILTER (
                         WHERE c.status IN ('draft', 'submitted', 'rework')
                       ) AS open_items,
                       COUNT(c.content_id) FILTER (WHERE c.status = 'rework') AS rework_items,
                       COUNT(c.content_id) FILTER (WHERE c.status = 'submitted') AS submitted_items
                FROM journalist j
                JOIN users u ON u.user_id = j.user_id
                JOIN role r ON r.role_id = u.role_id
                LEFT JOIN employee e ON e.employee_id = u.employee_id
                LEFT JOIN content c ON c.author_id = j.journalist_id
                WHERE j.status = 'active'
                  AND r.role_code = 'journalist'
                GROUP BY j.journalist_id, j.user_id, u.username, e.first_name, e.last_name,
                         j.primary_specialization, j.secondary_specialization, j.availability_status
                ORDER BY open_items DESC, j.journalist_id
                """
            )
            journalists = [dict(r) for r in cur.fetchall() or []]
        total_open = sum(int(j.get("open_items") or 0) for j in journalists)
        return {
            "journalists": journalists,
            "total_open_items": total_open,
            "method": "open content in draft/submitted/rework by author_id",
        }

    def deadline_risk(self, *, submitted_hours: float = 48.0, rework_hours: float = 24.0) -> dict[str, Any]:
        """Items stuck too long in stage (proxy for deadline risk)."""
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT content_id, title, status, author_id,
                       ROUND(EXTRACT(EPOCH FROM (NOW() - COALESCE(submitted_at, updated_at))) / 3600.0)
                         AS hours_in_stage
                FROM content
                WHERE status IN ('submitted', 'rework')
                  AND EXTRACT(EPOCH FROM (NOW() - COALESCE(submitted_at, updated_at))) / 3600.0
                      >= CASE WHEN status = 'rework' THEN %s ELSE %s END
                ORDER BY hours_in_stage DESC
                LIMIT 200
                """,
                (rework_hours, submitted_hours),
            )
            content_risk = [dict(r) for r in cur.fetchall() or []]

            cur.execute(
                """
                SELECT story_pitch_id, title, status, priority, source_type,
                       ROUND(EXTRACT(EPOCH FROM (NOW() - COALESCE(submitted_at, created_at))) / 3600.0)
                         AS hours_in_stage
                FROM story_pitch
                WHERE status = 'submitted'
                  AND EXTRACT(EPOCH FROM (NOW() - COALESCE(submitted_at, created_at))) / 3600.0
                      >= %s
                ORDER BY hours_in_stage DESC
                LIMIT 200
                """,
                (submitted_hours,),
            )
            pitch_risk = [dict(r) for r in cur.fetchall() or []]

        return {
            "thresholds_hours": {
                "submitted": submitted_hours,
                "rework": rework_hours,
            },
            "content_at_risk": content_risk,
            "pitches_at_risk": pitch_risk,
            "at_risk_count": len(content_risk) + len(pitch_risk),
            "method": "age in stage vs thresholds (no due_at column)",
        }

    def resources(self) -> dict[str, Any]:
        """Resource utilization across desks + journalist load distribution."""
        workload = self.workload()
        journalists = workload.get("journalists") or []
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT r.role_code, r.role_name, COUNT(u.user_id) AS active_users
                FROM role r
                LEFT JOIN users u ON u.role_id = r.role_id AND u.account_status = 'active'
                GROUP BY r.role_code, r.role_name
                ORDER BY r.role_code
                """
            )
            desks = [dict(r) for r in cur.fetchall() or []]

        loads = [int(j.get("open_items") or 0) for j in journalists]
        available = sum(
            1 for j in journalists if str(j.get("availability_status") or "") == "available"
        )
        avg_load = round(sum(loads) / len(loads), 2) if loads else 0.0
        overloaded = [j for j in journalists if int(j.get("open_items") or 0) >= max(3, avg_load + 2)]
        underutilized = [
            j
            for j in journalists
            if str(j.get("availability_status") or "") == "available"
            and int(j.get("open_items") or 0) == 0
        ]

        return {
            "desks": desks,
            "utilization": {
                "active_journalists": len(journalists),
                "available_journalists": available,
                "avg_open_load": avg_load,
                "overloaded_count": len(overloaded),
                "underutilized_count": len(underutilized),
            },
            "overloaded": overloaded[:20],
            "underutilized": underutilized[:20],
            "method": "role headcount + journalist open-load distribution",
        }

