from count.app_urls.input import urlpatterns as manual_urls
from count.app_urls.result import urlpatterns as pending_urls

app_name = "count"

urlpatterns = manual_urls + pending_urls
