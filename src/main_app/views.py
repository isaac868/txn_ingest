from django.shortcuts import render
import csv
import io
import re
from datetime import datetime
from django.views import View
from django.shortcuts import redirect
from django.forms import modelformset_factory, inlineformset_factory
from django.urls import reverse
from .models import ParseRule, CategoryRule, Category
from .forms import ParseRuleForm, FileSelectForm


def parse_rules(request):
    RuleFormset = modelformset_factory(ParseRule, form=ParseRuleForm, extra=1, can_delete=True)

    rule_formset = RuleFormset()
    if request.method == "POST":
        rule_formset = RuleFormset(request.POST)
        if rule_formset.is_valid():
            rule_formset.save()
            return redirect(reverse(parse_rules))
    return render(request, "parse_rules.html", {"formset": rule_formset})

def evaluate_rule(rule, description_text):
    match rule.match_type:
        case "equals":
            return rule.match_text.lower() == description_text.lower()
        case "contains":
            return rule.match_text.lower() in description_text.lower()
        case "regex":
            return re.search(rule.match_text, description_text) is not None

def get_category(description_text):
    for category in Category.objects.all():
        if any(evaluate_rule(rule, description_text) for rule in category.rule_set.all()):
            return category
    return None

def upload(request):
    form = FileSelectForm()
    if request.method == "POST":
        form = FileSelectForm(request.POST, request.FILES)
        if form.is_valid():
            parse_rule = ParseRule.objects.get(pk=form.cleaned_data["choice"])
            table = []
            for row in form.csv_rows:
                date = datetime.strptime(row[parse_rule.date_col], parse_rule.date_fmt_str).isoformat()
                category = get_category(row[parse_rule.desc_col]).name if get_category(row[parse_rule.desc_col]) else ""
                table.append([date, row[parse_rule.desc_col].strip(), row[parse_rule.amount_col], category])
            return render(request, "upload_preview.html", {"table": table})

    return render(request, "upload.html", {"form": form})


class UploadView(View):
    def get(self, request):
        return render(request, "upload.html", {"form": FileSelectForm})

    def post(self, request):
        if "uploaded-file" not in request.session:
            form = FileSelectForm(request.POST, request.FILES)
            if form.is_valid():
                file = io.TextIOWrapper(request.FILES["file"].file, encoding="utf-8")
                reader = csv.reader(file)


def get_rule_formset(category_form, data=None):
    RuleFormset = inlineformset_factory(Category, CategoryRule, extra=1, exclude=[])
    if category_form.instance.pk:
        return RuleFormset(data, instance=category_form.instance, prefix=f"category-{category_form.instance.pk}")
    else:
        return RuleFormset(data, prefix=f"new-category-{category_form.prefix}")


def category_rules(request):
    CategoryFormset = modelformset_factory(Category, exclude=[], extra=1, can_delete=True)

    category_formset = CategoryFormset()
    rule_formsets = [get_rule_formset(category_form) for category_form in category_formset]

    if request.method == "POST":
        category_formset = CategoryFormset(request.POST)
        if category_formset.is_valid():
            rule_formsets = []
            all_valid = True
            for category_form in category_formset:
                rule_formset = get_rule_formset(category_form, request.POST)
                rule_formsets.append(rule_formset)
                if not rule_formset.is_valid():
                    all_valid = False

            if all_valid:
                category_formset.save()
                for category_form, rule_formset in zip(category_formset, rule_formsets):
                    rule_formset.instance = category_form.instance
                    rule_formset.save()
                return redirect(reverse(category_rules))

    context = {"category_formset": category_formset, "zipped_lists": zip(category_formset, rule_formsets)}
    return render(request, "category_rules.html", context)
