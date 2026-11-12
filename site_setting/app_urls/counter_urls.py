from django.urls import path
from site_setting.app_views.counter_roster import (
    counter_setup,
    counter_create,
    counter_status,
    counter_template_download,
    counter_file_upload,
    counter_batch,
    counter_batch_confirm,
)

urlpatterns = [
    path("counter_setup", counter_setup, name="counter_setup"),
    path("counter_create", counter_create, name="counter_create"),
    path("counter_status/<int:ct_id>", counter_status, name="counter_status"),
]

urlpatterns += [
    path("counter_template_download", counter_template_download, name="counter_template_download"),
    path("counter_file_upload", counter_file_upload, name="counter_file_upload"),
    path("counter_batch/<int:batch_id>", counter_batch, name="counter_batch"),
    path("counter_batch_confirm/<int:batch_id>", counter_batch_confirm, name="counter_batch_confirm"),
]
