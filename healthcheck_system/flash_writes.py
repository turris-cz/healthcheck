import datetime
import itertools
from pathlib import Path

import humanize

from healthcheck.check import Check
from healthcheck.report import (
    HardwareErrorReport,
    HardwareWarningReport,
    NotApplicableReport,
    PassReport,
    Report,
    TryAgainLater,
)

from ._gettext import _


class FlashWrites(Check):
    """Tracks write cycles to MTD devices and reports excessive usage.

    Excessive writing to MTD devices can lead to their short lifespan. Loosing
    storage in device makes it almost unusable.
    """

    # This is max amount of sector writes per hour we consider ok.
    ERROR_RATE = 20000
    WARNING_RATE = 10000
    # It is pretty easy to spike over the rate limit at the beginning. This is safe marging under which we consider it
    # being too early to report warning or even an error. It is amount of sector writes.
    SAFE_LIMIT = 3000

    def _parameters(self, data):
        globs = ("mmcblk[0-9]", "mtdblock[0-9]")
        return tuple(itertools.chain(*[Path("/sys/block").glob(glob) for glob in globs]))

    def _run(self, data, param):
        if param is None:
            return NoFlashDeviceReport()

        uptime = self.uptime()
        writes = self.sector_writes_stat(param)
        rate = writes / uptime * 3600
        if rate >= self.WARNING_RATE and writes <= self.SAFE_LIMIT:
            return FlashWritesTooEarly(writes, uptime)
        if rate >= self.ERROR_RATE:
            return FlashWritesError(writes, uptime)
        if rate >= self.WARNING_RATE:
            return FlashWritesWarning(writes, uptime)
        return FlashWritesOk(writes, uptime)

    @staticmethod
    def name():
        return "flash-writes"

    @staticmethod
    def description():
        return _("Checks if system is not writing too much to flash storage.")

    @staticmethod
    def sector_writes_stat(path: Path):
        """Returns number of written sectors since boot or device initialization."""
        # Reference: https://www.kernel.org/doc/html/latest/block/stat.html
        with (path / "stat").open() as file:
            return int(next(file).split()[6])

    @staticmethod
    def uptime():
        """Returns uptime of device."""
        with open("/proc/uptime", "r") as file:
            return float(next(file).split()[0])


class NoFlashDeviceReport(NotApplicableReport):
    """There are no flash devices we track."""

    def summary(self):
        # TODO
        return _("")

    def details(self):
        # TODO
        return _("")


class _FlashWritesReport(Report):
    """Generic report about MMC writes."""

    def __init__(self, writes, uptime):
        self.device_writes = writes
        self.device_uptime = uptime

    def details(self):
        timedelta = humanize.time.naturaldelta(datetime.timedelta(seconds=self.device_uptime))
        return (
            _(
                "Number of writes on MMC storages is inherently linked to lifespan of it. Compared to some other regular "
                "storages where excessive writes are expected and lifespan still can regularly meet lifespan of the "
                "device, the excessive writes to MMC can shorten lifespan to just a year or two. The that excessive "
                "writes are not regularly covered by warranty."
            )
            + "\n"
            + _("The calculation is since boot up that was {} ago.").format(timedelta)
            + " "
            + _("The amount of recorded sector writes is {}.").format(self.device_writes)
            + " "
            + _("That is {} sector writes per hour.").format(int(self.device_writes / self.device_uptime * 3600))
        )

    def suggestion(self):
        return _(
            "Keep write heavy operations on other storage types, specially if the MMC storage can't be replaced "
            "(such as being soldered on board not inserted in SD slot). These are but not limited to services for file "
            "sharing and caching as well as databases or other data collectors."
        )


class FlashWritesOk(_FlashWritesReport, PassReport):
    """Amount of writes to flash devices is not that high."""

    def summary(self):
        return _("Number of writes to MMC storage does not exceed limits")

    def suggestion(self):
        return None


class FlashWritesTooEarly(_FlashWritesReport, TryAgainLater):
    """Amount of writes to flash devices is high but it is too soon after boot to reliably assess the impact."""

    def summary(self):
        return _("The amount of writes is hight but it is too soon after boot to reliably assess the impact")

    def details(self):
        return (
            _(
                "It is possible that this is just write happenig right after the boot and all will settle down in a while."
            )
            + "\n"
            + super().details()
        )


class FlashWritesWarning(_FlashWritesReport, HardwareWarningReport):
    """Amount of writes is hight."""

    def summary(self):
        return _("The amount of writes is considerably high")


class FlashWritesError(_FlashWritesReport, HardwareErrorReport):
    """Amount of writes is too hight."""

    def summary(self):
        return _("The amount of writes is really high!")

    def suggestion(self):
        return _("You should act now to prevent permanent hardware damage!") + "\n" + super().suggestion()
