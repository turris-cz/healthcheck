"""This implements classes to handle configuration for both healtcheck itself and every individual check.
"""
import abc
import collections.abc
import dataclasses
import functools
import re
import typing

from euci import EUci

UCI_CONFIG = "healthcheck"


@dataclasses.dataclass
class ConfigOption:
    """Description of specific configuration option."""

    name: str
    description: str
    type: type = str
    list: bool = False
    default: typing.Any = None


class ConfigValue:
    """The representation of configuration value."""

    def __init__(self, euci: EUci, config_section_type: str, config_section: str, option: ConfigOption):
        self._euci = euci
        self._section_type = config_section_type
        self._section = config_section
        self.option = option

    @property
    def value(self):
        """Provides access to configuration value."""
        return self._euci.get(
            *self.path(),
            dtype=self.option.type,
            default=self.option.default if not self.option.list or self.option.default else tuple(),
            list=self.option.list,
        )

    def set(self, value):
        """Allow change of this value in configuration.
        It only does uci.set(), the commit has to be called by caller.
        """
        raise NotImplementedError

    def path(self, join: bool = False):
        """Provides access to complete UCI path. That is three levels (config, section, option).

        join: join levels by dot to single string
        """
        if join:
            return ".".join(self.path())
        return UCI_CONFIG, self._section, self.option.name


class Configurable(abc.ABC):
    """Abstract class declaring class that it can be configured."""

    def __init__(self, euci: EUci):
        self.config = {
            option.name: ConfigValue(euci, self.config_type(), self.config_name(), option)
            for option in self.config_options()
        }

    @classmethod
    @abc.abstractmethod
    def config_name(cls) -> str:
        """The name used to identify configuration section."""

    @classmethod
    @abc.abstractmethod
    def config_type(cls) -> str:
        """The name of type used to identify configuration section."""

    @classmethod
    @abc.abstractmethod
    def config_options(cls) -> collections.abc.Iterable[ConfigOption]:
        """The listing of all possible configuration options for the associated configuration section."""

    @staticmethod
    def _canon_name(fullname: str) -> str:
        """Canonize name to format allowed by UCI. Any unsupported character is replaced by '_'."""
        return re.sub(r"[^a-zA-Z0-9_]", "_", fullname)
