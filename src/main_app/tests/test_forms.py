from django.test import TestCase
from django.contrib.auth.models import User
from main_app.forms import ParseRuleForm
from main_app.models import Account, Bank

class ParseRuleTests(TestCase):
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
        # Check defaults for optional fields
        self.assertEqual(good_rule.cleaned_data["csv_delim"], ",")
        self.assertEqual(good_rule.cleaned_data["start_line"], 0)
        self.assertEqual(good_rule.cleaned_data["sub_desc_col"], None)
        self.assertEqual(good_rule.cleaned_data["txn_type_col"], None)

        bad_data = {
            "user": self.user1,
            "account": self.account2.pk,
            "name": "bad-parse-rule",
            "date_fmt_str": "invalid string",
            "date_col": 0,
            "desc_col": 0,
            "amount_col": 1,
            "sub_desc_col": 1,
            "txn_type_col": 1,
        }
        bad_rule = ParseRuleForm(bad_data, user=self.user1)
        # Check form is not valid
        self.assertFalse(good_rule.is_valid())
        # Check individual field errors
        self.assertFormError(bad_rule, "account", "Select a valid choice. That choice is not one of the available choices.")
        self.assertFormError(bad_rule, "date_fmt_str", "Please provide a valid Python date format string.")
        self.assertFormError(bad_rule, None, ["The same column index cannot be used more than once." for i in range(5)])