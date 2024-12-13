from django.contrib import admin
from .models import ParseRule, Category, CategoryRule, Transaction, Bank, Account

class DisplayUserAdmin(admin.ModelAdmin):
    list_display = ["__str__", "user"]


class CategoryRuleAdmin(admin.ModelAdmin):
    list_display = ["__str__", "category__user"]

class AccountAdmin(admin.ModelAdmin):
    list_display = ["__str__", "bank__user"]

admin.site.register(ParseRule, DisplayUserAdmin)
admin.site.register(Category, DisplayUserAdmin)
admin.site.register(CategoryRule, CategoryRuleAdmin)
admin.site.register(Transaction, DisplayUserAdmin)
admin.site.register(Bank, DisplayUserAdmin)
admin.site.register(Account, AccountAdmin)
