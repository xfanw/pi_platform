from django.urls import path

from cycles.app_views.inventory_parts import *

urlpatterns = [
    path("part_setup", part_setup, name="part_setup"),
    path("part_create", part_create, name="part_create"),
    path("part_update/<int:part_id>", part_update, name="part_update"),
]

urlpatterns += [
    path("part_template_download", part_template_download, name="part_template_download"),
    path("part_file_upload", part_file_upload, name="part_file_upload"),
    path("part_batch/<int:batch_id>", part_batch, name="part_batch"),
    path("part_batch_confirm/<int:batch_id>", part_batch_confirm, name="part_batch_confirm"),
]
