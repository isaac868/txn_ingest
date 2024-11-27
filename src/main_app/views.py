from django.shortcuts import render
import csv
from django.views import View
from django.shortcuts import redirect
from django.forms import inlineformset_factory
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth import login, forms as auth_forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import ParseRule, CategoryRule, Category, UserData
from .forms import ParseRuleForm, FileSelectForm


@login_required
def parse_rules(request):
    RuleFormset = inlineformset_factory(User, ParseRule, form=ParseRuleForm, extra=1, can_delete=True)

    rule_formset = RuleFormset(instance=request.user)
    if request.method == "POST":
        rule_formset = RuleFormset(request.POST, instance=request.user)
        if rule_formset.is_valid():
            rule_formset.save()
            return redirect(reverse(parse_rules))
    return render(request, "parse_rules.html", {"formset": rule_formset})


class UploadView(LoginRequiredMixin, View):
    def get(self, request):
        if "preview" in request.GET and default_storage.exists(f"uploads/{request.user.pk}"):
            with default_storage.open(f"uploads/{request.user.pk}", "r") as file:
                reader = csv.DictReader(file)
                table_data = []
                for row in reader:
                    table_data.append(row)
                return JsonResponse(table_data, safe=False)
        elif "uploaded-file" not in request.session or not default_storage.exists(f"uploads/{request.user.pk}"):
            return render(request, "upload.html", {"form": FileSelectForm(user=request.user)})
        else:
            return render(request, "upload_preview.html")

    def post(self, request):
        if "uploaded-file" not in request.session:
            form = FileSelectForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                request.session["uploaded-file"] = True
                return redirect(reverse("upload"))


def get_rule_formset(category_form, data=None):
    RuleFormset = inlineformset_factory(Category, CategoryRule, extra=1, exclude=[])
    if category_form.instance.pk:
        return RuleFormset(data, instance=category_form.instance, prefix=f"category-{category_form.instance.pk}")
    else:
        return RuleFormset(data, prefix=f"new-category-{category_form.prefix}")


@login_required
def category_rules(request):
    CategoryFormset = inlineformset_factory(User, Category, exclude=["user"], extra=1, can_delete=True)

    category_formset = CategoryFormset(instance=request.user)
    rule_formsets = [get_rule_formset(category_form) for category_form in category_formset]

    if request.method == "POST":
        category_formset = CategoryFormset(request.POST, instance=request.user)
        if category_formset.is_valid():
            rule_formsets = [get_rule_formset(category_form, request.POST) for category_form in category_formset]

            if all(formset.is_valid() for formset in rule_formsets):
                category_formset.save()
                for category_form, rule_formset in zip(category_formset, rule_formsets):
                    rule_formset.instance = category_form.instance
                    rule_formset.save()
                return redirect(reverse(category_rules))

    context = {"category_formset": category_formset, "zipped_lists": zip(category_formset, rule_formsets)}
    return render(request, "category_rules.html", context)


def register(request):
    auth_form = auth_forms.BaseUserCreationForm()
    if request.method == "POST":
        auth_form = auth_forms.BaseUserCreationForm(request.POST)
        if auth_form.is_valid():
            new_user = auth_form.save()
            UserData.objects.create(user=new_user)
            login(request, new_user)
            return redirect("upload")
    return render(request, "registration/register.html", {"form": auth_form})
