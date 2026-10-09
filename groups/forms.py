from django import forms

from users.forms import BootstrapMixin

from .models import Group


class GroupForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", "description", "base_currency")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}