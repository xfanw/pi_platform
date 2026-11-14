from django.urls import path

from count.app_views.input_manual import count_manual, count_manual_create
from count.app_views.input_tag import count_tag, count_tag_create

urlpatterns = [
    path("count_manual", count_manual, name="count_manual"),
    path("count_manual_create", count_manual_create, name="count_manual_create"),
]

urlpatterns += [
    path("count_tag", count_tag, name="count_tag"),
    path("count_tag_create", count_tag_create, name="count_tag_create"),
]
