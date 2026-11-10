from site_setting.app_views.location import *
from django.urls import path

urlpatterns = [
    path("location_setup", location_setup, name="location_setup"),
    path("create_location", create_location, name="create_location"),
    path("update_location/<slug:location_id>", update_location, name="update_location"),
]

urlpatterns += [
    path("location_template_download", location_template_download, name="location_template_download"),
    path("location_file_upload", location_file_upload, name="location_file_upload"),
    path("location_batch/<int:batch_id>", location_batch, name="location_batch"),
    path("location_batch_confirm/<int:batch_id>", location_batch_confirm, name="location_batch_confirm"),
]


urlpatterns += [
    path("sub_location_setup", sub_location_setup, name="sub_location_setup"),
    path("create_sub_location", create_sub_location, name="create_sub_location"),
    path("update_sub_location/<slug:sub_location_id>", update_sub_location, name="update_sub_location"),
]

urlpatterns += [
    path("sub_location_template_download", sub_location_template_download, name="sub_location_template_download"),
    path("sub_location_file_upload", sub_location_file_upload, name="sub_location_file_upload"),
    path("sub_location_batch/<int:batch_id>", sub_location_batch, name="sub_location_batch"),
    path("sub_location_batch_confirm/<int:batch_id>", sub_location_batch_confirm, name="sub_location_batch_confirm"),
]
