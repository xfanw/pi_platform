from django.urls import path

from cycles.app_views.inventory_parts import (
    part_setup,
    part_create,
    part_update,
    part_template_download,
    part_file_upload,
    part_batch,
    part_batch_confirm,
)

from cycles.app_views.inventory_sap_parts import (
    sap_part_setup,
    sap_part_create,
    sap_part_update,
    sap_part_template_download,
    sap_part_file_upload,
    sap_part_batch,
    sap_part_batch_confirm,
)
from cycles.app_views.inventory_ex_parts import (
    ex_part_setup,
    ex_part_create,
    ex_part_delete,
    ex_part_template_download,
    ex_part_file_upload,
    ex_part_batch,
    ex_part_batch_confirm,
)

# Parts
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

# SAP Parts
urlpatterns = [
    path("sap_part_setup", sap_part_setup, name="sap_part_setup"),
    path("sap_part_create", sap_part_create, name="sap_part_create"),
    path("sap_part_update/<int:line_id>", sap_part_update, name="sap_part_update"),
]

urlpatterns += [
    path("sap_part_template_download", sap_part_template_download, name="sap_part_template_download"),
    path("sap_part_file_upload", sap_part_file_upload, name="sap_part_file_upload"),
    path("sap_part_batch/<int:batch_id>", sap_part_batch, name="sap_part_batch"),
    path("sap_part_batch_confirm/<int:batch_id>", sap_part_batch_confirm, name="sap_part_batch_confirm"),
]

# Excluded Parts
urlpatterns += [
    path("ex_part_setup", ex_part_setup, name="ex_part_setup"),
    path("ex_part_create", ex_part_create, name="ex_part_create"),
    path("ex_part_delete/<int:ex_part_id>", ex_part_delete, name="ex_part_delete"),
]

urlpatterns += [
    path("ex_part_template_download", ex_part_template_download, name="ex_part_template_download"),
    path("ex_part_file_upload", ex_part_file_upload, name="ex_part_file_upload"),
    path("ex_part_batch/<int:batch_id>", ex_part_batch, name="ex_part_batch"),
    path("ex_part_batch_confirm/<int:batch_id>", ex_part_batch_confirm, name="ex_part_batch_confirm"),
]
