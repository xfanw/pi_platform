from django.urls import path

from site_setting.app_views.counter_roster import data_entry_setup

from .views import *

from site_setting.app_urls.counter_urls import urlpatterns as counter_urls
from site_setting.app_urls.location_urls import urlpatterns as location_urls
from site_setting.app_urls.plant_urls import urlpatterns as plant_urls
from site_setting.app_urls.sys_set_url import urlpatterns as sys_set_urls

app_name = "site_setting"

urlpatterns = [
    path("data_entry_setup", data_entry_setup, name="data_entry_setup"),
]

urlpatterns += counter_urls + location_urls + plant_urls + sys_set_urls
