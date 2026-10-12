from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Expense(models.Model):
    class SplitMode(models.TextChoices):
        EQUAL = "equal", "Rovným dílem"
        EXACT = "exact", "Přesné částky"
        PERCENT = "percent", "Procenta"
        WEIGHT = "weight", "Váhy (podíly)"

    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, related_name="expenses"
    )
    description = models.CharField("popis", max_length=200)
    amount = models.DecimalField(
        "částka",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="paid_expenses",
        verbose_name="zaplatil",
    )
    date = models.DateField("datum", default=timezone.localdate)
    split_mode = models.CharField(
        "způsob dělení", max_length=10, choices=SplitMode.choices, default=SplitMode.EQUAL
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_expenses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "výdaj"
        verbose_name_plural = "výdaje"

    def __str__(self):
        return f"{self.description} ({self.amount})"

    def can_edit(self, user):
        """Upravit/smazat může autor výdaje nebo správce skupiny."""
        return user == self.created_by or self.group.is_owner(user)


class ExpenseShare(models.Model):
    """Kolik z výdaje dluží konkrétní člen (spočítaný podíl)."""

    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="shares")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expense_shares"
    )
    amount = models.DecimalField("podíl", max_digits=12, decimal_places=2)
    value = models.DecimalField(
        "zadaná hodnota", max_digits=12, decimal_places=2, null=True, blank=True
    )  # částka / % / váha, jak ji uživatel zadal (u rovného dělení prázdné)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["expense", "user"], name="unique_expense_share")
        ]

    def __str__(self):
        return f"{self.user}: {self.amount}"