from django.contrib import admin
from .models import ParseRule, Category, CategoryRule, Transaction, Bank, Account

admin.site.register(ParseRule)
admin.site.register(Category)
admin.site.register(CategoryRule)
admin.site.register(Transaction)
admin.site.register(Bank)
admin.site.register(Account)
