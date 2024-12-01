from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("parse-rules/", views.parse_rules, name="parse_rules"),
    path("category-rules/", views.category_rules, name="category_rules"),
    path("upload/", views.UploadView.as_view(), name="upload"),
    path("transactions/", views.TransactionView.as_view(), name="transactions"),
    path("accounts/login/", auth_views.LoginView.as_view(next_page="upload", extra_context={"login_page": True}), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/register/", views.register, name="register"),
]
