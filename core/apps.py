from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.utils import OperationalError


def is_admin_present():
    try:
        User = get_user_model()
        return User.objects.filter(email='admin@example.com').exists()
    except OperationalError:
        return True

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if not is_admin_present():
            User.objects.create_superuser(
                email='admin@example.com',
                password='Admin123'
            )