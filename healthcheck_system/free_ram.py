import logging
import resource
from pathlib import Path

import humanize

from healthcheck import config
from healthcheck.check import Check
from healthcheck.report import (
    PassReport,
    Report,
    SoftwareErrorReport,
    SoftwareWarningReport,
)

from ._gettext import _
from .utils import parse_bytes

logger = logging.getLogger(__name__)


class FreeRam(Check):
    """Watches amount of free ram."""

    DEFAULT = {
        "warning_level": "160MB",
        "error_level": "80MB",
    }

    def _run(self, data, param):
        freemem = self.meminfo()["MemAvailable"]
        if freemem <= self._level_config("error_level"):
            return FreeRamError(freemem)
        if freemem <= self._level_config("warning_level"):
            return FreeRamWarning(freemem)
        return FreeRamPass(freemem)

    @staticmethod
    def name():
        return "free-ram"

    @staticmethod
    def description():
        return _("watches amount of free ram and reports not enough space.")

    def _level_config(self, confname) -> int:
        try:
            return parse_bytes(self.config[confname].value)
        except ValueError as exc:
            logger.warning(
                "Invalid configuration option value: %s=%s: %s",
                self.config[confname].path(True),
                self.config[confname].value,
                exc.args[0],
            )
            return parse_bytes(self.DEFAULT[confname])

    @classmethod
    def config_options(cls):
        return super().config_options() + (
            config.ConfigOption(
                name="error_level",
                description=_(
                    "Amount of memory or less that triggers error. The format is number and unit (such as '80MB')"
                ),
                default=cls.DEFAULT["error_level"],
            ),
            config.ConfigOption(
                name="warning_level",
                description=_(
                    "Amount of memory or less that triggers warning. The format is number and unit (such as '160MB')"
                ),
                default=cls.DEFAULT["warning_level"],
            ),
        )

    @staticmethod
    def meminfo():
        "Load data from /proc/meminfo and returns dict"
        data = {}
        with open("/proc/meminfo", "r") as file:
            for line in file:
                splitted = [x.strip() for x in line.split(" ") if x]
                splitted[0] = splitted[0][:-1]  # remove ':'
                if len(splitted) == 3:
                    data[splitted[0]] = parse_bytes(splitted[1], unit=splitted[2])
                else:
                    data[splitted[0]] = int(splitted[1])
        return data


class FreeRamReport(Report):
    """Common class for all freeram report classes."""

    def __init__(self, freemem):
        self.freemem = freemem
        self.consumption = sorted(
            filter(None, (self._proc_info(proc) for proc in Path("/proc").glob("[0-9]*"))),
            key=lambda proc: proc["mem"],
            reverse=True,
        )

    @staticmethod
    def _proc_info(pid_path):
        res = {"pid": int(pid_path.name)}
        try:
            with (pid_path / "statm").open() as file:
                res["mem"] = int(file.readline().split()[1]) * resource.getpagesize()
            with (pid_path / "comm").open() as file:
                res["comm"] = file.read().strip()
            with (pid_path / "cmdline").open("rb") as file:
                res["cmdline"] = b" ".join(file.read().split(b"\x00")[:-1]).decode()
            return res
        except FileNotFoundError:  # The process can disappear at any point so we just ignore such process
            return None

    def details(self):
        return (
            _("Amount of free memory: ")
            + humanize.naturalsize(self.freemem)
            + "\n"
            + _("Processes consuming the most memory:")
            + "\n"
            + "\n".join(
                f"  {humanize.naturalsize(proc['mem'])}: {proc['comm']}[{proc['pid']}]: {proc['cmdline']}"
                for proc in self.consumption
                if proc["mem"] >= self.consumption[0]["mem"] / 2
            )
        )


class FreeRamPass(FreeRamReport, PassReport):
    """Report: There is enough memory in system."""

    def summary(self):
        return _("System seems to have enough free memory.")


class FreeRamWarning(FreeRamReport, SoftwareWarningReport):
    """Report: The amount of free memory in system is getting short."""

    def summary(self):
        return _("System seems to have not enough free memory.")

    def suggestion(self):
        return _("You might want to check what processes are running on your router and how much memory they consume.")


class FreeRamError(FreeRamReport, SoftwareErrorReport):
    """Report: The amount of free memory in system is getting dangerously short."""

    def summary(self):
        return _("System experiences memory shortage.")

    def suggestion(self):
        return _("You might want to check what processes are running on your router and how much memory they consume.")
