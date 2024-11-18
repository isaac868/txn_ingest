import csv
import io
from datetime import datetime
from django import forms
from django.core.exceptions import ValidationError
from .models import ParseRule

class ParseRuleForm(forms.ModelForm):
    class Meta:
        model = ParseRule
        exclude = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = "form-control"

def get_rules():
    rules = list(ParseRule.objects.all())
    choices = []
    for rule in rules:
        choices.append((rule.pk, rule.name))
    return choices

class FileSelectForm(forms.Form):
    file = forms.FileField()
    choice = forms.ChoiceField(choices=get_rules)
    csv_rows = []
    
    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data
        
        self.validate_upload(io.TextIOWrapper(cleaned_data["file"], encoding='utf-8'), cleaned_data["choice"])
        return cleaned_data

    def validate_upload(self, file_contents, choice_idx):
        """Validate the uploaded file given the selected parse rule. choice_idx corresponds to the pk of the parse rule."""
        
        row_index = 0
        try:
            try:
                parse_rule = ParseRule.objects.get(pk=choice_idx)
            except ParseRule.DoesNotExist:
                raise ValidationError("The parse rule %(rule)s does not exist.", params={"rule": self.choice.label}, code="internal_error")
            reader = csv.reader(file_contents)

            for x in range(parse_rule.start_line):
                next(reader)

            row_index = parse_rule.start_line
            csv_col_num = 0
            for row in reader:
                #Check desc col, will raise IndexError if parsing fails
                if csv_col_num != len(row) and csv_col_num != 0:
                    raise ValidationError("Error, number of CSV columns on line %(line)s does not match other rows.", params={"line": row_index}, code="input_error")
                csv_col_num = len(row)
                
                #Check date, will raise ValueError if parsing fails
                try:
                    datetime.strptime(row[parse_rule.date_col], parse_rule.date_fmt_str)
                except ValueError:
                    raise ValidationError("Error parsing time on %(line)s.", params={"line": row_index}, code="input_error")

                #Check the column pointed to by amount_col is actually a number
                try:
                    float(row[parse_rule.amount_col])
                except ValueError:
                    raise ValidationError("The value (%(val)s) on line %(line)s column %(column)s is not a number. The amount column should only contain numbers", 
                                          params={"line": row_index, "column": parse_rule.amount_col, "val": row[parse_rule.amount_col]}, code="input_error")
                self.csv_rows.append(row)
                row_index += 1
        except ValidationError:
            raise
        except IndexError:
            raise ValidationError("Indexing error present on line %(line)s.", params={"line": row_index}, code="input_error")
        except:
            raise ValidationError("Internal server error.", code="internal_error")