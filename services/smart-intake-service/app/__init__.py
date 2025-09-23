# Enable namespace package so this 'app' can coexist with other 'app.*' packages (e.g., app.mq)
# This prevents import errors like "No module named 'app.mq'" caused by package shadowing.
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)