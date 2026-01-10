"""App package."""
from .factory import create_app
from .version import get_version

__all__ = ['create_app', 'get_version']
