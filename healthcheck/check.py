"""This module is intended to be used in healthcheck plugin checks modules.

You should import it to plugin and use its classes to define new checks.
"""

import abc
import sys
import traceback
import typing

from . import config, report
from ._gettext import _


class Check(config.Configurable, metaclass=abc.ABCMeta):
    """Generic definition of check.

    Implement this class to define new check. Note that check has to be part of plugin and has to be registered in that
    plugin to make it visible to healthcheck.
    """

    def __init__(self, euci: config.EUci, plugin):
        """Initialize check itself.

        config:
        """
        self.plugin = plugin
        config.Configurable.__init__(self, euci)

    def _collect_data(self) -> typing.Any:
        """Collect data required for check to be performed. This can be implemented when check collects a lot of data
        before it analyzes it in separate parametrized checks. It is beneficial only in combination with _parameters
        otherwise it all right to collect data in _run method.
        """

    def _parameters(self, data: typing.Any) -> typing.Optional[tuple[str, ...]]:
        """Provides a tuple of possible parameters the check can be run on. This can be optionally implemented if test
        is parametrized.
        """

    @abc.abstractmethod
    def _run(self, data: typing.Any, param: typing.Optional[str]) -> report.Report:
        """This function has to be implemented with check itself."""

    @staticmethod
    @abc.abstractmethod
    def name() -> str:
        """Name of check used to address it. Do not localize this string!"""

    @staticmethod
    @abc.abstractmethod
    def description() -> str:
        """Description for this check."""

    @classmethod
    def config_type(cls):
        return "check"

    @classmethod
    def config_name(cls):
        return cls._canon_name(cls.name())

    @classmethod
    def config_options(cls):
        return (
            config.ConfigOption(
                name="enable",
                description=_("Can be used to disable check execution. It has to be a boolean value."),
                type=bool,
                default=True,
            ),
        )

    def __call__(self) -> report.Report:
        """Run this check.

        Returns instance of Report.
        """
        if not self.config["enable"].value or not self.plugin.config["enable"].value:
            return DisabledCheckReport(self.plugin.config["enable"].value, self.config["enable"].value)
        try:
            data = self._collect_data() or None
            parameters = self._parameters(data) or None
            if parameters:
                return report.MultiReport({param: self.__run(data, param) for param in parameters})
            return self.__run(data, None)
        except Exception:  # pylint: disable=broad-exception-caught
            return InconclusiveExceptionReport()

    def __run(self, data, param):
        try:
            return self._run(data, param)
        except Exception:  # pylint: disable=broad-exception-caught
            return InconclusiveExceptionReport()


class InconclusiveExceptionReport(report.InconclusiveReport):
    """Check execution ended with exception."""

    def __init__(self):
        self._type, self._value, self._traceback = sys.exc_info()

    def summary(self) -> str:
        res = _("Check execution failed with exception: ") + self._type.__name__
        if str(self._value):
            res += f": {str(self._value)}"
        return res

    def details(self) -> str:
        return _("Traceback:") + "\n" + "".join(traceback.format_tb(self._traceback))


class DisabledCheckReport(report.InconclusiveReport):
    """Check execution wasn't attempted as it is disabled."""

    def __init__(self, enable_plugin: bool, enable_check: bool):
        self.disabled_plugin = not enable_plugin
        self.disabled_check = not enable_check

    def summary(self) -> str:
        return _("Check execution is disabled")

    def details(self) -> str:
        if self.disabled_plugin and self.disabled_check:
            return _("Both plugin as check itself are disabled in configuration. You are rigorous I give you that.")
        if self.disabled_plugin:
            return _("The plugin check is part of is explicitly disabled as whole in configuration.")
        return _("The check is explicitly disabled in configuration.")
