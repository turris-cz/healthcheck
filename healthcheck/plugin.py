"""This module is intended to be used in healthcheck plugins.

You should import it to such plugin and use Plugin class to define it.
"""

import abc
import collections.abc
import typing

from . import config
from ._gettext import _
from .check import Check


class Plugin(collections.abc.Mapping, config.Configurable, metaclass=abc.ABCMeta):
    """Generic definition of healthcheck plugin."""

    def __init__(self, euci: config.EUci, checks: typing.Iterable[typing.Type[Check]]):
        """Initialization function which checks all checks.

        euci:
        checks: iterable with all checks classes.
        """
        config.Configurable.__init__(self, euci)
        self._checks = {check.name(): check(euci, self) for check in checks}

    def __getitem__(self, key) -> Check:
        return self._checks[key]

    def __iter__(self) -> typing.Iterator:
        return iter(self._checks)

    def __len__(self) -> int:
        return len(self._checks)

    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        """Name of plugin used to address it. It should be consistent with name set in setup tools.
        Do not localize this string!
        """

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str:
        """Description for this plugin."""

    @classmethod
    def config_type(cls):
        return "plugin"

    @classmethod
    def config_name(cls):
        return cls._canon_name(cls.name())

    @classmethod
    def config_options(cls):
        return (
            config.ConfigOption(
                name="enable",
                description=_("Can be used to disable all checks from this plugin. It has to be a boolean value."),
                type=bool,
                default=True,
            ),
        )
