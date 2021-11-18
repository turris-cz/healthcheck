"""This module implements abstraction for checks reports.

Any check execution terminates with a report. There are defined types of reports and those are implemented here.
The check instanciates the correct one.
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

    @property
    @abc.abstractmethod
    def level(self) -> int:
        """Returns a numerical level of this report. You can use it to sort reports.
        The level should be from 0 to 100, but that is in no way ensured.
        """

    @abc.abstractmethod
    def level_name(self) -> str:
        """Returns the name of this report. This is supposed to be used to tell the user what
        this report is. To identify reports themselves, please use isinstance() instead.
        """

    @abc.abstractmethod
    def level_description(self) -> str:
        """Returns a description of this report level.
        In other words it is a string telling the user how important the report is.
        """

    @abc.abstractmethod
    def summary(self) -> str:
        """Returns a description of this report. It is generaly a short summary of the reported info."""

    @abc.abstractmethod
    def details(self) -> str:
        """Returns a long description of this report. It contains all the info that can be provided to user."""

    def suggestion(self) -> typing.Optional[str]:
        """Returns a suggestion on how to potentially improve the reported state.
        This function can return \"None\" if there is nothing to suggest.
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


class InconclusiveReport(Report):
    """Report used when the check is unable to finish or has failed."""

    @property
    def level(self):
        return 5

    def level_name(self):
        return _("Inconclusive")

    def level_description(self):
        return _(
            "The check was inconclusive. This means that for some reason the check wasn't "
            "able to generate any other report. This highly suggests it failed horribly."
        )


class NotApplicableReport(Report):
    """Report used when a check passed, but had nothing to do for whatever reason."""

    @property
    def level(self):
        return 0

    def level_name(self):
        return _("Not applicable")

    def level_description(self):
        return _(
            "The check wasn't applicable. "
            "This is most probably because it checks a system attribute that is not installed or activated."
        )


class PassReport(Report):
    """Report used when everything is OK."""

    @property
    def level(self):
        return 10

    def level_name(self):
        return _("Pass")

    def level_description(self):
        return _("Check passed. No problem was detected.")


class TryAgainLater(Report):
    """This is special report specifying that a check can't decide right now,
    but should be able after some amount of time.
    A common use for this is when a check tracks some trend and has no previous data to conclude any result right now.
    """

    @property
    def level(self):
        return 15

    def level_name(self):
        return _("Try again later")

    def level_description(self):
        return _(
            "The Check can't finish at the moment, but should be able after a while. "
            "This is commonly becuase it lacks data to assess trends from."
        )


class SoftwareReport(Report):
    """Generic report for all software  related reports."""


class SoftwareAdviseReport(SoftwareReport):
    """Report used when advice should be reported regarding the software on the router."""

    @property
    def level(self):
        return LEVEL_ADVICE

    def level_name(self):
        return _("Software advise")

    def level_description(self):
        return _("The check provides advice regarding the software running on the router. Please consider it.")


class SoftwareWarningReport(SoftwareReport):
    """Report used when a detected problem is of the software kind and far from fatal."""

    @property
    def level(self):
        return LEVEL_WARNING

    def level_name(self):
        return _("Software warning")

    def level_description(self):
        return _(
            "A check detected a problem with the software."
            "It is far from fatal, but it might be causing some functionality degradation now or in future."
            "Please solve this issue at your convenience."
        )


class SoftwareErrorReport(SoftwareReport):
    """Report used when a detected problem is of the software kind and not immediately fatal."""

    @property
    def level(self):
        return LEVEL_ERROR

    def level_name(self):
        return _("Software error")

    def level_description(self):
        return _(
            "A check detected a dangerous problem with the software. It is not immediately fatal, but it"
            "possibly causes some functionality degradation and/or it can turn fatal for device functionality."
            "Please resolve this problem as soon as possible."
        )


class SoftwareFatalErrorReport(SoftwareReport):
    """Report used when a detected problem is of the software kind and affects primary router functionality."""

    @property
    def level(self):
        return LEVEL_FATAL_ERROR

    def level_name(self):
        return _("Software fatal error")

    def level_description(self):
        return _("A check detected a fatal problem with the software. It is causing the system not to work properly.")


class HardwareReport(Report):
    """Generic report for hardware issues."""


class HardwareWarningReport(HardwareReport):
    """Report used when a detected problem is of the hardware kind and far from fatal."""

    @property
    def level(self):
        return LEVEL_WARNING + 10

    def level_name(self):
        return _("Hardware warning")

    def level_description(self):
        return _(
            "A check detected a problem with the hardware. It is far from fatal, but might be causing some functionality"
            "degradation now or in future. Please solve this issue at your convenience."
        )


class HardwareErrorReport(HardwareReport):
    """Report used when detected problem is of the hardware kind and not immediately fatal."""

    @property
    def level(self):
        return LEVEL_ERROR + 10

    def level_name(self):
        return _("Hardware error")

    def level_description(self):
        return _(
            "A check detected a dangerous problem with hardware. It is not immediately fatal, but possibly causes"
            "some functionality degradation and/or it can turn fatal for the device."
            "Please resolver this problem as soon as possible."
        )


class HardwareFatalErrorReport(Report):
    """Report used when a detected problem is of the hardware kind and affects router functionality."""

    @property
    def level(self):
        return LEVEL_FATAL_ERROR + 10

    def level_name(self):
        return _("Fatal hardware error")

    def level_description(self):
        return _("A check detected a fatal problem with the hardware. It is causing the system to not work properly.")


class SecurityReport(SoftwareReport):
    """Generic report for security related issues."""


class SecurityAdviseReport(SecurityReport):
    """Report used when security advise should be reported."""

    @property
    def level(self):
        return LEVEL_ADVICE + 5

    def level_name(self):
        return _("Security advice")

    def level_description(self):
        return _("A check detected a possible security concern. It provides advice. Please consider it.")


class SecurityWarningReport(SecurityReport):
    """Report used when a check detected a problem with a possible security hole."""

    @property
    def level(self):
        return LEVEL_WARNING + 5

    def level_name(self):
        return _("Security warning")

    def level_description(self):
        return _(
            "A check detected a possible security problem. It is advised to solve it as soon as possible to mitigate"
            "any possible exploit."
        )


class MultiReport(Report, collections.abc.Mapping):
    """This is combination report. It combines multiple reports from the same check.
    Every report has some string identifier in this report.
    It has no level, but rather represents itself as having the highest level of assigned sub-reports.
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
