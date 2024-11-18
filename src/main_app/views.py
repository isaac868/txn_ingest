from django.shortcuts import render
import csv
import io
from datetime import datetime
from django.views import View
from django.shortcuts import redirect
from django.forms import modelformset_factory
from django.urls import reverse
from .models import ParseRule
from .forms import ParseRuleForm, FileSelectForm

def parse_rules(request):
    RuleFormset = modelformset_factory(ParseRule, form=ParseRuleForm, extra = 1, can_delete=True, can_order=True)

    rule_formset = RuleFormset()
    if request.method == "POST":
        rule_formset = RuleFormset(request.POST)
        if rule_formset.is_valid():
            rule_formset.save()
            return redirect(reverse(parse_rules))
    return render(request, "parse_rules.html", {"formset": rule_formset})
    
def upload(request):
    form = FileSelectForm()
    if request.method == "POST":
        form = FileSelectForm(request.POST, request.FILES)
        if form.is_valid():
            parse_rule = ParseRule.objects.get(pk=form.cleaned_data["choice"])
            table = []
            for row in form.csv_rows:
                date = datetime.strptime(row[parse_rule.date_col], parse_rule.date_fmt_str).isoformat()
                table.append([date, row[parse_rule.desc_col].strip(), row[parse_rule.amount_col]])
            return render(request, "upload_preview.html", {"table": table})

    return render(request, "upload.html", {"form": form})

class UploadView(View):
    def get(self, request):
        return render(request, "upload.html", {"form": FileSelectForm})
    
    def post(self, request):
        if("uploaded-file" not in request.session):
            form = FileSelectForm(request.POST, request.FILES)
            if form.is_valid():
                file = io.TextIOWrapper(request.FILES["file"].file, encoding='utf-8')
                reader = csv.reader(file)