import json
import subprocess
import typing
from pathlib import Path

from healthcheck.check import Check
from healthcheck.report import PassReport, SoftwareAdviseReport, SoftwareWarningReport

from ._gettext import _


class ReenabledServices(Check):
    """Checks if there is any running service that is disabled but would be re-enabled with update."""

    def _run(self, data, param):
        disabled = []
        with open("/etc/services_wanted", "r") as file:
            for service in file:
                if (Path("/etc/init.d") / service).exists():
                    if not next((Path("/etc/rc.d") / service).glob("*[0-9]" + service)):
                        disabled.append(service)
        if disabled:
            return ReenabledServicesReport(disabled)
        return ReenabledServicesPass()

    @staticmethod
    def name():
        return "services-reenabled"

    @staticmethod
    def description():
        return _("Check if there is no disabled service that would be re-enabled with update.")


class ReenabledServicesPass(PassReport):
    """All wanted services are enabled."""

    def summary(self):
        return _("All wanted services are enabled.")

    def details(self):
        return _(
            "Some of the services are automatically activated even if they were previously disabled. "
            "All of such services are enabled and are going to be started on startup."
        )


class ReenabledServicesReport(SoftwareWarningReport):
    """There are wanted services that are disabled."""

    def __init__(self, disabled):
        self.services = disabled

    def summary(self):
        return _("Some services currently disabled are going to be enabled with future updates.")

    def details(self):
        return (
            _("Following disabled services are going to be re-enabled with future updates: ")
            + ", ".join(self.services)
            + "\n"
            + _(
                "These services are automatically enabled even if they were previously disabled to ensure router's "
                "functionality."
            )
        )

    def suggestion(self):
        return _("To solve this you should configure system to not install software you do not want.")


class DisabledServices(Check):
    """Checks if there is any running service that would not be started after boot."""

    DEFAULT_IGNORE = (
        "ubus",  # Ubus actually does not have any init script and is hard dependency of procd (init system)
        "kresd",  # Knot resolver is commonly controller by resolver-conf so we can ignore it
    )

    def _run(self, data, param):
        disabled = []
        for service, value in self.services().items():
            if "instances" not in value:
                continue
            if any(instance["running"] for _, instance in value["instances"].items()):
                if (
                    not next(Path("/etc/rc.d").glob("[KS][0-9][0-9]" + service), False)
                    and service not in self.DEFAULT_IGNORE
                ):
                    disabled.append(service)
        if disabled:
            return DisabledServicesReport(disabled)
        return DisabledServicesPass()

    @staticmethod
    def services() -> typing.Union[str, dict]:
        """Get info about services from ubus."""
        return json.loads(subprocess.run(["ubus", "call", "service", "list"], capture_output=True, check=True).stdout)

    @staticmethod
    def name():
        return "services-disabled"

    @staticmethod
    def description():
        return _("Checks if currently running services would be automatically strated after boot.")


class DisabledServicesPass(PassReport):
    """All running services are enabled."""

    def summary(self):
        return _("All running services are enabled.")

    def details(self):
        return _(
            "Services are not automatically started on next startup unless they are activated. "
            "All currently running services are enabled so you should not miss any service after reboot."
        )


class DisabledServicesReport(SoftwareAdviseReport):
    """There are running services that are disabled."""

    def __init__(self, disabled):
        self.services = disabled

    def summary(self):
        return _("There are currently running services that are not enabled.")

    def details(self):
        return (
            _("Following currently running services are disabled: ")
            + ", ".join(self.services)
            + "\n"
            + _("Enabled services are started on startup. You might want to enable these services.")
        )

    def suggestion(self):
        return _("Using either LuCI or SSH enable mentioned services.")
