"""This module implements abstraction for checks reports.

Check execution terminates with report. There are defined types of reports and those are implemented here. Check
instanciate correct type.
"""
import abc
import collections
import collections.abc
import typing

from ._gettext import _

LEVEL_ADVICE = 20  # The low boundary for advices
LEVEL_WARNING = 40  # The low boundary for warnings
LEVEL_ERROR = 60  # The low boundary for errors
LEVEL_FATAL_ERROR = 80  # The low boundary for fatal errors


class Report(abc.ABC):
    """Generic report implementation."""

    @abc.abstractstaticmethod
    def level() -> int:
        """Returns numerical level of this report. You can use it to sort reports. Level should be from 0 to 100 but
        that is in no way ensured.
        """

    @abc.abstractstaticmethod
    def level_name() -> str:
        """Returns name of this report. This is suppose to be used to tell user what this report is.
        To identify reports them self please use isinstance() instead.
        """

    @abc.abstractstaticmethod
    def level_description() -> str:
        """Returns description of this report level.
        In other words it is string telling user how important this report is.
        """

    @abc.abstractmethod
    def summary(self) -> str:
        """Returns description of this report. It is generaly short summary about report info."""

    @abc.abstractmethod
    def details(self) -> str:
        """Returns long description of this report. It contains all info that can be provided to user."""

    def suggestion(self) -> typing.Optional[str]:
        """Returns suggestion how to potentially improve reported state. This function can return None if there is
        nothing to suggest.
        """

    def __str__(self) -> str:
        return f"{self.level_name()}: {self.summary()}"

    def description(self) -> str:
        """Full string description."""
        res = str(self)
        res += "\n" + self.details()
        suggestion = self.suggestion() or None
        if suggestion is not None:
            res += "\n" + suggestion
        return res

    def volatility(self) -> float:
        """Returns number between between zero and one. This number informs how volatile report can be considered. Zero
        means no change is expected unless there is user's or other unconsidered intervention. One is other case and
        report is expected to change almost immediately.
        As change of report we consider change of report level/type. Change of details in same report type is not change
        of report.
        """
        return 0

    @staticmethod
    def _calculate_volatility(data_points, min: float = -math.inf, max: flost = math.inf, trend: float = .0):
        """This is helper function for calculating volatility from series of data points recorded in time.

        trend: this is expected trend of data where positive number is rising, negative number is falling and zero is
            no change in value. In match speak this is derivative at a point.
        """
        # Here comes the math
        return 0

    def effective_level(self):
        """This is combination of report level and volatility. High volatility decreases level.
        """
        lvl = self.level()
        return lvl - (lvl * self.volatility())


class InconclusiveReport(Report):
    """Report used when check is unable to finish or failed."""

    @property
    def level(self):
        return 5

    @staticmethod
    def level_name():
        return _("Inconclusive")

    def level_description(self):
        return _(
            "Check was inconclusive. This means that for some reason check wasn't able to generate any other "
            "report. This is mostly because it failed horribly."
        )


class NotApplicableReport(Report):
    """Report used when check passed but had nothing to do for what ever reason."""

    @staticmethod
    def level():
        return 0

    @staticmethod
    def level_name():
        return _("Not applicable")

    def level_description(self):
        return _(
            "Check wasn't applicable. This is most probably because it checks system attribute that is not"
            "installed or activated."
        )


class PassReport(Report):
    """Report used when everything is OK."""

    @staticmethod
    def level():
        return 10

    @staticmethod
    def level_name():
        return _("Pass")

    @staticmethod
    def level_description():
        return _("Check successfully passed. No problem was detected.")


class TryAgainLater(Report):
    """This is special report that specifies that check can't decide right now but should be able after some amount of
    time.
    Common use for this is when check tracks some trend and has no previous data to conclude any result right now.
    """

    @staticmethod
    def level():
        return 15

    @staticmethod
    def level_name():
        return _("Try again later")

    def level_description(self):
        return _(
            "Check can't be finished at the moment but should be able after a while. This is commonly becuase it"
            "lacks data to assess trends from."
        )


class SoftwareReport(Report):
    """Generic report for all software  related reports."""


class SoftwareAdviseReport(SoftwareReport):
    """Report used when advise should be reported regarding of software on router."""

    @property
    def level(self):
        return LEVEL_ADVICE

    @staticmethod
    def level_name():
        return _("Software advise")

    @staticmethod
    def level_description():
        return _("Check provides advise regarding software running on router.  Please consider it.")


class SoftwareWarningReport(SoftwareReport):
    """Report used when detected problem is of software kind and is far from fatal."""

    @property
    def level(self):
        return LEVEL_WARNING

    @staticmethod
    def level_name():
        return _("Software warning")

    def level_description(self):
        return _(
            "Check detected problem with software. It is far from fatal but it might be causing some functionality"
            "degradation now or in future. Please solve this issue at your convenience."
        )


class SoftwareErrorReport(SoftwareReport):
    """Report used when detected problem is of software kind and is not immediately fatal."""

    @property
    def level(self):
        return LEVEL_ERROR

    @staticmethod
    def level_name():
        return _("Software error")

    def level_description(self):
        return _(
            "Check detected dangerous problem with software. It is not immediately fatal but it possibly causes"
            "some functionality degradation and/or it can progress to be fatal for device functionality. Please"
            "resolver this problem as soon as possible."
        )


class SoftwareFatalErrorReport(SoftwareReport):
    """Report used when detected problem is of software kind and is affecting primary router functionality."""

    @property
    def level(self):
        return LEVEL_FATAL_ERROR

    @staticmethod
    def level_name():
        return _("Software fatal error")

    @staticmethod
    def level_description():
        return _("Check detected fatal problem with software. It is causing system to not work properly.")


class HardwareReport(Report):
    """Generic report for hardware issues."""


class HardwareWarningReport(HardwareReport):
    """Report used when detected problem is of hardware kind and is far from fatal."""

    @property
    def level(self):
        return LEVEL_WARNING + 10

    @staticmethod
    def level_name():
        return _("Hardware warning")

    def level_description(self):
        return _(
            "Check detected problem with hardware. It is far from fatal but it might be causing some functionality"
            "degradation now or in future. Please solve this issue at your convenience."
        )


class HardwareErrorReport(HardwareReport):
    """Report used when detected problem is of hardware kind and is not immediately fatal."""

    @property
    def level(self):
        return LEVEL_ERROR + 10

    @staticmethod
    def level_name():
        return _("Hardware error")

    def level_description(self):
        return _(
            "Check detected dangerous problem with hardware. It is not immediately fatal but it possibly causes"
            "some functionality degradation and/or it can progress to be fatal for device. Please resolver this"
            "problem as soon as possible."
        )


class HardwareFatalErrorReport(HardwareReport):
    """Report used when detected problem is of hardware kind and is affecting router functionality."""

    @property
    def level(self):
        return LEVEL_FATAL_ERROR + 10

    @staticmethod
    def level_name():
        return _("Hardware fatal error")

    @staticmethod
    def level_description():
        return _("Check detected fatal problem with hardware. It is causing system to not work properly.")


class SecurityReport(SoftwareReport):
    """Generic report for security related issues."""


class SecurityAdviseReport(SecurityReport):
    """Report used when security advise should be reported."""

    @property
    def level(self):
        return LEVEL_ADVICE + 5

    @staticmethod
    def level_name():
        return _("Security advise")

    @staticmethod
    def level_description():
        return _("Check detected possible security concern. It provides advise.  Please consider it.")


class SecurityWarningReport(SecurityReport):
    """Report used when check detected problem with possible security hole."""

    @property
    def level(self):
        return LEVEL_WARNING + 5

    @staticmethod
    def level_name():
        return _("Security warning")

    def level_description(self):
        return _(
            "Check detected possible security problem. It is advised to solve it as soon as possible to mitigate"
            "possible exploit."
        )


class MultiReport(Report, collections.abc.Mapping):
    """This is combination report. It combines multiple reports from same check. Every report has some string identifier
    in this report.
    It has no level but rather it represents itself as having highest level of assigned sub-reports.
    """

    def __init__(self, subreports: typing.Dict[str, Report]):
        super().__init__()
        self._subreports = dict(sorted(subreports.items(), key=lambda report: report[1].level, reverse=True))

    @property
    def level(self):
        # Note: reports are sorted so the first one is the maximum level
        return max(report.level for report in self._subreports.values())

    def level_name(self):
        # Note: reports are sorted so the first one is the one with maximum level
        return next(iter(self._subreports.values())).level_name()

    def level_description(self):
        # Note: reports are sorted so the first one is the one with maximum level
        return next(iter(self._subreports.values())).level_description()

    def summary(self) -> str:
        return "\n".join((f"{key}: {report.summary()}" for key, report in self._subreports.items()))

    def details(self) -> str:
        return "\n".join((f"{key}: {report.details()}" for key, report in self._subreports.items()))

    def suggestion(self) -> typing.Optional[str]:
        return "\n".join(
            (
                f"{key}: {report.suggestion()}"
                for key, report in self._subreports.items()
                if report.suggestion() is not None
            )
        )

    def description(self) -> str:
        res = []
        for key, report in self._subreports.items():
            res.append(f"{key}: {str(report)}\n{report.details()}")
            if report.suggestion() is not None:
                res[-1] += f"\n{self.suggestion()}"
        return "\n".join(res)

    def __getitem__(self, key) -> Report:
        return self._subreports[key]

    def __iter__(self) -> typing.Iterator:
        return iter(self._subreports)

    def __len__(self) -> int:
        return len(self._subreports)
