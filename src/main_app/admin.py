from django.contrib import admin
from .models import ParseRule, Category, CategoryRule, UserData, Transaction

admin.site.register(ParseRule)
admin.site.register(Category)
admin.site.register(CategoryRule)
admin.site.register(UserData)
admin.site.register(Transaction)