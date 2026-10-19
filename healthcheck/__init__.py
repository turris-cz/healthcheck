"""This is Healthcheck. Tool to run various checks to ensure that system is in stable condition."""

import collections.abc
import logging
import typing

import pkg_resources
from euci import EUci

from .plugin import Plugin

logger = logging.getLogger(__name__)


class HealthCheck(collections.abc.Mapping):
    """System health checking top level handler. Use this to run various checks."""

    def __init__(
        self,
        plugins_discovery: bool = True,
        disable_plugins: collections.abc.Container[str] = frozenset(),
        extra_plugins: collections.abc.Iterable[typing.Type[Plugin]] = (),
    ):
        """Initialize Healthcheck handle.

        plugins_discovery: if automatic plugin discovery using package resources should be attempted.
        disable_plugins: set of all names of discovered plugins to skip loading. Note that these are names declared by
            setuptools. They should be same as plugin names but it is not ensured.
        extra_plugins: list with extra plugins to load.
        """
        self._plugins: dict[str, Plugin] = {}
        self.euci = EUci()
        # Discover available plugins
        if plugins_discovery:
            for plugin in pkg_resources.iter_entry_points("healthcheck.plugins"):
                if plugin.name not in disable_plugins:
                    try:
                        loaded_plugin = plugin.load()
                    except Exception:
                        logging.exception("Plugin '%s' failed to load", plugin.name)
                    if plugin.name != loaded_plugin.name():
                        logging.warning(
                            "Setup tool plugin '%s' has different name: %s", plugin.name, loaded_plugin.name()
                        )
                    self.__add_plugin(loaded_plugin)
        # Push extra plugins
        for plugin in extra_plugins:
            self.__add_plugin(plugin)

    def __add_plugin(self, plugin):
        """Method used from __init__ to load and sanity check plugins."""
        if issubclass(plugin, Plugin):
            try:
                self._plugins[plugin.name()] = plugin(self.euci)
            except Exception:
                logger.exception("Plugin '%s' failed to instantiate", plugin.name)
        else:
            logger.error(
                "Class provided for plugin '%s' is not Healthcheck Plugin instance.",
                str(plugin),
            )

    def __getitem__(self, key) -> Plugin:
        return self._plugins[key]

    def __iter__(self) -> typing.Iterator:
        return iter(self._plugins)

    def __len__(self) -> int:
        return len(self._plugins)
