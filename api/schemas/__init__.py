"""Pydantic request/response models for FastAPI routers.

Schemas are **not** business logic. They define:
  - what JSON a client may send (request models)
  - what JSON the API returns (response models)
  - field validation (types, min length, allowed status values via `rules.py`)

Routers import schemas for `response_model=` and body parameters.
Domain work stays in `services/` / `modules/` / `ml/`.
"""
