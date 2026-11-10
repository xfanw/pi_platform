from django.urls import path

from cycles.app_views.inventory_sap_parts import *

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
