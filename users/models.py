from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Vlastní uživatel – připraveno na budoucí rozšíření (např. číslo účtu pro QR)."""
    pass