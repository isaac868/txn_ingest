import os
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from main_app.forms import ParseRuleForm, FileSelectForm
from main_app.models import Account, Bank, ParseRule


class ParseRuleFormTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.bank1 = Bank.objects.create(user=self.user1, name="bnk")
        self.bank2 = Bank.objects.create(user=self.user2, name="bnk")
        self.account1 = Account.objects.create(bank=self.bank1, name="act", account_type="savings", currency="cad")
        self.account2 = Account.objects.create(bank=self.bank2, name="act", account_type="savings", currency="cad")

    def test_parse_rule_validation(self):
        good_data = {
            "user": self.user1,
            "account": self.account1.pk,
            "name": "good-parse-rule",
            "date_fmt_str": "%Y-%d-%m",
            "date_col": 0,
            "desc_col": 1,
            "amount_col": 3,
        }
        good_rule = ParseRuleForm(good_data, user=self.user1)
        # Check form accepts valid data
        self.assertTrue(good_rule.is_valid())

        bad_data = {
            "user": self.user1,
            "account": self.account2.pk,
            "name": "bad-parse-rule",
            "date_fmt_str": "%r-%t-%o",
            "date_col": 0,
            "desc_col": 0,
            "amount_col": 1,
            "sub_desc_col": 1,
            "txn_type_col": 1,
        }
        bad_rule = ParseRuleForm(bad_data, user=self.user1)
        # Check form is not valid
        self.assertFalse(bad_rule.is_valid())
        # Check individual field errors
        self.assertFormError(bad_rule, "account", "Select a valid choice. That choice is not one of the available choices.")
        self.assertFormError(bad_rule, None, "The same column index cannot be used more than once.")


class FileSelectFormTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.bank = Bank.objects.create(user=self.user1, name="bnk")
        self.account = Account.objects.create(bank=self.bank, name="act", account_type="savings", currency="cad")
        self.prule1 = ParseRule.objects.create(
            user=self.user1, account=self.account, name="prule1", date_fmt_str="%y-%d-%m", date_col=0, desc_col=1, amount_col=2
        )
        self.prule2 = ParseRule.objects.create(
            user=self.user2, account=self.account, name="prule2", date_fmt_str="%y-%d-%m", date_col=0, desc_col=1, amount_col=2
        )

    def test_only_user_prules_allowed(self):
        file_name = f"valid{self.prule1.date_fmt_str}{self.prule1.date_col}{self.prule1.desc_col}{self.prule1.amount_col}.csv"
        with open(f"{os.path.dirname(__file__)}/test_data/" + file_name, "rb") as valid_file:
            mock_file = SimpleUploadedFile(
                name=file_name,
                content=valid_file.read(),
                content_type="text/csv",
            )
            valid_form = FileSelectForm({"choice": self.prule1.pk}, {"file": mock_file}, user=self.user1)
            var = valid_form.is_valid()
            self.assertTrue(valid_form.is_valid())

            invalid_form = FileSelectForm({"choice": self.prule2.pk}, {"file": mock_file}, user=self.user1)
            self.assertFalse(invalid_form.is_valid())
            self.assertFormError(invalid_form, "choice", f"Select a valid choice. {self.prule2.pk} is not one of the available choices.")
