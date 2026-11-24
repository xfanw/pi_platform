from django.urls import path
from . import views

app_name = "audit"

urlpatterns = [
    path("", views.index, name="audit_index"),
]
