from hashlib import sha256
from pathlib import Path

from healthcheck.check import Check
from healthcheck.report import PassReport, SoftwareWarningReport

from ._gettext import _


class PkgCheck(Check):
    """Checks if all files installed from distribution (from packages) are not modified.

    Modification of such files is not harmful on its own but such modification is overwritten once package owning such
    file is updated or reinstalled.
    """

    DEFAULT_IGNORE = ("/etc/uci-defaults/*",)

    def _run(self, data, param):
        modified = {}
        for sha256_path in Path("/usr/lib/opkg/info").glob("*.files-sha256sum"):
            pkg_name = sha256_path.stem
            conffiles = []
            conffiles_path = sha256_path.with_suffix(".conffiles")
            if conffiles_path.exists():
                with conffiles_path.open() as file:
                    conffiles = file.file.lines()
            with sha256_path.open() as file:
                for line in file:
                    file_hash, path = line.strip().split(maxsplit=1)
                    if path in conffiles or any(Path(path).match(pattern) for pattern in self.DEFAULT_IGNORE):
                        continue
                    if file_hash != self._sha256sum(path):
                        if pkg_name not in modified:
                            modified[pkg_name] = list()
                        modified[pkg_name].append(path)
        if modified:
            return PkgCheckReport(modified)
        return PkgCheckPass()

    @staticmethod
    def name():
        return "pkg-check"

    @staticmethod
    def description():
        return _(
            "Verify that none of the user's modifications in files provided by packages would be removed by update."
        )

    @staticmethod
    def _sha256sum(path):
        try:
            with open(path, "rb") as file:
                hashobj = sha256()
                while True:
                    buf = file.read(8192)
                    if len(buf) == 0:
                        break
                    hashobj.update(buf)
                return hashobj.hexdigest()
        except FileNotFoundError:
            return "0" * 64


class PkgCheckPass(PassReport):
    """All files from all installed packages matched their recoded hashes."""

    def summary(self):
        return _("All files provided by packages are in their original state")

    def details(self):
        return _(
            "No files from packages were modified and thus there is no danger that subsequent update would erase these changes."
        )


class PkgCheckReport(SoftwareWarningReport):
    """There are modified files from packages."""

    def __init__(self, modified):
        self.modified = modified

    def summary(self):
        return _("Some files from system packages were modified.")

    def details(self):
        return (
            _("The changes in these files from these packages are going to be wiped with subsequent updates:")
            + "\n"
            + "\n".join((f"* {pkg}: " + ", ".join(files) for pkg, files in self.modified.items()))
        )

    def suggestion(self):
        return _(
            "You should revert changes by reinstalling the affected packages and investigate the alternative "
            "approach for anything you are trying to achieve.\n"
            "Most of the packages provide a way to add configuration without having to modify the root configuration "
            "file. Look for directories with '.d' suffix.\n"
            "If you are modifying some sort of the script you should think about sending your change to the upstream."
            " It is open-source non the less."
        )
