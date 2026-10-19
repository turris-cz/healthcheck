"""Healthcheck setup checks."""

from euci import EUci

from healthcheck.plugin import Plugin

from ._gettext import _
from .email_notifications import EmailNotifications


class SetupPlugin(Plugin):
    """Healthcheck plugin for setup suggestions."""

    def __init__(self, euci: EUci):
        super().__init__(euci, (EmailNotifications,))

    @classmethod
    def name(cls):
        return "setup"

    @classmethod
    def description(cls):
        return _("Suggestion for router setup.")
