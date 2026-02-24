import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def setup():
    sys.path.append(str(BASE_DIR))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lms_admin.settings")
    import django  # noqa: WPS433
    if not getattr(django, "setup_done", False):
        django.setup()
        setattr(django, "setup_done", True)

