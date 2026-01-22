#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

python_path = os.getenv("PYTHONPATH")
if python_path:
    sys.path.insert(0, python_path)


def main():
    """Run administrative tasks."""
    sys.path.append(os.path.join(os.path.dirname(__file__), "utils_site"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "utils_site.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
