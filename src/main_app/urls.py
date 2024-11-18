from django.urls import path

from . import views

urlpatterns = [
    path("parse-rules/", views.parse_rules, name="parse_rules"),
    path("upload/", views.upload, name="upload")
]