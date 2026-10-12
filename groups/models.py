import uuid

from django.conf import settings
from django.db import models

CURRENCY_CHOICES = [
    ("CZK", "Česká koruna (CZK)"),
    ("EUR", "Euro (EUR)"),
    ("USD", "Americký dolar (USD)"),
    ("GBP", "Britská libra (GBP)"),
    ("PLN", "Polský zlotý (PLN)"),
]


class Group(models.Model):
    name = models.CharField("název", max_length=100)
    description = models.TextField("popis", blank=True)
    base_currency = models.CharField(
        "základní měna", max_length=3, choices=CURRENCY_CHOICES, default="CZK"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_groups",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Membership",
        related_name="split_groups",
    )
    invite_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "skupina"
        verbose_name_plural = "skupiny"

    def __str__(self):
        return self.name

    def is_owner(self, user):
        return self.memberships.filter(user=user, role=Membership.Role.OWNER).exists()

    def regenerate_invite(self):
        self.invite_token = uuid.uuid4()
        self.save(update_fields=["invite_token"])

    def has_activity(self, user):
        """Má uživatel ve skupině nějaké výdaje (zaplatil je nebo na nich dluží)?"""
        return self.expenses.filter(
            models.Q(paid_by=user) | models.Q(shares__user=user)
        ).exists()


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Správce"
        MEMBER = "member", "Člen"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "group"], name="unique_membership")
        ]
        verbose_name = "členství"
        verbose_name_plural = "členství"

    def __str__(self):
        return f"{self.user} v {self.group} ({self.get_role_display()})"