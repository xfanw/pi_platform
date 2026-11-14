from cycles.app_urls.cycle_urls import urlpatterns as cycle_urls
from cycles.app_urls.inventory_urls import urlpatterns as parts_urls

app_name = "cycles"

urlpatterns = cycle_urls + parts_urls
