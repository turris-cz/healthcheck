"""Translations for Healthcheck core."""

import gettext
import pathlib

_ = gettext.translation("healthcheck", pathlib.Path(__file__).parent / "locale", fallback=True).gettext
