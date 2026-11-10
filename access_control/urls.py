from django.urls import path

from .views import *

app_name = "access_control"

# User Management
urlpatterns = [
    path("users", user_list, name="user_list"),
    path("create_user", create_user, name="create_user"),
    path("user_detail/<int:user_id>", user_detail, name="user_detail"),
    path("edit_user/<int:user_id>", edit_user, name="edit_user"),
    path("reset_password/<int:user_id>", reset_password, name="reset_password"),
    path("assign_user_role/<int:user_id>", assign_user_role, name="assign_user_role"),
    path("remove_user_role/<int:role_id>", remove_user_role, name="remove_user_role"),
]

# Role Management
urlpatterns += [
    path("role_list", role_list, name="role_list"),
    path("role_detail/<int:role_id>", role_detail, name="role_detail"),
    path("save_role_info/<int:role_id>", save_role_info, name="save_role_info"),
    path("add_role_access", add_role_access, name="add_role_access"),
    path("remove_role_access/<int:role_id>", remove_role_access, name="remove_role_access"),
]
