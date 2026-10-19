"""Command line interface of Healthcheck."""

import argparse
import logging
import os
import sys

from . import HealthCheck
from ._gettext import _
from ._output import ConsoleFormatter, JSONFormatter, NotificationFormatter

logger = logging.getLogger(__name__)

HELP_DESCRIPTION = _("System health checker.")


def parse_args():
    "Parse passed arguments and return result"
    parser = argparse.ArgumentParser(description=HELP_DESCRIPTION)
    parser.add_argument("--list", "-l", action="store_true", help=_("List all available checks"))
    parser.add_argument(
        "--config-list", "-c", action="store_true", help=_("List all available UCI configuration options")
    )
    parser.add_argument("--json", "-j", action="store_true", help=_("Output in JSON data format"))
    parser.add_argument("--background", "-b", action="store_true", help=_("Run healthcheck in background"))
    parser.add_argument(
        "--periodic", action="store_true", help=_("Periodic check that sends notifications when issues are found")
    )
    parser.add_argument(
        "check",
        nargs=argparse.REMAINDER,
        help=_("Check to be executed. If not specified then all checks are executed."),
    )
    return parser.parse_args()


def detach_std():
    "Expected to be called after fork in new process to set it up"
    sys.stdout.close()
    sys.stderr.close()
    sys.stdin.close()
    # The files have to stay open for the rest of the process lifetime.
    sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")  # pylint: disable=consider-using-with
    sys.stdin = open(os.devnull, "r", encoding="utf-8")  # pylint: disable=consider-using-with


def list_modules(handler):
    "Lists all available plugins with their checks"
    for plugin in handler:
        for check in handler[plugin]:
            print(plugin + ":" + check)


def list_config_options(handler):
    "List all available configuration options."

    def configs():
        for plugin in handler.values():
            yield from plugin.config.values()
            for check in plugin.values():
                yield from check.config.values()
        yield from NotificationFormatter(handler.euci).config.values()

    for config in configs():
        print(config.path(join=True))
        print("  " + config.option.description)


def select_checks(handler, requested):
    "Resolve requested checks to list of (plugin_name, check_name). All checks are selected if none are requested."
    if not requested:
        return [(plugin_name, check_name) for plugin_name, plugin in handler.items() for check_name in plugin]
    checks = []
    for req_check in requested:
        req_split = req_check.split(":", maxsplit=1)
        plugin_name = req_split[0]
        if plugin_name not in handler:
            logger.error("%s: %s", _("No such plugin"), plugin_name)
            continue
        if len(req_split) == 1:
            for check_name in handler[plugin_name]:
                checks.append((plugin_name, check_name))
        else:
            check_name = req_split[1]
            if check_name not in handler[plugin_name]:
                logger.error("%s: %s:%s", _("No such check in plugin"), plugin_name, check_name)
                continue
            checks.append((plugin_name, check_name))
    return checks


def main():
    "Main function of healthcheck"
    args = parse_args()

    handler = HealthCheck()

    if args.list:
        list_modules(handler)  # If plugins list is requested then just list it and exit
        return
    if args.config_list:
        list_config_options(handler)  # If configuration listing is requested then just list it and exit
        return

    if args.background:
        if os.fork():
            detach_std()
        else:
            return

    checks = select_checks(handler, args.check)

    formatter = (
        JSONFormatter() if args.json else NotificationFormatter(handler.euci) if args.periodic else ConsoleFormatter()
    )
    with formatter as format_reports:
        for check in checks:
            format_reports(check[0], check[1], handler[check[0]][check[1]]())


if __name__ == "__main__":
    main()
