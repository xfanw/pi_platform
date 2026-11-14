from django.urls import path

from count.app_views.input_manual import count_manual, count_manual_create, count_manual_update, count_manual_delete
from count.app_views.input_tag import count_tag, count_tag_create, count_tag_update
from count.app_views.input_batches import (
    count_batch,
    count_batch_confirm,
    count_upload,
    count_file_upload,
    count_template_download,
)

urlpatterns = [
    path("count_manual", count_manual, name="count_manual"),
    path("count_manual_create", count_manual_create, name="count_manual_create"),
    path("count_manual_update", count_manual_update, name="count_manual_update"),
    path("count_manual_delete/<int:id>", count_manual_delete, name="count_manual_delete"),
]

urlpatterns += [
    path("count_tag", count_tag, name="count_tag"),
    path("count_tag_create", count_tag_create, name="count_tag_create"),
    path("count_tag_update", count_tag_update, name="count_tag_update"),
]

urlpatterns += [
    path("count_upload", count_upload, name="count_upload"),
    path("count_template_download", count_template_download, name="count_template_download"),
    path("count_file_upload", count_file_upload, name="count_file_upload"),
    path("count_batch/<int:batch_id>", count_batch, name="count_batch"),
    path("count_batch_confirm/<int:batch_id>", count_batch_confirm, name="count_batch_confirm"),
]
