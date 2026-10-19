"""Check of free space on mounted file-systems."""

import os
import typing

import humanize

from healthcheck import config
from healthcheck.check import Check
from healthcheck.report import (
    PassReport,
    Report,
    SoftwareErrorReport,
    SoftwareFatalErrorReport,
    SoftwareWarningReport,
)

from ._gettext import _


class FreeStorage(Check):
    """Watches for amount of free space on all mounted file-systems.

    It is parametrized by mount path.
    """

    IGNORED_FS = {
        "proc",
        "sysfs",
        "securityfs",
        "debugfs",
        "configfs",
        "pstore",
        "efivarfs",
        "cgroup",
        "cgroup2",
        "devtmpfs",
        "mqueue",
        "devpts",
        "binfmt_misc",
    }
    WARNING_PERCENT = 0.1
    ERROR_PERCENT = 0.05
    FATAL_PERCENT = 0.01

    def _collect_data(self):
        res = self.mounts()
        for path, info in res.items():
            info["free_space"], info["total_space"] = self.storage_info(path)
        return res

    def _parameters(self, data):
        ignored = set(self.config["ignore"].value)
        ignored_fs = set(self.IGNORED_FS).union(self.config["ignore_fs"].value)
        return tuple(
            path
            for path, info in data.items()
            if path not in ignored and info["type"] not in ignored_fs and info["total_space"] > 0
        )

    def _run(self, data, param):
        assert param is not None, "There should be at least one mount point (the root filesystem)"
        info = data[param]
        percent = info["free_space"] / info["total_space"] * 100
        report_class = None
        if percent <= self.FATAL_PERCENT:
            report_class = FreeStorageFatalError
        elif percent <= self.ERROR_PERCENT:
            report_class = FreeStorageError
        elif percent <= self.WARNING_PERCENT:
            report_class = FreeStorageWarning
        else:
            report_class = FreeStoragePass
        return report_class(param, info["free_space"], info["total_space"], info["device"], info["type"])

    @staticmethod
    def name():
        return "free-storage"

    @staticmethod
    def description():
        return _("Checks amount of free space on mounted filesystems.")

    @classmethod
    def config_options(cls):
        return super().config_options() + (
            # config.ConfigOption(
            #    name="warnig",
            #    description=_("Warning is raised when amount of empty space drops below this percentage."),
            #    type=float,
            #    default=str(cls.WARNING_PERCENT),
            # ),
            # config.ConfigOption(
            #    name="error",
            #    description=_("Error is raised when amount of empty space drops below this percentage."),
            #    type=float,
            #    default=str(cls.ERROR_PERCENT),
            # ),
            # config.ConfigOption(
            #    name="fatal",
            #    description=_("Fatal error is raised when amount of empty space drops below this percentage."),
            #    type=float,
            #    default=str(cls.ERROR_PERCENT),
            # ),
            config.ConfigOption(
                name="ignore",
                description=_("Specific mount point to be ignored (such as '/home')."),
                list=True,
            ),
            config.ConfigOption(
                name="ignore_fs",
                description=_("File Systems type to be ignored (such as 'sysfs')."),
                list=True,
            ),
        )

    @staticmethod
    def storage_info(path) -> typing.Tuple[int, int]:
        """Returns two values: free space, total space in bytes."""
        stat = os.statvfs(path)
        return stat.f_bavail * stat.f_bsize, stat.f_blocks * stat.f_frsize

    @staticmethod
    def mounts() -> dict:
        """Returns mount points as dict where indexes are mount paths and values are dicts with more info about mount
        point. It contain fields "device" and "type".
        """
        ret = {}
        with open("/proc/mounts", "r", encoding="utf-8") as file:
            for line in file:
                columns = line.split()
                if "rw" not in columns[3].split(","):
                    continue  # only write filesystems are considered
                ret[columns[1]] = {
                    "device": columns[0],
                    "type": columns[2],
                    # Well we are not interested in mount options and rest so they are ignored
                }
        return ret


class _FreeStorageReport(Report):
    """Generic report about free space on mounted storage."""

    def __init__(self, mount, free_space, total_space, device, devtype):
        self.mount = mount
        self.free_space = free_space
        self.total_space = total_space
        self.device = device
        self.devtype = devtype

    def details(self):
        return (
            humanize.naturalsize(self.free_space)
            + _(" out of ")
            + humanize.naturalsize(self.total_space)
            + _(" available on device: ")
            + self.device
        )

    def _used(self):
        used = (1 - (self.free_space / self.total_space)) * 100
        return f"{used:.2f}% " + _("used")

    def suggestion(self):
        msg = _(
            "You should remove any unnecessary files and directories in case they were created by user(s) and not "
            "by system (unless you know what you are doing)."
        )
        if self.mount == "/":
            msg += _(" You can also remove some nonessential software you do not need to free storage space.")
        if self.devtype == "btrfs":
            msg += _(
                " You should also check snapshots and remove unnecessary ones (using schnapps or by any other "
                "way you are using)."
            )
        elif self.devtype == "tmpfs":
            msg += _(
                " In case of this storage it can also be enough to just reboot device as content resides in "
                "volatile memory."
            )
        else:
            msg += _(
                "This applies to permanent storages (hardware storage devices). In case of memory storages "
                "such as 'tmpfs' it might be enough to perform reboot."
            )


class FreeStoragePass(_FreeStorageReport, PassReport):
    """Storage is not getting short."""

    def summary(self):
        return _("There is enough of free storage space") + f" ({self._used()})"

    def suggestion(self):
        return None


class FreeStorageWarning(_FreeStorageReport, SoftwareWarningReport):
    """Warning about not enough free space on file-system."""

    def summary(self):
        return _("Storage space is getting low") + f" ({self._used()})"


class FreeStorageError(_FreeStorageReport, SoftwareErrorReport):
    """Error about not enough free space on file-system."""

    def summary(self):
        return _("Amount of free storage space is getting dangerously low") + f" ({self._used()})"

    def details(self):
        return (
            super().details()
            + "\n"
            + _(
                "Having storage device filled almost to the brim is dangerous as you can easily run out of of storage "
                "space with system updates or when files are updated or new added. Not only that it also considerably "
                "slows down the storage."
            )
        )


class FreeStorageFatalError(_FreeStorageReport, SoftwareFatalErrorReport):
    """Fatal error about not enough free space on file-system."""

    def summary(self):
        return _("Storage is full!") + f" ({self._used()})"

    def details(self):
        return (
            super().details()
            + "\n"
            + _(
                "Storage is pretty much full. It is expected that writing or extending files can fail and "
                "services might start failing as well. You should act now!"
            )
        )
