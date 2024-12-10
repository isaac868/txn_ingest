from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.dispatch import receiver
from django.db.models.signals import pre_delete


class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    priority = models.IntegerField()

    class Meta:
        ordering = ["priority"]
        verbose_name_plural = "Categories"
        constraints = [models.UniqueConstraint(fields=["name", "user"], name="unique_category_rule_name")]

    @staticmethod
    def get_uncategorized(current_user):
        return Category.objects.get_or_create(user=current_user, name="Uncategorized", defaults={"priority": -1, "parent": None})[0]

    def __str__(self):
        return self.name


class Bank(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "user"], name="unique_bank_name")]

    def __str__(self):
        return self.name


class Account(models.Model):
    ACCOUNT_TYPES = {"savings": "Savings", "credit": "Credit", "chequing": "Chequing"}
    CURRENCY_CHOICES = {"cad": "CAD", "usd": "USD", "eur": "EUR"}
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES, default="chequing")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="cad")

    def __str__(self):
        return self.name


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    description = models.CharField(max_length=300)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.DO_NOTHING)
    category_override = models.BooleanField()
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.FloatField()

    class Meta:
        ordering = ["date", "description"]

    def __str__(self):
        return self.description


@receiver(pre_delete, sender=User)
def delete_uncategorized(sender, **kwargs):
    deleted_user = kwargs["instance"]
    Category.objects.filter(user=deleted_user).delete()


@receiver(pre_delete, sender=Category)
def assign_uncategorized(sender, **kwargs):
    category = kwargs["instance"]
    category.transaction_set.update(category=Category.get_uncategorized(category.user))


class ParseRule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    date_fmt_str = models.CharField(max_length=30)
    csv_delim = models.CharField(default=",", blank=True, max_length=1)
    start_line = models.IntegerField(default=0, blank=True, validators=[MinValueValidator(0)])
    date_col = models.IntegerField(validators=[MinValueValidator(0)])
    desc_col = models.IntegerField(validators=[MinValueValidator(0)])
    sub_desc_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    amount_col = models.IntegerField(validators=[MinValueValidator(0)])
    txn_type_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    negate_amount = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name", "user"], name="unique_parse_rule_name")]

    def __str__(self):
        return self.name


class CategoryRule(models.Model):
    OPERATOR_CHOICES = [("equals", "Equals"), ("contains", "Contains"), ("regex", "Regex"), ("starts_with", "Starts with"), ("ends_with", "Ends with")]
    match_text = models.CharField(max_length=50)
    match_type = models.CharField(max_length=50, choices=OPERATOR_CHOICES, default="contains")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="rule_set")

    def __str__(self):
        return f"If {self.match_type} {self.match_text} assign {self.category.name} category"
