import csv
import io
from datetime import datetime
from django import forms
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from .models import ParseRule, Category


class ParseRuleForm(forms.ModelForm):
    class Meta:
        model = ParseRule
        exclude = ["user"]
        labels = {
            "name": "Name *",
            "date_fmt_str": "Date format string *",
            "csv_delim": "CSV delimiter",
            "start_line": "CSV start line",
            "date_col": "Date column *",
            "desc_col": "Description column",
            "sub_desc_col": "Sub-description column",
            "amount_col": "Amount column *",
            "txn_type_col": "Credit/Debit indicator",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"


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

        self.validate_upload(io.TextIOWrapper(cleaned_data["file"], encoding="utf-8"), cleaned_data["choice"])
        return cleaned_data

    @staticmethod
    def evaluate_rule(rule, description_text):
        match rule.match_type:
            case "equals":
                return rule.match_text.lower() == description_text.lower()
            case "contains":
                return rule.match_text.lower() in description_text.lower()
            case "regex":
                return re.search(rule.match_text, description_text) is not None
            case "starts_with":
                return description_text.lower().startswith(rule.match_text.lower())
            case "ends_with":
                return description_text.lower().endswith(rule.match_text.lower())

    @staticmethod
    def get_category(description_text):
        for category in Category.objects.all():
            if any(FileSelectForm.evaluate_rule(rule, description_text) for rule in category.rule_set.all()):
                return category
        return None

    def validate_upload(self, file, choice_idx):
        """Validate the uploaded file given the selected parse rule. choice_idx corresponds to the pk of the parse rule."""

        row_index = 0
        try:
            try:
                parse_rule = ParseRule.objects.get(pk=choice_idx)
            except ParseRule.DoesNotExist:
                raise ValidationError("The parse rule %(rule)s does not exist.", params={"rule": self.choice.label}, code="internal_error")

            csv_rows = [["id", "date", "desc", "cat", "amt"]]
            reader = csv.reader(file)
            if parse_rule.start_line:
                for x in range(parse_rule.start_line):
                    next(reader)
                row_index = parse_rule.start_line

            csv_col_num = 0
            for row in reader:
                # Check all rows have same number of columns
                if csv_col_num != len(row) and csv_col_num != 0:
                    raise ValidationError(
                        "Error, number of CSV columns on line %(line)s does not match other rows.", params={"line": row_index}, code="input_error"
                    )
                csv_col_num = len(row)

                # Check date, will raise ValueError if parsing fails
                try:
                    datetime.strptime(row[parse_rule.date_col], parse_rule.date_fmt_str)
                except ValueError:
                    raise ValidationError("Error parsing time on %(line)s.", params={"line": row_index}, code="input_error")

                # Check the column pointed to by amount_col is actually a number
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
                        FileSelectForm.get_category(description).pk if FileSelectForm.get_category(description) else -1,
                        row[parse_rule.amount_col],
                    ]
                )
                row_index += 1

            with default_storage.open(f"uploads/{self.user.pk}", "w") as file:
                writer = csv.writer(file)
                writer.writerows(csv_rows)
        except ValidationError:
            raise
        except IndexError:
            raise ValidationError("Indexing error present on line %(line)s.", params={"line": row_index}, code="input_error")
        except Exception as e:
            raise ValidationError("Internal server error.", code="internal_error")
