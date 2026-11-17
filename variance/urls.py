from django.urls import path

from variance.app_views.by_part import variance_by_part

app_name = "variance"

urlpatterns = [
    path("variance_by_part", variance_by_part, name="variance_by_part"),
]
