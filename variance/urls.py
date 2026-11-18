from django.urls import path

from variance.app_views.by_part import add_comment, add_decision, variance_by_part
from variance.app_views.by_location import variance_by_location
from variance.app_views.live_report import variance_live_report

app_name = "variance"

urlpatterns = [
    path("variance_by_part", variance_by_part, name="variance_by_part"),
    path("add_comment", add_comment, name="add_comment"),
    path("add_decision", add_decision, name="add_decision"),
]

urlpatterns += [
    path("variance_by_location", variance_by_location, name="variance_by_location"),
]

urlpatterns += [
    path("variance_live_report", variance_live_report, name="variance_live_report"),
]
