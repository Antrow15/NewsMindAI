"""DAO layer — one DAO per ERD table in scope."""

from dao.adaptation_dao import AdaptationDAO
from dao.article_dao import ArticleDAO
from dao.audience_insight_analyst_dao import AudienceInsightAnalystDAO
from dao.base_dao import BaseDAO
from dao.category_dao import CategoryDAO
from dao.cleaning_report_dao import CleaningReportDAO
from dao.content_adaptation_editor_dao import ContentAdaptationEditorDAO
from dao.content_dao import ContentDAO
from dao.editor_dao import EditorDAO
from dao.employee_dao import EmployeeDAO
from dao.evidence_dao import EvidenceDAO
from dao.ingest_file_dao import IngestFileDAO
from dao.journalist_dao import JournalistDAO
from dao.news_dao import NewsDAO
from dao.newsroom_manager_dao import NewsroomManagerDAO
from dao.publication_dao import PublicationDAO
from dao.publisher_dao import PublisherDAO
from dao.raw_ingest_dao import RawIngestDAO
from dao.role_dao import RoleDAO
from dao.story_pitch_dao import StoryPitchDAO
from dao.user_dao import UserDAO

__all__ = [
    "AdaptationDAO",
    "ArticleDAO",
    "AudienceInsightAnalystDAO",
    "BaseDAO",
    "CategoryDAO",
    "CleaningReportDAO",
    "ContentAdaptationEditorDAO",
    "ContentDAO",
    "EditorDAO",
    "EmployeeDAO",
    "EvidenceDAO",
    "IngestFileDAO",
    "JournalistDAO",
    "NewsDAO",
    "NewsroomManagerDAO",
    "PublicationDAO",
    "PublisherDAO",
    "RawIngestDAO",
    "RoleDAO",
    "StoryPitchDAO",
    "UserDAO",
]
