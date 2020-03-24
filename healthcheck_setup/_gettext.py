import gettext
import pathlib

_ = gettext.translation("healthcheck_setup", pathlib.Path(__file__).parent / "locale", fallback=True).gettext
