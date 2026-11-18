"""Domain services.

Root (pipeline / shared):
  ingestion, persistence, permission, report, access

Grouped (like entities/content):
  services/content/   content CRUD
  services/user/      user CRUD
"""

from services.content import ContentService
from services.ingestion_service import IngestionService
from services.permission_service import has_capability
from services.persistence_service import PersistenceService
from services.report_service import ReportService
from services.user import UserService

__all__ = [
    "ContentService",
    "IngestionService",
    "PersistenceService",
    "ReportService",
    "UserService",
    "has_capability",
]
