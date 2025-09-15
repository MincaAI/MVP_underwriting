from pkgutil import extend_path

# Make "app.mq" a namespace subpackage so modules from multiple packages (schemas, mq)
# are accessible under a single package.
__path__ = extend_path(__path__, __name__)
