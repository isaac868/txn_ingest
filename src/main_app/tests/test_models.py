from django.test import TestCase
from django.contrib.auth.models import User
from main_app.models import Account, Bank, Category, Transaction, ParseRule
from django.db import IntegrityError


class ModelTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.bank = Bank.objects.create(user=self.user1, name="bnk")
        self.account = Account.objects.create(bank=self.bank, name="act", account_type="savings", currency="cad")
        self.cat = Category.objects.create(user=self.user1, name="new", priority=1)
        self.txn = Transaction.objects.create(
            user=self.user1, date="2024-01-01", description="txn", category=self.cat, category_override=False, account=self.account, amount=0
        )
        self.parse_rule = ParseRule.objects.create(user=self.user1, account=self.account, name="prule", date_fmt_str="", date_col=0, desc_col=0, amount_col=0)

    def test_user_deletion(self):
        self.user1.delete()
        self.assertFalse(Bank.objects.filter(pk=self.bank.pk).exists())
        self.assertFalse(Account.objects.filter(pk=self.account.pk).exists())
        self.assertFalse(Category.objects.filter(pk=self.cat.pk).exists())
        self.assertFalse(Transaction.objects.filter(pk=self.txn.pk).exists())
        self.assertFalse(ParseRule.objects.filter(pk=self.parse_rule.pk).exists())

    def test_category_creation(self):
        Category.objects.create(user=self.user1, name="test", priority=1)
        Category.objects.create(user=self.user2, name="test", priority=1)
        self.assertRaises(IntegrityError, Category.objects.create, user=self.user1, name="test", priority=1)

    def test_uncategorized(self):
        uc1 = Category.get_uncategorized(self.user1)
        uc2 = Category.get_uncategorized(self.user2)
        self.assertNotEqual(uc1.pk, uc2.pk)
        self.assertEqual(uc1.name, uc2.name)

    def test_category_deletion(self):
        cat_pk = self.cat.pk
        self.cat.delete()
        self.assertFalse(Category.objects.filter(pk=cat_pk).exists())

        # Test that deletion assigns categorized txns to uncategorized
        self.txn.refresh_from_db()
        self.assertEqual(self.txn.category, Category.get_uncategorized(self.user1))

    def test_bank_creation(self):
        Bank.objects.create(user=self.user2, name="bnk")
        self.assertRaises(IntegrityError, Bank.objects.create, user=self.user1, name="bnk")

    def test_parse_rule_creation(self):
        ParseRule.objects.create(user=self.user2, account=self.account, name="prule", date_fmt_str="", date_col=0, desc_col=0, amount_col=0)
        self.assertRaises(
            IntegrityError, ParseRule.objects.create, user=self.user1, account=self.account, name="prule", date_fmt_str="", date_col=0, desc_col=0, amount_col=0
        )
