from django.urls import path

from cycles.app_views.cycle_tags import *

urlpatterns = [
    path("tag_setup", tag_setup, name="tag_setup"),
    path("tag_create", tag_create, name="tag_create"),
]

urlpatterns += [
    path("tag_template_download", tag_template_download, name="tag_template_download"),
    path("tag_file_upload", tag_file_upload, name="tag_file_upload"),
    path("tag_batch/<int:batch_id>", tag_batch, name="tag_batch"),
    path("tag_batch_confirm/<int:batch_id>", tag_batch_confirm, name="tag_batch_confirm"),
]
