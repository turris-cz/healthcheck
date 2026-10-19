from pathlib import Path

from healthcheck.check import Check
from healthcheck.report import PassReport, SoftwareAdviseReport

from ._gettext import _


class MergeConffiles(Check):
    """Checks if there are not some configuration files ready for merge.

    All files are provided by packages are automatically replaced when a package is updated with exception of modified
    configuration files. For those the new version is placed to file wiht '-opkg' stem.

    Users should merge such files manually to update basic configuration.
    """

    DEFAULT_IGNORES = (
        "/etc/config/*",  # These are modified by UCI and are expected to be migrated by associated packages
        # The following files are in reality system files and are shipped in packages only to provide initial file
        "/etc/group",
        "/etc/passwd",
        "/etc/shadow",
        "/etc/shells",
    )

    def _run(self, data, param):
        unmerged_conffiles = {}
        for conffiles_path in Path("/usr/lib/opkg/info").glob("*.conffiles"):
            pkg_name = conffiles_path.stem
            with conffiles_path.open() as file:
                conffiles = [Path(path.strip()) for path in file]
            unmerged = []
            for path in conffiles:
                opkg = path.with_name(path.name + "-opkg")
                if not opkg.exists():
                    continue
            unmerged = [
                path
                for path in conffiles
                if not self._path_ignored(path) and path.with_name(path.name + "-opkg").exists()
            ]
            if unmerged:
                unmerged_conffiles[pkg_name] = unmerged
        if conffiles:
            return MergeConffilessAdvise(unmerged_conffiles)
        return MergeConffilesPass()

    @staticmethod
    def name():
        return "merge-conffiles"

    @staticmethod
    def description():
        return _("Notifies about updates of the configuration files in packages.")

    def _path_ignored(self, path):
        for pattern in self.DEFAULT_IGNORES:
            if path.match(pattern):
                return True
        return False


class MergeConffilesPass(PassReport):
    """There are no unmerged configuration files."""

    def summary(self):
        return _("There are no configuration files with need for merge.")

    def details(self):
        return _(
            "The configuration files are updated automatically only if they were not modified in the meantime. "
            "They are never automatically replaced once they are modified. The new version is always placed to "
            "the file with '-opkg' suffix with expectation that user is going to manually update their "
            "current configuration file. Right now there are no configuration files that would require merging."
        )


class MergeConffilessAdvise(SoftwareAdviseReport):
    """There are unmerged default configuration files."""

    def __init__(self, conffiles):
        self.conffiles = conffiles

    def summary(self):
        return _("There are some configuration files with updated defaults that should be reviewed and merged.")

    def details(self):
        return (
            _("The following configuration files from these packages should be merged:")
            + "\n"
            + "\n".join((f"* {pkg}: " + ", ".join(map(str, confs)) for pkg, confs in self.conffiles.items()))
        )

    def suggestion(self):
        return _(
            "These configuration files were modified either directly by you or by application you used. "
            "You want to check the new default state saved in '*-opkg' file (the original file name with '-opkg' "
            "appended and update your configuration accordingly. Then you can remove '*-opkg' file."
        )
