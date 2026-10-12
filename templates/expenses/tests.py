from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from groups.models import Group, Membership
from users.models import User

from .models import Expense
from .splitting import SplitError, allocate, compute_shares

D = Decimal


class SplittingTests(SimpleTestCase):
    def test_equal_split_distributes_cents(self):
        result = compute_shares("equal", D("100"), {1: None, 2: None, 3: None})
        self.assertEqual(sorted(result.values()), [D("33.33"), D("33.33"), D("33.34")])
        self.assertEqual(sum(result.values()), D("100.00"))

    def test_equal_split_exact(self):
        result = compute_shares("equal", D("10"), {1: None, 2: None, 3: None, 4: None})
        self.assertEqual(set(result.values()), {D("2.50")})

    def test_weights(self):
        result = compute_shares("weight", D("100"), {1: D("2"), 2: D("1")})
        self.assertEqual(result, {1: D("66.67"), 2: D("33.33")})

    def test_weight_zero_gets_nothing(self):
        result = compute_shares("weight", D("10"), {1: D("1"), 2: D("0")})
        self.assertEqual(result, {1: D("10.00"), 2: D("0.00")})

    def test_weights_all_zero_rejected(self):
        with self.assertRaises(SplitError):
            compute_shares("weight", D("10"), {1: D("0"), 2: D("0")})

    def test_percent(self):
        result = compute_shares(
            "percent", D("99.99"), {1: D("50"), 2: D("30"), 3: D("20")}
        )
        self.assertEqual(result, {1: D("49.99"), 2: D("30.00"), 3: D("20.00")})
        self.assertEqual(sum(result.values()), D("99.99"))

    def test_percent_must_sum_to_100(self):
        with self.assertRaises(SplitError):
            compute_shares("percent", D("100"), {1: D("50"), 2: D("40")})

    def test_exact(self):
        result = compute_shares("exact", D("100"), {1: D("70"), 2: D("30")})
        self.assertEqual(result, {1: D("70.00"), 2: D("30.00")})

    def test_exact_must_match_total(self):
        with self.assertRaises(SplitError):
            compute_shares("exact", D("100"), {1: D("70"), 2: D("20")})

    def test_no_participants_rejected(self):
        with self.assertRaises(SplitError):
            compute_shares("equal", D("100"), {})

    def test_sum_always_equals_total(self):
        for people in range(1, 9):
            for cents in (1, 2, 7, 99, 100, 1001, 99999, 123457):
                total = D(cents) / 100
                weights = {i: D(i + 1) for i in range(people)}
                result = allocate(total, weights)
                self.assertEqual(sum(result.values()), total.quantize(D("0.01")))


class ExpenseTestBase(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("anna", password="Heslo-12345")
        self.member = User.objects.create_user("bob", password="Heslo-12345")
        self.third = User.objects.create_user("cyril", password="Heslo-12345")
        self.outsider = User.objects.create_user("dana", password="Heslo-12345")
        self.group = Group.objects.create(name="Byt", created_by=self.owner)
        Membership.objects.create(user=self.owner, group=self.group, role="owner")
        Membership.objects.create(user=self.member, group=self.group)
        Membership.objects.create(user=self.third, group=self.group)
        self.create_url = reverse("expense_create", args=[self.group.pk])

    def post_data(self, **overrides):
        data = {
            "description": "Nákup",
            "amount": "100.00",
            "paid_by": self.owner.pk,
            "date": "2026-10-10",
            "split_mode": "equal",
            f"include_{self.owner.pk}": "on",
            f"include_{self.member.pk}": "on",
            f"include_{self.third.pk}": "on",
        }
        data.update(overrides)
        return data

    def make_expense(self, creator):
        self.client.force_login(creator)
        self.client.post(self.create_url, self.post_data())
        return Expense.objects.get()


class ExpenseCreateTests(ExpenseTestBase):
    def test_equal_split_saved(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.create_url, self.post_data())
        self.assertRedirects(response, reverse("group_detail", args=[self.group.pk]))
        expense = Expense.objects.get()
        amounts = sorted(s.amount for s in expense.shares.all())
        self.assertEqual(amounts, [D("33.33"), D("33.33"), D("33.34")])
        self.assertEqual(expense.created_by, self.owner)

    def test_exact_mismatch_rejected(self):
        self.client.force_login(self.owner)
        data = self.post_data(
            split_mode="exact",
            **{f"value_{self.owner.pk}": "50", f"value_{self.member.pk}": "40",
               f"value_{self.third.pk}": "0"},
        )
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_missing_value_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.create_url, self.post_data(split_mode="percent"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)

    def test_only_selected_members_get_share(self):
        self.client.force_login(self.owner)
        data = self.post_data()
        del data[f"include_{self.third.pk}"]
        self.client.post(self.create_url, data)
        expense = Expense.objects.get()
        self.assertEqual(expense.shares.count(), 2)
        self.assertEqual(sum(s.amount for s in expense.shares.all()), D("100.00"))

    def test_payer_must_be_member(self):
        self.client.force_login(self.owner)
        self.client.post(self.create_url, self.post_data(paid_by=self.outsider.pk))
        self.assertEqual(Expense.objects.count(), 0)

    def test_outsider_gets_404(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.create_url).status_code, 404)


class ExpensePermissionTests(ExpenseTestBase):
    def test_creator_can_edit(self):
        expense = self.make_expense(self.member)
        url = reverse("expense_edit", args=[self.group.pk, expense.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_group_owner_can_edit(self):
        expense = self.make_expense(self.member)
        self.client.force_login(self.owner)
        url = reverse("expense_edit", args=[self.group.pk, expense.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_other_member_cannot_edit_or_delete(self):
        expense = self.make_expense(self.member)
        self.client.force_login(self.third)
        edit = reverse("expense_edit", args=[self.group.pk, expense.pk])
        delete = reverse("expense_delete", args=[self.group.pk, expense.pk])
        self.assertEqual(self.client.get(edit).status_code, 403)
        self.assertEqual(self.client.post(delete).status_code, 403)
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())

    def test_edit_recomputes_shares(self):
        expense = self.make_expense(self.owner)
        url = reverse("expense_edit", args=[self.group.pk, expense.pk])
        self.client.post(url, self.post_data(amount="90.00"))
        expense.refresh_from_db()
        self.assertEqual(expense.amount, D("90.00"))
        self.assertEqual(set(s.amount for s in expense.shares.all()), {D("30.00")})

    def test_delete(self):
        expense = self.make_expense(self.owner)
        url = reverse("expense_delete", args=[self.group.pk, expense.pk])
        self.client.post(url)
        self.assertFalse(Expense.objects.exists())


class MemberWithExpensesTests(ExpenseTestBase):
    def test_member_with_expenses_cannot_leave(self):
        self.make_expense(self.owner)
        self.client.force_login(self.member)
        self.client.post(reverse("group_leave", args=[self.group.pk]))
        self.assertTrue(self.group.memberships.filter(user=self.member).exists())

    def test_member_with_expenses_cannot_be_removed(self):
        self.make_expense(self.owner)
        membership = self.group.memberships.get(user=self.member)
        self.client.force_login(self.owner)
        self.client.post(reverse("member_remove", args=[self.group.pk, membership.pk]))
        self.assertTrue(self.group.memberships.filter(user=self.member).exists())