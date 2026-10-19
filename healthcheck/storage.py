"""The implementation of both temporally and permanent storage that is easy to use."""

import abc
import collections.abc
import fcntl
import json
import os
import pathlib


class Storage(collections.abc.MutableMapping):
    """Generic storage implemntation."""

    def __init__(self, path: pathlib.Path, update: bool = True):
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        self.path = path
        self._update = update
        existed = path.exists()
        self.file = open(path, "r+" if existed else "x", encoding="utf-8")
        fcntl.flock(self.file.fileno(), fcntl.LOCK_EX if update else fcntl.LOCK_SH)
        if existed:
            self.file.seek(0)
            self.data = json.load(self.file)
        else:
            self.data = {}
            self.file.write("{}")
        if not update:
            self.file.close()  # This automatically reelases the lock

    def close(self):
        """Update file content, if requested, and close."""
        if not self._update:
            return  # Nothing to do
        self.file.seek(0)
        json.dump(self.data, self.file)
        self.file.truncate(self.file.tell())
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


class TemporallyStorage(Storage):
    """Storage in tmpfs. The storage is removed on device reboot."""

    def __init__(self, identifier: str, update: bool = True):
        super().__init__(pathlib.Path("/var/run/healthcheck") / identifier, update)


class PermanentStorage(Storage):
    """Storage in tmpfs. The storage is removed on device reboot."""

    def __init__(self, identifier: str, update: bool = True):
        super().__init__(pathlib.Path("/usr/share/healthcheck") / identifier, update)
