from django.contrib.auth import views as auth_views
from django.urls import path

from .views import *

app_name = "core"

urlpatterns = [
    path("", home, name="home"),
    path("init_db", init_db, name="init_db"),
    path(
        "login",
        auth_views.LoginView.as_view(
            template_name="core/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("log_out", log_out, name="log_out"),
    path("signup", signup, name="signup"),
    path("select_plant", select_plant, name="select_plant"),
    path("select_role", select_role, name="select_role"),
]
