from django.urls import path

from cycles.app_views.inventory_ex_parts import *

urlpatterns = [
    path("ex_part_setup", ex_part_setup, name="ex_part_setup"),
    path("ex_part_create", ex_part_create, name="ex_part_create"),
]

urlpatterns += [
    path("ex_part_template_download", ex_part_template_download, name="ex_part_template_download"),
    path("ex_part_file_upload", ex_part_file_upload, name="ex_part_file_upload"),
    path("ex_part_batch/<int:batch_id>", ex_part_batch, name="ex_part_batch"),
    path("ex_part_batch_confirm/<int:batch_id>", ex_part_batch_confirm, name="ex_part_batch_confirm"),
]
