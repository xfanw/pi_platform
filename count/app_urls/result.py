from django.urls import path
from count.app_views.result_pending import pending_station, pending_part_create, pending_part_map, pending_part_reject
from count.app_views.result_results import count_result

urlpatterns = [
    path("pending_station", pending_station, name="pending_station"),
    path("pending_part_create", pending_part_create, name="pending_part_create"),
    path("pending_part_map", pending_part_map, name="pending_part_map"),
    path("pending_part_reject", pending_part_reject, name="pending_part_reject"),
]

urlpatterns += [
    path("count_result", count_result, name="count_result"),
]
