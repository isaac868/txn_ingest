from django.contrib import admin
from .models import ParseRule, Category, CategoryRule

admin.site.register(ParseRule)
admin.site.register(Category)
admin.site.register(CategoryRule)