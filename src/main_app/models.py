from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class ParseRule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    date_fmt_str = models.CharField(max_length=30)
    csv_delim = models.CharField(null=True, blank=True, max_length=1)
    start_line = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    date_col = models.IntegerField(validators=[MinValueValidator(0)])
    desc_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    sub_desc_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    amount_col = models.IntegerField(validators=[MinValueValidator(0)])
    txn_type_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["name"], name="unique_parse_rule_name")]

    def __str__(self):
        return self.name


class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    priority = models.IntegerField()

    class Meta:
        ordering = ["priority"]
        verbose_name_plural = "Categories"
        constraints = [models.UniqueConstraint(fields=["name"], name="unique_category_rule_name")]

    def __str__(self):
        return self.name


class CategoryRule(models.Model):
    OPERATOR_CHOICES = [("equals", "Equals"), ("contains", "Contains"), ("regex", "Regex"), ("starts_with", "Starts with"), ("ends_with", "Ends with")]
    match_text = models.CharField(max_length=50)
    match_type = models.CharField(max_length=50, choices=OPERATOR_CHOICES, default="contains")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="rule_set")

    def __str__(self):
        return f"If {self.match_type} {self.match_text} assign {self.category.name} category"


class UserData(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userdata')
    upload_file_path = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "User Data"

    def __str__(self):
        return self.user.username