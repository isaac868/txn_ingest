from django.db import models
from django.core.validators import MinValueValidator

class ParseRule(models.Model):
    name = models.CharField(max_length=50)
    date_fmt_str = models.CharField(max_length=30)
    csv_delim = models.CharField(null=True, blank=True, max_length=1)
    start_line = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    date_col = models.IntegerField(validators=[MinValueValidator(0)])
    desc_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    sub_desc_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])
    amount_col = models.IntegerField(validators=[MinValueValidator(0)])
    txn_type_col = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0)])

    def __str__(self):
        return self.name