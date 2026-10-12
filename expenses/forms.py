from decimal import Decimal

from django import forms
from django.db import transaction

from users.forms import BootstrapMixin
from users.models import User

from .models import Expense, ExpenseShare
from .splitting import EQUAL, SplitError, compute_shares


class ExpenseForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Expense
        fields = ("description", "amount", "paid_by", "date", "split_mode")
        labels = {
            "description": "Popis",
            "amount": "Částka",
            "paid_by": "Zaplatil",
            "date": "Datum",
            "split_mode": "Způsob dělení",
        }
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, group, **kwargs):
        self.group = group
        super().__init__(*args, **kwargs)

        self.members = list(
            User.objects.filter(memberships__group=group).order_by("username")
        )
        self.fields["amount"].label = f"Částka ({group.base_currency})"
        self.fields["paid_by"].queryset = User.objects.filter(
            pk__in=[u.pk for u in self.members]
        )
        self.fields["paid_by"].label_from_instance = lambda u: u.get_full_name() or u.username

        # dynamická pole pro každého člena
        for user in self.members:
            self.fields[f"include_{user.pk}"] = forms.BooleanField(
                required=False,
                initial=True,
                widget=forms.CheckboxInput(attrs={"class": "form-check-input include-input"}),
            )
            self.fields[f"value_{user.pk}"] = forms.DecimalField(
                required=False,
                min_value=Decimal("0"),
                max_digits=12,
                decimal_places=2,
                widget=forms.NumberInput(
                    attrs={"class": "form-control form-control-sm value-input", "step": "0.01"}
                ),
            )

        # při úpravě předvyplníme původní dělení
        if self.instance.pk:
            existing = {s.user_id: s for s in self.instance.shares.all()}
            for user in self.members:
                share = existing.get(user.pk)
                self.fields[f"include_{user.pk}"].initial = share is not None
                if share is not None and share.value is not None:
                    self.fields[f"value_{user.pk}"].initial = share.value

    def member_rows(self):
        """Trojice (člen, pole 'účastní se', pole 'hodnota') pro šablonu."""
        return [
            (u, self[f"include_{u.pk}"], self[f"value_{u.pk}"]) for u in self.members
        ]

    def clean(self):
        cleaned = super().clean()
        amount = cleaned.get("amount")
        mode = cleaned.get("split_mode")
        if amount is None or mode is None:
            return cleaned

        values, missing = {}, False
        for user in self.members:
            if not cleaned.get(f"include_{user.pk}"):
                continue
            value = cleaned.get(f"value_{user.pk}")
            field_name = f"value_{user.pk}"
            if mode != EQUAL and value is None and field_name not in self.errors:
                self.add_error(field_name, "Zadejte hodnotu.")
                missing = True
            values[user.pk] = value
        if missing:
            return cleaned

        try:
            self.shares = compute_shares(mode, amount, values)
        except SplitError as exc:
            raise forms.ValidationError(str(exc))
        self.share_inputs = values
        return cleaned

    @transaction.atomic
    def save_expense(self, user):
        expense = self.save(commit=False)
        expense.group = self.group
        if not expense.pk:
            expense.created_by = user
        expense.save()

        expense.shares.all().delete()
        is_equal = expense.split_mode == Expense.SplitMode.EQUAL
        ExpenseShare.objects.bulk_create(
            [
                ExpenseShare(
                    expense=expense,
                    user_id=user_id,
                    amount=amount,
                    value=None if is_equal else self.share_inputs[user_id],
                )
                for user_id, amount in self.shares.items()
            ]
        )
        return expense