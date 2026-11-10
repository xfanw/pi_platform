from django.urls import path
from cycles.app_views.cycles import *

urlpatterns = [
    path("", cycles, name="cycles"),
    path("create_cycle", create_cycle, name="create_cycle"),
]
