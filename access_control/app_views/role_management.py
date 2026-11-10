################################################################################
#     role_list
#     role_detail
#     save_role_info
#     add_role_access
#     remove_role_access
################################################################################

from core._imports_for_views import *
from access_control.models import RoleAction, RoleApp, RoleGroup
from access_control.app_functions import is_global_manager, is_plant_manager

PERMISSION = "Admin.Role & Permissions"


@login_required
def role_list(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view roles. {msg}"))
        return redirect("core:home")

    context["role_list"] = RoleGroup.objects.all().order_by("group_order")
    return render(request, "access_control/role_list.html", context)


@login_required
def role_detail(request, role_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view role details. {msg}"))
        return redirect("access_control:role_list")

    selected_role = request.session.get("selected_role_id")
    can_manage = False
    if is_global_manager(curr_user) or is_plant_manager(curr_user, plant, role_name=selected_role):
        target_role = RoleGroup.objects.filter(id=role_id).first()
        if not target_role:
            messages.error(request, f"Selected role does NOT exist. ")
            return redirect("access_control:role_list")
        context["target_role"] = target_role
        target_role_app = RoleAction.objects.filter(role=target_role.group_name)
        context["target_role_app_list"] = RoleAction.objects.filter(role=target_role.group_name).order_by("access_page__app_order")
        context["available_app_list"] = list(
            RoleApp.objects.exclude(app_name__in=target_role_app.values_list("access_page_id")).order_by("app_order")
        )
    return render(request, "access_control/role_detail.html", context)


@login_required
def save_role_info(request, role_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        return json_error(f"You do NOT have permission to edit role info. {msg}")

    curr_role = RoleGroup.objects.filter(id=role_id).first()
    if not curr_role:
        return json_error("Role Not Found. ")

    post_data = request.POST

    curr_role.role_scope = post_data.get("role_scope", "").strip()
    curr_role.role_holder = post_data.get("role_holder", "").strip()
    curr_role.description = post_data.get("description", "").strip()
    curr_role.save()
    # TODO: Keep Log
    return json_success(f"Role {curr_role.group_name} is updated successfully. ")


@login_required
def add_role_access(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        return json_error("No Plant is available in your approved scope.")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        return json_error(f"You do NOT have permission to edit role access. {msg}")

    post_data = request.GET

    group_name = post_data.get("group_name", "").strip()
    app_name = post_data.get("app_name", "").strip()
    can_edit = post_data.get("can_edit", "") == "true"
    RoleAction.objects.update_or_create(
        role=group_name,
        access_page_id=app_name,
        defaults={"can_edit": can_edit},
    )
    # TODO: Keep Log
    return json_success(f"Role {group_name} is updated successfully. ")


@login_required
def remove_role_access(request, role_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        return json_error("No Plant is available in your approved scope.")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        return json_error(f"You do NOT have permission to edit role access. {msg}")

    post_data = request.GET
    group_name = post_data.get("group_name", "").strip()
    role_action = RoleAction.objects.filter(id=role_id).first()
    if not role_action:
        return json_error("Role access does NOT exist. ")

    group_name = role_action.role
    # TODO: Keep Log
    role_action.delete()

    return json_success(f"Role {group_name} is updated successfully. ")
