from django.urls import path
from count.app_views.manual import *

urlpatterns = [
    path("count_manual", count_manual, name="count_manual"),
    path("count_manual_create", count_manual_create, name="count_manual_create"),
]
