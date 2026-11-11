from django.urls import path
from count.app_views.pending import *

urlpatterns = [
    path("pending_station", pending_station, name="pending_station"),
]
