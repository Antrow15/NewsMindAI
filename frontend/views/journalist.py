"""Back-compat shim — prefer journalist_dashboard / create / library."""

from __future__ import annotations

from views.journalist_dashboard import render as render_dashboard
from views.journalist_create import render as render_create
from views.journalist_library import render as render_library


def render() -> None:
    render_dashboard()
