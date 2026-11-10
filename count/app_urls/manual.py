from django.urls import path
from count.app_views.manual import *

urlpatterns = [
    path("count_manual_view", count_manual_view, name="count_manual_view"),
]
