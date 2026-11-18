"""Feature modules — same idea as entities: packages + content group.

modules/
  authentication/   login / session
  admin/            ingest → clean → persist
  content/          desk content operations
"""

from modules import admin, authentication, content

__all__ = ["admin", "authentication", "content"]
