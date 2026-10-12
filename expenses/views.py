from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from groups.models import Group

from .forms import ExpenseForm
from .models import Expense


def _member_group(request, group_pk):
    return get_object_or_404(Group, pk=group_pk, memberships__user=request.user)


@login_required
def expense_create(request, group_pk):
    group = _member_group(request, group_pk)
    if request.method == "POST":
        form = ExpenseForm(request.POST, group=group)
        if form.is_valid():
            form.save_expense(request.user)
            messages.success(request, "Výdaj byl přidán.")
            return redirect("group_detail", pk=group.pk)
    else:
        form = ExpenseForm(group=group, initial={"paid_by": request.user.pk})
    return render(
        request,
        "expenses/expense_form.html",
        {"form": form, "group": group, "title": "Nový výdaj"},
    )


@login_required
def expense_detail(request, group_pk, pk):
    group = _member_group(request, group_pk)
    expense = get_object_or_404(Expense, pk=pk, group=group)
    context = {
        "group": group,
        "expense": expense,
        "shares": expense.shares.select_related("user").order_by("user__username"),
        "can_edit": expense.can_edit(request.user),
    }
    return render(request, "expenses/expense_detail.html", context)


@login_required
def expense_edit(request, group_pk, pk):
    group = _member_group(request, group_pk)
    expense = get_object_or_404(Expense, pk=pk, group=group)
    if not expense.can_edit(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = ExpenseForm(request.POST, instance=expense, group=group)
        if form.is_valid():
            form.save_expense(request.user)
            messages.success(request, "Výdaj byl upraven.")
            return redirect("expense_detail", group_pk=group.pk, pk=expense.pk)
    else:
        form = ExpenseForm(instance=expense, group=group)
    return render(
        request,
        "expenses/expense_form.html",
        {"form": form, "group": group, "title": "Upravit výdaj"},
    )


@login_required
@require_POST
def expense_delete(request, group_pk, pk):
    group = _member_group(request, group_pk)
    expense = get_object_or_404(Expense, pk=pk, group=group)
    if not expense.can_edit(request.user):
        raise PermissionDenied
    expense.delete()
    messages.success(request, "Výdaj byl smazán.")
    return redirect("group_detail", pk=group.pk)