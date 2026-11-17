from django.urls import path

from variance.app_views.by_part import add_comment, add_decision, variance_by_part

app_name = "variance"

urlpatterns = [
    path("variance_by_part", variance_by_part, name="variance_by_part"),
    path("add_comment", add_comment, name="add_comment"),
    path("add_decision", add_decision, name="add_decision"),
]
