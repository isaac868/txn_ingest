import csv
import io
import os
import json
from datetime import datetime
from jsonschema import validate
from django import forms
from django.conf import settings
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from .models import ParseRule, Category, Account, Bank
from .common import get_category, get_user_categorization_dicts


class ParseRuleForm(forms.ModelForm):
    class Meta:
        model = ParseRule
        exclude = ["user"]
        labels = {
            "name": "Name",
            "date_fmt_str": "Date format string",
            "csv_delim": "CSV delimiter",
            "start_line": "CSV start line",
            "date_col": "Date column",
            "desc_col": "Description column",
            "sub_desc_col": "Sub-description column",
            "amount_col": "Amount column",
            "txn_type_col": "Credit/Debit indicator",
            "negate_amount": "Negate Amount",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label_suffix = ""
        self.fields["account"].queryset = Account.objects.filter(bank__user=self.user)

    def clean(self):
        cleaned_data = super().clean()
        cols = [field_value for (field_name, field_value) in cleaned_data.items() if isinstance(field_value, int) and field_name.endswith("_col")]
        if len(cols) != len(set(cols)):
            raise ValidationError("The same column index cannot be used more than once.", code="input_error")
        return cleaned_data


class FileSelectForm(forms.Form):

    file = forms.FileField()
    choice = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["choice"].choices = {rule.pk: rule.name for rule in ParseRule.objects.filter(user=self.user)}

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        self.validate_upload(io.TextIOWrapper(cleaned_data["file"], encoding="utf-8-sig"), cleaned_data["choice"])
        return cleaned_data

    def validate_upload(self, file, choice_idx):
        """Validate the uploaded file given the selected parse rule. choice_idx corresponds to the pk of the parse rule."""

        row_index = 0
        try:
            try:
                parse_rule = ParseRule.objects.get(pk=choice_idx)
            except ParseRule.DoesNotExist:
                raise ValidationError("The parse rule %(rule)s does not exist.", params={"rule": self.choice.label}, code="internal_error")

            csv_rows = [["idx", "date", "desc", "cat", "amnt", "accnt"]]
            reader = csv.reader(file)
            if parse_rule.start_line:
                for x in range(parse_rule.start_line):
                    next(reader)
                row_index = parse_rule.start_line

            csv_col_num = 0
            categorization_dicts = get_user_categorization_dicts(self.user)
            for row in reader:
                # Check all rows have same number of columns
                if csv_col_num != len(row) and csv_col_num != 0:
                    raise ValidationError("Invalid CSV file, all rows must have the same number of columns.", params={"line": row_index}, code="input_error")
                csv_col_num = len(row)

                # Check date, will raise ValueError if parsing fails
                try:
                    datetime.strptime(row[parse_rule.date_col], parse_rule.date_fmt_str)
                except ValueError:
                    raise ValidationError("Error parsing date on line %(line)s.", params={"line": row_index}, code="input_error")

                # Check the column pointed to by amount_col is actually a number
                row[parse_rule.amount_col] = row[parse_rule.amount_col].replace("$", "").replace(",", "")
                try:
                    float(row[parse_rule.amount_col])
                except ValueError:
                    raise ValidationError(
                        "The value (%(val)s) on line %(line)s column %(column)s is not a number. The amount column should only contain numbers",
                        params={"line": row_index, "column": parse_rule.amount_col, "val": row[parse_rule.amount_col]},
                        code="input_error",
                    )

                description = row[parse_rule.desc_col].strip()
                if parse_rule.sub_desc_col:
                    description += " " + row[parse_rule.sub_desc_col].strip()
                csv_rows.append(
                    [
                        row_index,
                        datetime.strptime(row[parse_rule.date_col], parse_rule.date_fmt_str).isoformat(),
                        description,
                        get_category(categorization_dicts, description).pk,
                        float(row[parse_rule.amount_col]) * (-1 if parse_rule.negate_amount else 1),
                        parse_rule.account.pk,
                    ]
                )
                row_index += 1

            if not os.path.exists(settings.MEDIA_ROOT):
                os.makedirs(settings.MEDIA_ROOT)
            with default_storage.open(f"{self.user.pk}", "w") as file:
                writer = csv.writer(file)
                writer.writerows(csv_rows)
                file.close()
        except ValidationError:
            raise
        except IndexError:
            raise ValidationError("Indexing error present on line %(line)s.", params={"line": row_index}, code="input_error")
        except UnicodeDecodeError:
            raise ValidationError("The uploaded file contains invalid utf-8 bytes.", code="input_error")
        except Exception as e:
            raise ValidationError("Internal server error.", code="internal_error")


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        exclude = ["user"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            self.fields["parent"].queryset = Category.objects.filter(
                Q(user=self.user) & ~Q(pk=Category.get_uncategorized(self.user).pk) & ~Q(pk=self.instance.pk)
            )
        else:
            self.fields["parent"].queryset = Category.objects.filter(Q(user=self.user) & ~Q(pk=Category.get_uncategorized(self.user).pk))

    def clean_name(self):
        name = self.cleaned_data["name"]

        if name == Category.get_uncategorized(self.user).name:
            raise ValidationError("Category cannot be named %(cat)s", params={"cat": Category.get_uncategorized(self.user).name})
        if name in [cat.name for cat in Category.objects.filter(Q(user=self.user) & ~Q(pk=self.instance.pk))]:
            raise ValidationError("This category name is already in use", code="input_error")
        return name


class CategoryJsonFileForm(forms.Form):
    json_file = forms.FileField(required=False, label="Optional: JSON Rule File")

    def clean_json_file(self):
        json_file = self.cleaned_data["json_file"]
        if json_file:
            try:
                data = json_file.read().decode("utf-8")
                schema_path = os.path.join(settings.BASE_DIR, "main_app", "category_rule_schema.json")
                with open(schema_path, "r") as schema_file:
                    schema = json.load(schema_file)
                    self.json_data = json.loads(data)
                    validate(self.json_data, schema)
            except Exception as e:
                raise ValidationError("Invalid JSON file: %(schema_error)s", params={"schema_error": e.message}, code="input_error")
        return json_file


class BankForm(forms.ModelForm):
    class Meta:
        model = Bank
        exclude = ["user"]
        labels = {"name": "Bank Name"}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"]

        if name in [bank.name for bank in Bank.objects.filter(Q(user=self.user) & ~Q(pk=self.instance.pk))]:
            raise ValidationError("This bank name is already in use", code="input_error")
        return name


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        exclude = ["bank"]
        labels = {
            "name": "Account Name",
            "account_type": "Account Type",
            "currency": "Currency",
        }


class AccountFormset(forms.BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.bank = kwargs.pop("bank", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        if any(self.errors):
            return

        if self.bank.cleaned_data == {} and self.cleaned_data != [{}] and not self._should_delete_form(self.forms[0]):
            self.forms[0].add_error("name", "Cannot save an account without a named bank")
