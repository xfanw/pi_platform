from django.urls import path

from count.app_views.manual import count_manual, count_manual_create
from count.app_views.tag import count_tag_view

urlpatterns = [
    path("count_manual", count_manual, name="count_manual"),
    path("count_manual_create", count_manual_create, name="count_manual_create"),
]

urlpatterns += [
    path("count_tag_view", count_tag_view, name="count_tag_view"),
    # path("count_manual_create", count_manual_create, name="count_manual_create"),
]
