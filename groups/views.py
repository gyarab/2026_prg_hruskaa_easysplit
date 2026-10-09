from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import GroupForm
from .models import Group, Membership


def _get_group(request, pk, owner_only=False):
    """Vrátí skupinu, jen pokud je uživatel její člen (jinak 404).
    Při owner_only navíc vyžaduje roli správce (jinak 403)."""
    group = get_object_or_404(Group, pk=pk, memberships__user=request.user)
    if owner_only and not group.is_owner(request.user):
        raise PermissionDenied
    return group


@login_required
def group_list(request):
    groups = request.user.split_groups.all()
    return render(request, "groups/group_list.html", {"groups": groups})


@login_required
def group_create(request):
    if request.method == "POST":
        form = GroupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                group = form.save(commit=False)
                group.created_by = request.user
                group.save()
                Membership.objects.create(
                    user=request.user, group=group, role=Membership.Role.OWNER
                )
            messages.success(request, f"Skupina „{group.name}“ byla vytvořena.")
            return redirect("group_detail", pk=group.pk)
    else:
        form = GroupForm()
    return render(request, "groups/group_form.html", {"form": form})


@login_required
def group_detail(request, pk):
    group = _get_group(request, pk)
    memberships = group.memberships.select_related("user").order_by("joined_at")
    invite_url = request.build_absolute_uri(
        reverse("group_join", args=[group.invite_token])
    )
    context = {
        "group": group,
        "memberships": memberships,
        "invite_url": invite_url,
        "is_owner": group.is_owner(request.user),
    }
    return render(request, "groups/group_detail.html", context)


@login_required
def group_join(request, token):
    group = get_object_or_404(Group, invite_token=token)

    if group.memberships.filter(user=request.user).exists():
        messages.info(request, "V této skupině už jste.")
        return redirect("group_detail", pk=group.pk)

    if request.method == "POST":
        Membership.objects.create(user=request.user, group=group)
        messages.success(request, f"Připojili jste se do skupiny „{group.name}“.")
        return redirect("group_detail", pk=group.pk)

    return render(request, "groups/group_join.html", {"group": group})


@login_required
@require_POST
def group_leave(request, pk):
    group = _get_group(request, pk)
    if group.is_owner(request.user):
        messages.error(
            request, "Správce nemůže skupinu opustit. Můžete ji ale smazat."
        )
        return redirect("group_detail", pk=group.pk)
    group.memberships.filter(user=request.user).delete()
    messages.success(request, f"Opustili jste skupinu „{group.name}“.")
    return redirect("group_list")


@login_required
@require_POST
def group_delete(request, pk):
    group = _get_group(request, pk, owner_only=True)
    name = group.name
    group.delete()
    messages.success(request, f"Skupina „{name}“ byla smazána.")
    return redirect("group_list")


@login_required
@require_POST
def group_regenerate_invite(request, pk):
    group = _get_group(request, pk, owner_only=True)
    group.regenerate_invite()
    messages.success(request, "Pozvánkový odkaz byl vygenerován znovu, starý už nefunguje.")
    return redirect("group_detail", pk=group.pk)


@login_required
@require_POST
def member_remove(request, pk, membership_id):
    group = _get_group(request, pk, owner_only=True)
    membership = get_object_or_404(group.memberships, pk=membership_id)
    if membership.user == request.user:
        messages.error(request, "Sami sebe odebrat nemůžete.")
    else:
        membership.delete()
        messages.success(request, f"Uživatel {membership.user} byl odebrán.")
    return redirect("group_detail", pk=group.pk)