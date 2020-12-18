import re
import shutil
import subprocess
import typing
from pathlib import Path

from healthcheck.check import Check
from healthcheck.report import (
    HardwareErrorReport,
    HardwareFatalErrorReport,
    HardwareWarningReport,
    InconclusiveReport,
    MultiReport,
    NotApplicableReport,
    PassReport,
    Report,
)

from ._gettext import _


def _int(value: str) -> int:
    if value.startswith("0x"):
        return int(value[2:])
    return int(value)


class MMCLife(Check):
    """Watches life and end-of-life estimations of eMMC."""

    DEVICE_LIFE_A = "EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_A"
    DEVICE_LIFE_B = "EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_B"
    DEVICE_EOL = "EXT_CSD_PRE_EOL_INFO"
    OUT_PARSE = re.compile(r"\[(.*)\]: (.*)")

    def _parameters(self, data):
        # This relies only on naming schema of Linux devices but that should be enough in most cases.
        return tuple(dev for dev in Path("/dev").glob("mmcblk[0-9]") if dev.is_block_device())

    def _run(self, data, param):
        if param is None:
            return NoMMCDeviceReport()
        if shutil.which("mmc") is None:
            return UnableToGetCSDReport()

        info = self.mmc_extcsd(param)
        if isinstance(info, str) or set(info.keys()).issubset(
            (self.DEVICE_LIFE_A, self.DEVICE_LIFE_B, self.DEVICE_EOL)
        ):
            return UnableToGetCSDReport(info)
        device_life = max(_int(info[self.DEVICE_LIFE_A]), _int(info[self.DEVICE_LIFE_B]))
        device_eol = _int(info[self.DEVICE_EOL])
        if device_eol > 2 or device_life > 10:
            # All reserved blocks are depleted or memory has exceeded its life
            return MMCLifeFatalError(device_eol, device_life)
        if device_eol > 1 or device_life > 9:
            # 80% reserved blocks were used and 90% of its life
            return MMCLifeError(device_eol, device_life)
        if device_life > 7:
            # at least 70% of device life
            return MMCLifeWarning(device_eol, device_life)
        return MMCLifeOk(device_eol, device_life)

    @staticmethod
    def name():
        return "mmc-life"

    @staticmethod
    def description():
        return _("Watches wear of MMC storages plugged in to the router.")

    @classmethod
    def mmc_extcsd(cls, dev: str) -> typing.Union[str, dict]:
        """Loads EXTCSD from provided mmc device and returns dict."""
        data = {}
        out = subprocess.run(["mmc", "extcsd", "read", dev], capture_output=True, check=True)
        for line in out.stdout.decode(errors="ignore").splitlines():
            match = cls.OUT_PARSE.search(line)
            if match:
                data[match.group(1)] = match.group(2)
        return data


class NoMMCDeviceReport(NotApplicableReport):
    """There is no MMC device so there is nothing to check."""

    def summary(self):
        return _("There is no MMC device detected in system.")

    def details(self):
        return _(
            "Check found no MMC block device in system. This is most likely because there is just no such device "
            "plugged in."
        )


class UnableToGetCSDReport(InconclusiveReport):
    """It is possible that either MMC does not support extcsd or that mmc-tools are not installed."""

    def __init__(self, info=None):
        # Error message is either string in case of failed mmc read or None in case of missing mmc-utils or dictionary
        # in rare case device does not provide required info.
        self.info = info

    def summary(self):
        return _("It is not possible to read extcsd data.")

    def details(self):
        if self.info is None:
            return _("MMC tools (mmc-utils) are missing or not accessible.")
        if isinstance(self.info, str):
            return _("Read failed with error: ") + self.info
        return _("MMC does not provide information about its lifespan.")

    def suggestion(self):
        if self.info is None:
            return _("You should install mmc-utils or any other package that provides mmc-utils's command 'mmc'.")
        return super().suggestion()


class _MMCLifeReport(Report):
    """Generic report about MMC life."""

    def __init__(self, eol, life):
        self.device_eol = eol
        self.device_life = life

    def details(self):
        res = []
        if self.device_eol > 2:
            res.append(_("Reserved blocks on memory were depleted!"))
        elif self.device_eol > 1:
            res.append(_("More than 80% of reserved blocks consumed!"))
        res.append(_("Device's lifespan is depleted at least: ") + str((self.device_life - 1) * 10) + "%")
        return _(
            "MMC storage has limited amount of writes and because of that it has limited lifespan. This means "
            "that it is normal and expected that reserved blocks are going to be low if your device is years old. "
            "In case of new device it can be either faulty from factory or more likely it was used very heavily in "
            "the past. Note that the manufacturers do not provide warranty if MMC was used heavily.\n"
        ) + "\n".join(res)

    def suggestion(self):
        return _(
            "To prolong device lifespan you should minimize amount of writes (preferably to only system updates). "
            "This means moving any write heavy tasks such as file sharing, databases, containers, logs and others "
            "to some other storage device."
        )


class MMCLifeOk(_MMCLifeReport, PassReport):
    """MMC health is OK."""

    def summary(self):
        return _("Life of MMC is all right.")


class MMCLifeWarning(_MMCLifeReport, HardwareWarningReport):
    """MMC health is nearing its end of life."""

    def summary(self):
        return _("Life of MMC is getting short.")


class MMCLifeError(_MMCLifeReport, HardwareErrorReport):
    """MMC health is nearing its end of life."""

    def summary(self):
        return _("Life of MMC is getting dangerously short!")


class MMCLifeFatalError(_MMCLifeReport, HardwareFatalErrorReport):
    """MMC life has exceeded its lifespan."""

    def summary(self):
        return _("MMC is end of life.")

    def suggestion(self):
        return _(
            "There is nothing that can be done now. It is too late. MMC is most probably already not usable. "
            "You should stop using it if your data are dear to you. It should be replaced if possible. Either "
            "with same type of device or with different in case it is MMC soldered to board in device."
        )
