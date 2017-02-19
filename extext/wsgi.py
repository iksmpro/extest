"""
WSGI config for extext project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "extext.settings")

application = get_wsgi_application()

# this code executes only when runserver and server starts
from .longjobs import periodic_task
periodic_task.delay()
