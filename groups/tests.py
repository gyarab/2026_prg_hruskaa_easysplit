from django.test import TestCase
from django.urls import reverse

from users.models import User

from .models import Group, Membership


def make_group(owner, name="Byt"):
    group = Group.objects.create(name=name, created_by=owner)
    Membership.objects.create(user=owner, group=group, role=Membership.Role.OWNER)
    return group


class GroupTestBase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="Heslo-12345")
        self.member = User.objects.create_user("member", password="Heslo-12345")
        self.outsider = User.objects.create_user("outsider", password="Heslo-12345")
        self.group = make_group(self.owner)
        Membership.objects.create(user=self.member, group=self.group)


class GroupAccessTests(GroupTestBase):
    def test_list_requires_login(self):
        url = reverse("group_list")
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_list_shows_only_own_groups(self):
        make_group(self.outsider, name="Cizi skupina")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("group_list"))
        self.assertContains(response, "Byt")
        self.assertNotContains(response, "Cizi skupina")

    def test_outsider_gets_404_on_detail(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("group_detail", args=[self.group.pk]))
        self.assertEqual(response.status_code, 404)

    def test_member_sees_detail(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("group_detail", args=[self.group.pk]))
        self.assertEqual(response.status_code, 200)


class GroupCreateTests(TestCase):
    def test_creator_becomes_owner(self):
        user = User.objects.create_user("novak", password="Heslo-12345")
        self.client.force_login(user)
        response = self.client.post(
            reverse("group_create"),
            {"name": "Chata", "description": "", "base_currency": "EUR"},
        )
        group = Group.objects.get(name="Chata")
        self.assertRedirects(response, reverse("group_detail", args=[group.pk]))
        self.assertTrue(group.is_owner(user))
        self.assertEqual(group.base_currency, "EUR")


class InviteTests(GroupTestBase):
    def test_join_via_token(self):
        self.client.force_login(self.outsider)
        url = reverse("group_join", args=[self.group.invite_token])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url)
        self.assertTrue(self.group.memberships.filter(user=self.outsider).exists())

    def test_joining_twice_does_not_duplicate(self):
        self.client.force_login(self.member)
        url = reverse("group_join", args=[self.group.invite_token])
        self.client.post(url)
        self.assertEqual(self.group.memberships.filter(user=self.member).count(), 1)

    def test_regenerate_invalidates_old_token(self):
        old = self.group.invite_token
        self.client.force_login(self.owner)
        self.client.post(reverse("group_regenerate_invite", args=[self.group.pk]))
        self.group.refresh_from_db()
        self.assertNotEqual(old, self.group.invite_token)
        response = self.client.get(reverse("group_join", args=[old]))
        self.assertEqual(response.status_code, 404)

    def test_member_cannot_regenerate(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("group_regenerate_invite", args=[self.group.pk])
        )
        self.assertEqual(response.status_code, 403)


class MembershipManagementTests(GroupTestBase):
    def test_owner_can_remove_member(self):
        membership = self.group.memberships.get(user=self.member)
        self.client.force_login(self.owner)
        self.client.post(
            reverse("member_remove", args=[self.group.pk, membership.pk])
        )
        self.assertFalse(self.group.memberships.filter(user=self.member).exists())

    def test_member_cannot_remove_others(self):
        membership = self.group.memberships.get(user=self.owner)
        self.client.force_login(self.member)
        response = self.client.post(
            reverse("member_remove", args=[self.group.pk, membership.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.group.memberships.filter(user=self.owner).exists())

    def test_member_can_leave(self):
        self.client.force_login(self.member)
        self.client.post(reverse("group_leave", args=[self.group.pk]))
        self.assertFalse(self.group.memberships.filter(user=self.member).exists())

    def test_owner_cannot_leave(self):
        self.client.force_login(self.owner)
        self.client.post(reverse("group_leave", args=[self.group.pk]))
        self.assertTrue(self.group.memberships.filter(user=self.owner).exists())

    def test_only_owner_can_delete(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("group_delete", args=[self.group.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Group.objects.filter(pk=self.group.pk).exists())

        self.client.force_login(self.owner)
        self.client.post(reverse("group_delete", args=[self.group.pk]))
        self.assertFalse(Group.objects.filter(pk=self.group.pk).exists())