from django.shortcuts import render
import csv
import json
import os
import requests
from datetime import datetime
from django.views import View
from django.shortcuts import redirect
from django.forms import inlineformset_factory
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, F
from django.contrib.auth import login, forms as auth_forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.storage import default_storage
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from .models import ParseRule, CategoryRule, Category, Transaction, Account, Bank
from .forms import ParseRuleForm, FileSelectForm, CategoryForm, AccountForm, AccountFormset, BankForm, CategoryJsonFileForm
from .common import get_category, get_user_categorization_dicts


@login_required
def dashboard(request):
    superset_host = os.getenv("SUPERSET_HOST", "")
    superset_port = os.getenv("SUPERSET_PORT", "")
    superset_username = os.getenv("SUPERSET_USERNAME", "")
    superset_pass = os.getenv("SUPERSET_PASSWORD", "")
    superset_api_endpoint = f"{superset_host}:{superset_port}/api/v1/"
    session = requests.Session()

    resp = session.post(superset_api_endpoint + "security/login", json={"username": superset_username, "password": superset_pass, "provider": "db"})
    access_token = resp.json()["access_token"]

    resp = session.get(superset_api_endpoint + "security/csrf_token", headers={"Authorization": f"Bearer {access_token}"})
    csrf_token = resp.json()["result"]

    resp = session.get(superset_api_endpoint + "dashboard/", headers={"Authorization": f"Bearer {access_token}"})
    dashboards = resp.json()["result"]
    dashboard_id = None
    for dashboard in dashboards:
        if dashboard["dashboard_title"] == "expenses_dashboard":
            dashboard_id = dashboard["id"]
            break

    resp = session.get(superset_api_endpoint + "dataset/", headers={"Authorization": f"Bearer {access_token}"})
    datasets = resp.json()["result"]
    dataset_id = None
    for dataset in datasets:
        if dataset["table_name"] == "expenses_dataset":
            dataset_id = dataset["id"]
            break

    body = {
        "resources": [{"id": f"{dashboard_id}", "type": "dashboard"}],
        "rls": [{"clause": f"user_id={request.user.pk}", "dataset": dataset_id}],
        "user": {"first_name": request.user.username, "last_name": request.user.username, "username": request.user.username},
    }
    resp = session.post(
        superset_api_endpoint + "security/guest_token", headers={"Authorization": f"Bearer {access_token}", "X-CSRFToken": csrf_token}, json=body
    )

    uuid_resp = session.get(superset_api_endpoint + f"dashboard/{dashboard_id}" + "/embedded", headers={"Authorization": f"Bearer {access_token}"})

    return render(request, "dashboard.html", {"guest_token": resp.json()["token"], "db_uuid": uuid_resp.json()["result"]["uuid"]})


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
        return render(request, "upload.html", {"form": FileSelectForm(user=request.user)})

    def post(self, request):
        if "preview-upload" in request.POST:
            form = FileSelectForm(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                return redirect(reverse("upload_preview"))
            else:
                return render(request, "upload.html", {"form": form})


class UploadPreviewView(LoginRequiredMixin, View):
    def get(self, request):
        if default_storage.exists(f"{request.user.pk}"):
            # "getTxnData" set during tabulator ajax query
            if "getTxnData" in request.GET and default_storage.exists(f"{request.user.pk}"):
                with default_storage.open(f"{request.user.pk}", "r") as file:
                    reader = csv.DictReader(file)
                    table_data = []
                    for row in reader:
                        row["cat"] = Category.objects.get(pk=row["cat"]).name
                        row["accnt"] = Account.objects.get(pk=row["accnt"]).name
                        table_data.append(row)
                    return JsonResponse(table_data, safe=False)
            else:
                categories = [(cat.pk, cat.name) for cat in Category.objects.filter(user=request.user)]
                return render(
                    request,
                    "tables.html",
                    {
                        "override_values": categories,
                        "row_select_title": "Ommit",
                        "confirm_btn_txt": "Upload Tansactions",
                        "page_url": reverse("upload_preview"),
                    },
                )
        else:
            return redirect(reverse("upload"))

    def post(self, request):
        change_data = json.loads(request.body)
        if "cancel" not in change_data and default_storage.exists(f"{request.user.pk}"):
            with default_storage.open(f"{request.user.pk}", "r") as file:
                reader = csv.DictReader(file)

                categories_dict = {category.pk: category for category in Category.objects.filter(user=request.user)}
                accounts_dict = {account.pk: account for account in Account.objects.filter(bank__user=request.user)}
                categorization_dicts = get_user_categorization_dicts(request.user)
                txns = []
                row_idx = 0

                for row in reader:
                    if row_idx in change_data["deleted"]:
                        row_idx += 1
                        continue

                    # Change the category if it was overridden
                    cat = categories_dict.get(int(row["cat"]))
                    cat_o = False
                    if str(row_idx) in change_data["changes"]:
                        if change_data["changes"][str(row_idx)]["override"]:
                            cat = categories_dict.get(change_data["changes"][str(row_idx)]["category"])
                        else:
                            cat = get_category(categorization_dicts, row["desc"])
                        cat_o = change_data["changes"][str(row_idx)]["override"]

                    txn = Transaction(
                        user=request.user,
                        date=datetime.fromisoformat(row["date"]),
                        description=row["desc"],
                        category=cat,
                        account=accounts_dict.get(int(row["accnt"])),
                        amount=row["amnt"],
                        category_override=cat_o,
                    )
                    txns.append(txn)
                    row_idx += 1
                Transaction.objects.bulk_create(txns)
            # if "cancel-upload" in request.POST: Nothing to do, just redirect and delete cached file

        default_storage.delete(f"{request.user.pk}")
        return redirect(reverse("upload"))


@login_required
def category_rules(request):
    CategoryFormset = inlineformset_factory(User, Category, form=CategoryForm, exclude=["user"], min_num=1, extra=0, can_delete=True)
    RuleFormset = inlineformset_factory(Category, CategoryRule, extra=1, exclude=[], can_delete=True)

    filtered_queryset = Category.objects.exclude(pk=Category.get_uncategorized(request.user).pk)
    category_formset = CategoryFormset(instance=request.user, queryset=filtered_queryset, form_kwargs={"user": request.user})
    upload_form = CategoryJsonFileForm()
    rule_formsets = [RuleFormset(instance=category_form.instance, prefix=f"{category_form.prefix}-rule_set") for category_form in category_formset]
    categoryIsValid = [True for _ in category_formset]

    if request.method == "POST" and "save-changes" in request.POST:
        category_formset = CategoryFormset(request.POST, instance=request.user, queryset=filtered_queryset, form_kwargs={"user": request.user})
        rule_formsets = [
            RuleFormset(request.POST, instance=category_form.instance, prefix=f"{category_form.prefix}-rule_set") for category_form in category_formset
        ]
        upload_form = CategoryJsonFileForm(request.POST, request.FILES)
        if category_formset.is_valid() and upload_form.is_valid() and all(formset.is_valid() for formset in rule_formsets):
            # Load JSON file if provided
            if upload_form.cleaned_data["json_file"] and hasattr(upload_form, "json_data"):
                cats = []
                rules = []
                for json_entry in upload_form.json_data:
                    new_category = Category(user=request.user, name=json_entry["name"], priority=json_entry["priority"], parent=None)
                    cats.append(new_category)
                    for rule in json_entry["rules"]:
                        rules.append(CategoryRule(category=new_category, match_type=rule["match_type"], match_text=rule["match_text"]))
                Category.objects.bulk_create(cats, update_conflicts=True, update_fields=["priority", "parent"], unique_fields=["name", "user"])
                CategoryRule.objects.bulk_create(rules)

            # Save cateogries and rules
            category_formset.save()
            for category_form, rule_formset in zip(category_formset, rule_formsets):
                if not category_form in category_formset.deleted_forms:
                    rule_formset.instance = category_form.instance
                    rule_formset.save()

            # Update transactions with new categories
            txns = Transaction.objects.filter(Q(user=request.user) & Q(category_override=False))
            categorization_dicts = get_user_categorization_dicts(request.user)
            for txn in txns:
                txn.category = get_category(categorization_dicts, txn.description)
            Transaction.objects.bulk_update(txns, ["category"])

            return redirect(reverse(category_rules))
        categoryIsValid = [(category_form.is_valid() and rule_formset.is_valid()) for category_form, rule_formset in zip(category_formset, rule_formsets)]
    # if "cancel-changes" in request.POST: Nothing to do, just redirect

    if "getJson" in request.GET:
        jsonOuput = []
        for cat in Category.objects.filter(Q(user=request.user) & ~Q(pk=Category.get_uncategorized(request.user).pk)):
            jsonOuput.append(
                {
                    "name": cat.name,
                    "priority": cat.priority,
                    "rules": [{"match_type": rule.match_type, "match_text": rule.match_text} for rule in cat.rule_set.all()],
                }
            )
        return HttpResponse(
            json.dumps(jsonOuput, indent=2),
            headers={
                "Content-Type": "application/json",
                "Content-Disposition": 'attachment; filename="categories.json"',
            },
        )
    else:
        context = {"category_formset": category_formset, "zipped_lists": zip(category_formset, rule_formsets, categoryIsValid), "upload_form": upload_form}
        return render(request, "category_rules.html", context)


@login_required
def accounts(request):
    BankFormset = inlineformset_factory(User, Bank, form=BankForm, exclude=["user"], extra=1, can_delete=True)
    AccountFormset_ = inlineformset_factory(Bank, Account, formset=AccountFormset, form=AccountForm, extra=1, can_delete=True)

    bank_formset = BankFormset(instance=request.user, form_kwargs={"user": request.user})
    account_formsets = [AccountFormset_(instance=bank_form.instance, prefix=f"{bank_form.prefix}-account_set", bank=bank_form) for bank_form in bank_formset]
    bankIsValid = [True for _ in bank_formset]

    if request.method == "POST" and "save-changes" in request.POST:
        bank_formset = BankFormset(request.POST, instance=request.user, form_kwargs={"user": request.user})
        account_formsets = [
            AccountFormset_(request.POST, instance=bank_form.instance, prefix=f"{bank_form.prefix}-account_set", bank=bank_form) for bank_form in bank_formset
        ]
        if bank_formset.is_valid() and all(formset.is_valid() for formset in account_formsets):
            bank_formset.save()
            for bank_form, account_formset in zip(bank_formset, account_formsets):
                account_formset.instance = bank_form.instance
                account_formset.save()
            return redirect(reverse(accounts))
        bankIsValid = [
            (bank_form.is_valid() and account_formset.is_valid() and (bank_form.instance.pk != None))
            for bank_form, account_formset in zip(bank_formset, account_formsets)
        ]

    context = {"bank_formset": bank_formset, "zipped_lists": zip(bank_formset, account_formsets, bankIsValid)}
    return render(request, "accounts.html", context)


class TransactionView(LoginRequiredMixin, View):
    def get(self, request):
        # "getTxnData" set during tabulator ajax query
        if "getTxnData" in request.GET:
            txns = Transaction.objects.filter(user=request.user).values(
                "date", accnt=F("account__name"), amnt=F("amount"), cat=F("category__name"), desc=F("description"), cat_o=F("category_override"), idx=F("pk")
            )
            table_data = []
            for txn in txns:
                table_data.append(txn)
            return JsonResponse(table_data, safe=False)
        elif "getCsv" in request.GET:
            txns = Transaction.objects.filter(user=request.user).values("date", "account__name", "amount", "category__name", "description")
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
            writer = csv.writer(response)
            writer.writerow(["Date", "Account", "Description", "Category", "Amount"])
            for txn in txns:
                writer.writerow([txn["date"], txn["account__name"], txn["description"], txn["category__name"], txn["amount"]])
            return response
        else:
            categories = [(cat.pk, cat.name) for cat in Category.objects.filter(user=request.user)]
            return render(
                request,
                "tables.html",
                {
                    "override_values": categories,
                    "row_select_title": "Delete",
                    "confirm_btn_txt": "Save changes",
                    "page_url": reverse("transactions"),
                    "downloadable": True,
                },
            )

    def post(self, request):
        change_data = json.loads(request.body)
        if "cancel" in change_data:
            return HttpResponse(status=200)
        try:
            changed_txns = Transaction.objects.filter(Q(user=request.user) & Q(pk__in=[*change_data["changes"]]))
            categorization_dicts = get_user_categorization_dicts(request.user)
            for change_idx, change in change_data["changes"].items():
                changed_txn = changed_txns.get(pk=change_idx)
                if change["override"]:
                    changed_txn.category = Category.objects.filter(user=request.user).get(pk=change["category"])
                else:
                    changed_txn.category = get_category(categorization_dicts, changed_txn.description)
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
