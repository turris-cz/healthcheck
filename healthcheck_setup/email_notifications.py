from euci import EUci

from healthcheck.check import Check
from healthcheck.report import PassReport, SoftwareAdviseReport

from ._gettext import _


class EmailNotifications(Check):
    """Suggest email notification if they are not configured."""

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
        return _("Checks if email notifications are configured.")


class ConfigureEmailNotifications(SoftwareAdviseReport):
    """Suggest user to enable email notification."""

    def summary(self):
        return _("You should configure email for notifications to be notified about router events")

    def details(self):
        return _(
            "Turris system contains notification system. Various components, including healthcheck, are using it "
            "to inform administrator about possible issues."
        )

    def suggestion(self):
        return _('Go to the "Maintenance" setting in Foris and set up e-mail notifications there.')


class EmailNotificationsPass(PassReport):
    """Email notifications seems to be configured."""

    def __init__(self, mails):
        self._mails = mails

    def summary(self):
        return _("Email notifications seems to be configured.")

    def details(self):
        return _("Notifications are send to the following mail addresses: ") + ", ".join(self._mails)
