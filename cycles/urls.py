from cycles.app_urls.cycle_urls import urlpatterns as cycle_urls
from cycles.app_urls.cycle_tag_urls import urlpatterns as tag_urls
from cycles.app_urls.inventory_parts_urls import urlpatterns as parts_urls
from cycles.app_urls.inventory_ex_parts_urls import urlpatterns as ex_part_urls
from cycles.app_urls.inventory_sap_parts_urls import urlpatterns as sap_part_urls

app_name = "cycles"

urlpatterns = cycle_urls + tag_urls + parts_urls + ex_part_urls + sap_part_urls
