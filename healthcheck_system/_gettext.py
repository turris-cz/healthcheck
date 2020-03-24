import gettext
import pathlib

_ = gettext.translation("healthcheck_system", pathlib.Path(__file__).parent / "locale", fallback=True).gettext
