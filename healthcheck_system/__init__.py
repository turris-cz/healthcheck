"""Healthcheck system checks."""

from euci import EUci

from healthcheck.plugin import Plugin

from ._gettext import _
from .flash_writes import FlashWrites
from .free_ram import FreeRam
from .free_storage import FreeStorage
from .merge_conffiles import MergeConffiles
from .mmc_life import MMCLife
from .pkg_check import PkgCheck
from .services import DisabledServices, ReenabledServices
from .smart import SmartATA, SmartNVVMe


class SystemPlugin(Plugin):
    """Healthcheck plugin for basic system stability and endurance checks."""

    def __init__(self, euci: EUci):
        super().__init__(
            euci,
            (
                FreeRam,
                FreeStorage,
                MMCLife,
                FlashWrites,
                SmartATA,
                SmartNVVMe,
                PkgCheck,
                MergeConffiles,
                ReenabledServices,
                DisabledServices,
            ),
        )

    @classmethod
    def name(cls):
        return "system"

    @classmethod
    def description(cls):
        return _("Basic system stability and endurance checks")
