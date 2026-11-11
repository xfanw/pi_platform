from count.app_urls.manual import urlpatterns as manual_urls
from count.app_urls.pending import urlpatterns as pending_urls

app_name = "count"

urlpatterns = []
urlpatterns += manual_urls
urlpatterns += pending_urls
