from django.shortcuts import render
import csv
import json
from datetime import datetime
from django.views import View
from django.shortcuts import redirect
from django.forms import inlineformset_factory
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.contrib.auth import login, forms as auth_forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import ParseRule, CategoryRule, Category, Transaction, Account, Bank
from .forms import ParseRuleForm, FileSelectForm, CategoryForm
from .common import get_category


@login_required
def parse_rules(request):
    RuleFormset = inlineformset_factory(User, ParseRule, form=ParseRuleForm, extra=1, can_delete=True)

    rule_formset = RuleFormset(instance=request.user, form_kwargs={"user": request.user})
    if request.method == "POST":
        rule_formset = RuleFormset(request.POST, instance=request.user, form_kwargs={"user": request.user})
        if rule_formset.is_valid():
            rule_formset.save()
            return redirect(reverse(parse_rules))
    return render(request, "parse_rules.html", {"formset": rule_formset})


class UploadView(LoginRequiredMixin, View):
    def get(self, request):
        # "preview" set during tabulator ajax query
        if "preview" in request.GET and default_storage.exists(f"uploads/{request.user.pk}"):
            with default_storage.open(f"uploads/{request.user.pk}", "r") as file:
                reader = csv.DictReader(file)
                table_data = []
                for row in reader:
                    row["cat"] = Category.objects.get(pk=row["cat"]).name
                    row["act"] = Account.objects.get(pk=row["act"]).name
                    table_data.append(row)
                return JsonResponse(table_data, safe=False)
        elif "uploaded-file" in request.session and default_storage.exists(f"uploads/{request.user.pk}"):
            del request.session["uploaded-file"]
            return render(request, "upload_preview.html")
        else:
            return render(request, "upload.html", {"form": FileSelectForm(user=request.user)})

    def post(self, request):
        if "preview-upload" in request.POST:
            form = FileSelectForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                request.session["uploaded-file"] = True
            else:
                return render(request, "upload.html", {"form": form})
        else:
            if "save-upload" in request.POST:
                with default_storage.open(f"uploads/{request.user.pk}", "r") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        Transaction.objects.create(
                            user=request.user,
                            date=datetime.fromisoformat(row["date"]),
                            description=row["desc"],
                            category=(Category.objects.get(pk=row["cat"])),
                            account=(Account.objects.get(pk=row["act"])),
                            amount=row["amt"],
                            category_override=False,
                        )
            # if "cancel-upload" in request.POST: Nothing to do, just redirect

            default_storage.delete(f"uploads/{request.user.pk}")
        return redirect(reverse("upload"))


def get_rule_formset(category_form, data=None):
    RuleFormset = inlineformset_factory(Category, CategoryRule, extra=1, exclude=[])
    if category_form.instance.pk:
        return RuleFormset(data, instance=category_form.instance, prefix=f"category-{category_form.instance.pk}")
    else:
        return RuleFormset(data, prefix=f"new-category-{category_form.prefix}")


@login_required
def category_rules(request):
    CategoryFormset = inlineformset_factory(User, Category, form=CategoryForm, exclude=["user"], extra=1, can_delete=True)

    filtered_queryset = Category.objects.exclude(pk=Category.get_uncategorized(request.user).pk)
    category_formset = CategoryFormset(instance=request.user, queryset=filtered_queryset, form_kwargs={"user": request.user})
    rule_formsets = [get_rule_formset(category_form) for category_form in category_formset]

    if request.method == "POST":
        category_formset = CategoryFormset(request.POST, instance=request.user, queryset=filtered_queryset, form_kwargs={"user": request.user})
        if category_formset.is_valid():
            rule_formsets = [get_rule_formset(category_form, request.POST) for category_form in category_formset]

            if all(formset.is_valid() for formset in rule_formsets):
                category_formset.save()
                for category_form, rule_formset in zip(category_formset, rule_formsets):
                    rule_formset.instance = category_form.instance
                    rule_formset.save()
                for txn in Transaction.objects.filter(Q(user=request.user) & Q(category_override=False)):
                    txn.category = get_category(request.user, txn.description)
                    txn.save()
                return redirect(reverse(category_rules))

    context = {"category_formset": category_formset, "zipped_lists": zip(category_formset, rule_formsets)}
    return render(request, "category_rules.html", context)


def get_account_formset(bank_form, data=None):
    AccountFormset = inlineformset_factory(Bank, Account, extra=1, exclude=[])
    if bank_form.instance.pk:
        return AccountFormset(data, instance=bank_form.instance, prefix=f"bank-{bank_form.instance.pk}")
    else:
        return AccountFormset(data, prefix=f"new-bank-{bank_form.prefix}")


@login_required
def accounts(request):
    BankFormset = inlineformset_factory(User, Bank, exclude=["user"], extra=1, can_delete=True)

    bank_formset = BankFormset(instance=request.user)
    account_formsets = [get_account_formset(bank_form) for bank_form in bank_formset]

    if request.method == "POST":
        bank_formset = BankFormset(request.POST, instance=request.user)
        if bank_formset.is_valid():
            account_formsets = [get_account_formset(bank_form, request.POST) for bank_form in bank_formset]

            if all(formset.is_valid() for formset in account_formsets):
                bank_formset.save()
                for bank_form, account_formset in zip(bank_formset, account_formsets):
                    account_formset.instance = bank_form.instance
                    account_formset.save()
                return redirect(reverse(accounts))

    context = {"category_formset": bank_formset, "zipped_lists": zip(bank_formset, account_formsets)}
    return render(request, "category_rules.html", context)


class TransactionView(LoginRequiredMixin, View):
    def get(self, request):
        # "preview" set during tabulator ajax query
        if "preview" in request.GET:
            txns = Transaction.objects.filter(user=request.user).values(
                "pk", "account__name", "amount", "category__name", "description", "date", "category_override"
            )
            table_data = []
            for txn in txns:
                table_data.append(txn)
            return JsonResponse(table_data, safe=False)
        else:
            categories = [(cat.pk, cat.name) for cat in Category.objects.filter(user=request.user)]
            return render(request, "transactions.html", {"override_values": categories})

    def post(self, request):
        change_data = json.loads(request.body)
        try:
            changed_txns = Transaction.objects.filter(Q(user=request.user) & Q(pk__in=[item["pk"] for item in change_data["changes"]]))
            for change in change_data["changes"]:
                changed_txn = changed_txns.get(pk=change["pk"])
                if change["override"]:
                    changed_txn.category = Category.objects.filter(user=request.user).get(pk=change["category"])
                else:
                    changed_txn.category = get_category(request.user, changed_txn.description)
                changed_txn.category_override = change["override"]
                changed_txn.save()

            deleted_rows = change_data["deleted"]
            Transaction.objects.filter(Q(pk__in=deleted_rows) & Q(user=request.user)).delete()
            return HttpResponse(status=200)
        except Exception as e:
            return HttpResponse(status=400)


def register(request):
    auth_form = auth_forms.BaseUserCreationForm()
    if request.method == "POST":
        auth_form = auth_forms.BaseUserCreationForm(request.POST)
        if auth_form.is_valid():
            new_user = auth_form.save()
            login(request, new_user)
            return redirect("upload")
    return render(request, "registration/login.html", {"form": auth_form})
