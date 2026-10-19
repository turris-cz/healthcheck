"""Checks of S.M.A.R.T. attributes of ATA/SATA and NVMe drives."""

import json
import shutil
import subprocess
from pathlib import Path

from healthcheck.check import Check
from healthcheck.report import InconclusiveReport, NotApplicableReport

from ._gettext import _

DEFAULT_TEMPERATURE_WARNIG = 45
DEFAULT_TEMPERATURE_ERROR = 60


def smart(dev) -> tuple[int, dict]:
    """Loads S.M.A.R.T. info from provided device device and returns dict."""
    out = subprocess.run(["smartctl", "--attributes", "--json=c", dev], capture_output=True, check=False)
    info = json.loads(out.stdout)
    return out.returncode, info


class SmartATA(Check):
    """Tracks pre-fail attributes in S.M.A.R.T. for ATA/SATA drives."""

    def _parameters(self, data):
        return tuple(Path("/dev").glob("sd[a-z]"))

    def _run(self, data, param):
        if param is None:
            return NoSMARTDeviceReport()
        if shutil.which("smartctl") is None:
            return UnableToGetSMARTReport()
        exitcode, info = smart(param)
        if exitcode != 0:
            return UnableToGetSMARTReport(info)

        # TODO really check here
        # pylint: disable=unused-variable
        reallocated_sector_cnt = self._smart_attribute(info, "Reallocated_Sector_Ct")
        reallocated_event_cnt = self._smart_attribute(info, "Reallocated_Event_Count")
        spin_retry_count = self._smart_attribute(info, "Spin_Retry_Count")
        end_to_end_error = self._smart_attribute(info, "End-to-End_Error")

        seek_error_rate = self._smart_attribute(info, "Seek_Error_Rate")

        power_cycle_count = self._smart_attribute(info, "Power_Cycle_Count")
        temperature_celsius = self._smart_attribute(info, "Temperature_Celsius")

        return None

    @staticmethod
    def name():
        return "smart-ata"

    @staticmethod
    def description():
        return "Watches S.M.A.R.T. attributes of ATA/SATA storage devices plugged in to the router."

    @staticmethod
    def _smart_attribute(info, name):
        try:
            attr = next(field for field in info["ata_smart_attributes"]["table"] if field["name"] == name)
            return attr["raw"]["value"]
        except StopIteration:
            return None  # No such attribute


class SmartNVVMe(Check):
    """Tracks pre-fail attributes in S.M.A.R.T. for NVVMe drives."""

    def _parameters(self, data):
        return tuple(Path("/dev").glob("nvme[0-9]"))

    def _run(self, data, param):
        if param is None:
            return NoSMARTDeviceReport()
        if shutil.which("smartctl") is None:
            return UnableToGetSMARTReport()
        exitcode, info = smart(param)
        if exitcode != 0:
            return UnableToGetSMARTReport(info)

        # TODO really check here
        # pylint: disable=unused-variable
        available_spare = self._smart_attribute(info, "available_spare")
        media_errors = self._smart_attribute(info, "media_errors")
        critical_warning = self._smart_attribute(info, "critical_warning")

        power_cycles = self._smart_attribute(info, "power_cycles")
        temperature = self._smart_attribute(info, "temperature")

        return None

    @staticmethod
    def name():
        return "smart-nvme"

    @staticmethod
    def description():
        return "Watches S.M.A.R.T. attributes of NVMe storage devices plugged in to the router."

    @staticmethod
    def _smart_attribute(info, name):
        return info["nvme_smart_health_information_log"].get(name)


class NoSMARTDeviceReport(NotApplicableReport):
    """There is no ATA/SATA/NVMe device so there is nothing to check."""

    def summary(self):
        return _("There is no such device detected in system.")

    def details(self):
        return _(
            "Check found no ATA/SATA/NVMe block device in system. This is most likely because there is just no "
            "such device plugged in."
        )


class UnableToGetSMARTReport(InconclusiveReport):
    """It is possible that either device does not support S.M.A.R.T. or that smartmontools are not installed."""

    def __init__(self, info=None):
        # Info is either from smartctl in case of failed smartctl or None in case of missing smartmontools.
        self.info = info

    def summary(self):
        return _("It is not possible to read extcsd data.")

    def details(self):
        if self.info is None:
            return _("MMC tools (mmc-utils) are missing or not accessible.")
        return _("Read failed with error: ") + str(self.info["smartctl"]["messages"][0]["string"])

    def suggestion(self):
        if self.info is None:
            return _("You should install mmc-utils or any other package that provides mmc-utils's command 'mmc'.")
        return super().suggestion()
