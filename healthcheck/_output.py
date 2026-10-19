"""Output formatters."""

import abc
import datetime
import itertools
import json
import logging
import subprocess
import sys

import crontab
import rich.console
import rich.markup
import rich.theme

from . import config
from . import report as _report
from . import storage
from ._gettext import _

logger = logging.getLogger(__name__)


class OutputFormatter(abc.ABC):
    """Generic definition of formatter."""

    def __init__(self):
        self.level = 50

    def __enter__(self):
        return self.report

    def __exit__(self, exc_type, exc_value, traceback):
        self.finish()

    @abc.abstractmethod
    def report(self, plugin_name, check_name, report):
        """Output given report."""

    @abc.abstractmethod
    def finish(self):
        """Finish outputing reports. No subsequent reports can be added after calling this. Output might not be
        generated unless this is called.
        """


class ConsoleFormatter(OutputFormatter):  # pylint: disable=too-many-instance-attributes
    """Output to console in text possibly with colors."""

    def __init__(self):
        super().__init__()
        self.console_theme = rich.theme.Theme(
            {
                "heading": "blue",
                "pass": "green",
                "other": "bright_black",
                "advice": "bright_cyan",
                "warning": "bright_yellow",
                "error": "red",
                "fatal_error": "bright_red",
            }
        )
        self.console = rich.console.Console(theme=self.console_theme)
        self.passes = 0
        self.advices = 0
        self.warnings = 0
        self.errors = 0
        self.fatal_errors = 0
        self.others = 0

    def report(self, plugin_name, check_name, report):
        check = f"{plugin_name}:{check_name}"
        self.console.rule(f"[heading]{check}", characters="=", style="heading")
        if isinstance(report, _report.MultiReport):
            for key, subreport in report.items():
                self.console.print(f"{key}: ", style="heading", end="")
                self._report(subreport)
        else:
            self._report(report)

    def _report(self, report):
        style = ""
        if isinstance(report, _report.PassReport):
            style = "pass"
            self.passes += 1
        elif report.level < _report.LEVEL_ADVICE:
            style = "other"
            self.others += 1
        elif _report.LEVEL_ADVICE <= report.level < _report.LEVEL_WARNING:
            style = "advice"
            self.advices += 1
        elif _report.LEVEL_WARNING <= report.level < _report.LEVEL_ERROR:
            style = "warning"
            self.warnings += 1
        elif _report.LEVEL_ERROR <= report.level < _report.LEVEL_FATAL_ERROR:
            style = "error"
            self.errors += 1
        elif _report.LEVEL_FATAL_ERROR <= report.level:
            style = "fatal_error"
            self.fatal_errors += 1
        self.console.print(report, style=style, markup=False, highlight=False)
        self.console.print(report.details(), markup=False)
        suggestion = report.suggestion()
        if suggestion is not None:
            self.console.print(suggestion, markup=False)

    def finish(self):
        self.console.rule()
        report = [f"[pass]{_('Passes')}: {self.passes}[/pass]"]
        if self.fatal_errors > 0:
            report.append(f"[fatal_error]{_('Fatal Errors')}: {self.fatal_errors}[/fatal_error]")
        if self.errors > 0:
            report.append(f"[error]{_('Errors')}: {self.errors}[/error]")
        if self.warnings > 0:
            report.append(f"[warning]{_('Warnings')}: {self.warnings}[/warning]")
        if self.advices > 0:
            report.append(f"[advice]{_('Advices')}: {self.advices}[/advice]")
        if self.others > 0:
            report.append(f"[other]{_('Others')}: {self.others}[/other]")
        self.console.print("  ".join(report))


class JSONFormatter(OutputFormatter):
    """Output in JSON."""

    def __init__(self):
        super().__init__()
        self.data = {}

    @staticmethod
    def __representation(report):
        data = {
            "result": report.level_name(),
            "summary": report.summary(),
            "details": report.details(),
        }
        if report.suggestion() is not None:
            data["suggestion"] = report.suggestion()
        return data

    def report(self, plugin_name, check_name, report):
        self.data[f"{plugin_name}:{check_name}"] = self.__representation(report)

    def finish(self):
        if sys.stdout.isatty():
            rich.console.Console().print_json(data=self.data)
        else:  # We explicitly print here just json dump as it provides more compat output
            print(json.dumps(self.data))


class NotificationFormatter(OutputFormatter, config.Configurable):
    """Output to notification system."""

    DEFAULT_LEVEL = 40
    DEFAULT_HARDWARE_LEVEL = 40
    DEFAULT_SOFTWARE_LEVEL = 40
    DEFAULT_PERIOD = "0 1 * * *"

    def __init__(self, euci: config.EUci):
        super().__init__()
        config.Configurable.__init__(self, euci)
        self.reports: dict[str, _report.Report] = {}
        self.silent_reports: dict[str, _report.Report] = {}
        self.ignore_reports: dict[str, _report.Report] = {}
        self.level = self.config["level"].value
        self.hardware_level = max(self.level, self.config["hardware_level"].value)
        self.software_level = max(self.level, self.config["software_level"].value)
        try:
            self.period = crontab.CronTab(self.config["period"].value)
        except ValueError as exc:
            logger.error(
                "UCI option '%s' does not have correct format: %s", self.config["period"].path(join=True), exc.args[0]
            )
            self.period = crontab.CronTab(self.DEFAULT_PERIOD)

    def report(self, plugin_name, check_name, report):
        level = (
            self.hardware_level
            if isinstance(report, _report.HardwareReport)
            else self.software_level if isinstance(report, _report.SoftwareReport) else self.level
        )

        def add(attr, report):
            identifier = f"{plugin_name}:{check_name}{'|' + str(attr) if attr is not None else ''}"
            if isinstance(report, (_report.InconclusiveReport, _report.TryAgainLater)):
                self.ignore_reports[identifier] = report
            elif report.level >= level:
                self.reports[identifier] = report
            else:
                self.silent_reports[identifier] = report

        if isinstance(report, _report.MultiReport):
            for attr, subreport in report.items():
                add(attr, subreport)
        else:
            add(None, report)

    def finish(self):  # pylint: disable=too-many-branches
        worst = []
        better = []
        nochange = []
        with storage.PermanentStorage("notifications") as store:
            if "reports" not in store:
                store["reports"] = {}
            for identifier, report in self.reports.items():
                if identifier in store["reports"]:
                    if store["reports"][identifier]["level"] > report.level:
                        better.append(self._report2str(identifier, report))
                    elif store["reports"][identifier]["level"] < report.level:
                        worst.append(self._report2str(identifier, report))
                    else:
                        nochange.append(self._report2str(identifier, report))
                else:
                    worst.append(self._report2str(identifier, report))
            for identifier in store["reports"].keys():
                if identifier in self.ignore_reports:
                    nochange.append(self._report2str(identifier, self.ignore_reports[identifier]))
                elif identifier not in self.reports:
                    if identifier in self.silent_reports:
                        better.append(self._report2str(identifier, self.silent_reports[identifier]))

            for identifier, report in self.reports.items():
                store["reports"][identifier] = {
                    "level": report.level,
                }
            for identifier in set(store["reports"].keys()) - set(
                itertools.chain(self.reports.keys(), self.ignore_reports.keys())
            ):
                del store["reports"][identifier]

            now = datetime.datetime.now().timestamp()
            last_notification = float(store.get("last_notification", default=now))
            if (
                not worst
                and not better
                and (not nochange or last_notification > (now + self.period.previous(default_utc=False)))
            ):
                return
            store["last_notification"] = now

        message = []
        if worst:
            message.append(_("#### Healthcheck detected the following new or deteriorated issues ####"))
            message += worst
        if better:
            message.append(_("#### Healthcheck detected improvement on following issues ####"))
            message += better
        if nochange:
            message.append(_("#### Healthcheck still reports the following issues ####"))
            message += nochange
        assert message, "There has to be some message if we get here"
        subprocess.run(["create_notification", "-s", "error", "\n\n".join(message)], check=True)
        subprocess.run(["notifier"], check=False)

    @staticmethod
    def _report2str(identifier, report):
        suggestion = report.suggestion()
        idsplit = identifier.split("|", maxsplit=1)
        attr = f"## {idsplit[1]} " if len(idsplit) > 1 else ""
        return f"{attr}## {report.summary()}\n" + report.details() + (suggestion if suggestion else "")

    @classmethod
    def config_type(cls):
        return "notify"

    @classmethod
    def config_name(cls):
        return "notify"

    @classmethod
    def config_options(cls):
        return (
            config.ConfigOption(
                name="enable",
                description=_("Can be used to disable notifications."),
                type=bool,
                default=True,
            ),
            config.ConfigOption(
                name="level",
                description=_(
                    "Minimal priority for notification to be generated. This is number from 0 to 100 where higher "
                    + "means more significant. In default this is set to: "
                )
                + str(cls.DEFAULT_LEVEL),
                type=int,
                default=cls.DEFAULT_LEVEL,
            ),
            config.ConfigOption(
                name="hardware_level",
                description=_(
                    "Minimal priority for hardware related notifications to be generated. This is number as well "
                    + "as for level. In default this is set to: "
                )
                + str(cls.DEFAULT_HARDWARE_LEVEL),
                type=int,
                default=cls.DEFAULT_HARDWARE_LEVEL,
            ),
            config.ConfigOption(
                name="software_level",
                description=_(
                    "Minimal priority for software related notifications to be generated. This is number as well "
                    + "as for level. In default this is set to: "
                )
                + str(cls.DEFAULT_SOFTWARE_LEVEL),
                type=int,
                default=cls.DEFAULT_SOFTWARE_LEVEL,
            ),
            config.ConfigOption(
                name="period",
                description=_(
                    "Notification period specified in cron format. This specifies how often and when should "
                    "notification about persistent issues be send. In deafult it is set to: "
                )
                + cls.DEFAULT_PERIOD,
                default=cls.DEFAULT_PERIOD,
            ),
        )
