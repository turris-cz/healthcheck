from euci import EUci

from healthcheck.check import Check
from healthcheck.report import PassReport, SoftwareAdviseReport

from ._gettext import _


class EmailNotifications(Check):
    """Suggest setting up e-mail notifications if not set up already."""

    def _run(self, data, param):
        with EUci() as uci:
            mails = uci.get("user_notify", "smtp", "to", default=[], list=True)
            if mails:
                return EmailNotificationsPass(mails)
            return ConfigureEmailNotifications()

    @staticmethod
    def name():
        return "email-notifications"

    @staticmethod
    def description():
        return _("Checks if e-mail notifications are set up.")


class ConfigureEmailNotifications(SoftwareAdviseReport):
    """Suggests the user turn on e-mail notifications."""

    def summary(self):
        return _("Set up e-mail notifications to be notified of router events")

    def details(self):
        return _(
            "Turris system has notification system. Various components (including healthcheck) are using it "
            "to inform the administrator of possible issues."
        )

    def suggestion(self):
        return _('Go to the "Maintenance" setting in Foris and set up e-mail notifications there.')


class EmailNotificationsPass(PassReport):
    """E-mail notifications will be sent out."""

    def __init__(self, mails):
        self._mails = mails

    def summary(self):
        return _("E-mail notifications will be sent out.")

    def details(self):
        return _("Notifications are sent to the following e-mail addresses: ") + ", ".join(self._mails)
