from site_setting.app_views.sys_set import (
    sys_set,
    sys_set_detail,
    change_system_list_settings,
)
from django.urls import path

urlpatterns = [
    path("sys_set", sys_set, name="sys_set"),
    path("sys_set_detail", sys_set_detail, name="sys_set_detail"),
    path("change_system_list_settings", change_system_list_settings, name="change_system_list_settings"),
]
