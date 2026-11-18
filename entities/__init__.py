"""Entities — role desks as top-level files; content under content/."""

from entities.audience_insight_analyst import AudienceInsightAnalyst
from entities.content import Article, Category, Content, Evidence, News, StoryPitch
from entities.content_adaptation_editor import ContentAdaptationEditor
from entities.editor import Editor
from entities.employee import Employee
from entities.journalist import Journalist
from entities.newsroom_manager import NewsroomManager
from entities.publisher import Publisher
from entities.role import Role
from entities.user import User

__all__ = [
    "Article",
    "AudienceInsightAnalyst",
    "Category",
    "Content",
    "ContentAdaptationEditor",
    "Editor",
    "Employee",
    "Evidence",
    "Journalist",
    "News",
    "NewsroomManager",
    "Publisher",
    "Role",
    "StoryPitch",
    "User",
]
