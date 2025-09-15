from pkgutil import extend_path

# Make "app" a namespace package so multiple subpackages (db, storage, schemas, etc.)
# can coexist on sys.path.
__path__ = extend_path(__path__, __name__)
