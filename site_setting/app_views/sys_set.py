from core._imports_for_views import *
from site_setting.system_setting.sys_settings import SysSet
from core._imports_for_views import *
from core.app_functions import *

PERMISSION = "Admin.Dropdown Management"


@login_required
def change_system_settings(request):
    can_act, msg = check_permission(request.user, "Sys Setting", True)
    if not can_act:
        return json_error(msg)

    var_name = request.GET.get("var_name", "")
    var_value = request.GET.get("var_value", "")

    if not var_name or not var_value:
        return json_error("Invalid Input")

    sys_setting_ref = SysSet()
    sys_setting_ref.set_obj(var_name, var_value, request.user.username)
    return json_success("Value updated successfully. ")


@login_required
def change_system_list_settings(request):
    can_act, msg = check_permission(request.user, "Sys Setting", True)
    if not can_act:
        return json_error(msg)

    var_name = request.GET.get("var_name", "")
    var_action = request.GET.get("var_action", "")
    var_value = request.GET.get("var_value", "")
    user_name = request.user.username

    if not var_name or not var_value or not var_action:
        return json_error("Invalid Input")

    sys_setting_ref = SysSet()
    var_obj_val = sys_setting_ref.get_val(var_name)
    if var_action == "delete":
        if var_value not in var_obj_val:
            return json_error(f"Value {var_value} is not in {var_name}. ")
        sys_setting_ref.delete_list_val(var_name, var_value, user_name)

    if var_action == "add":
        if var_value in var_obj_val:
            return json_error(f"Value {var_value} is already in {var_name}. ")
        sys_setting_ref.add_list_val(var_name, var_value, user_name)

    return json_success("Value updated successfully. ")


@login_required
def change_system_dict_settings(request):
    can_act, msg = check_permission(request.user, "Sys Setting", True)
    if not can_act:
        return json_error(msg)

    var_name = request.GET.get("var_name", "")
    var_action = request.GET.get("var_action", "")
    var_key = request.GET.get("var_key", "")
    var_value = request.GET.get("var_value", "")
    user_name = request.user.username

    if not var_name or not var_key or not var_action:
        return json_error("Invalid Input")

    if "value" in var_action:
        if not var_value:
            return json_error("Invalid Input")

    sys_setting_ref = SysSet()
    var_obj_val = sys_setting_ref.get_val(var_name)

    if var_action == "delete_key":
        if var_key not in var_obj_val:
            return json_error(f"Key {var_key} is not in {var_name}. ")
        sys_setting_ref.delete_dict_key(var_name, var_key, user_name)

    if var_action == "add_key":
        if var_key in var_obj_val:
            return json_error(f"Key {var_key} is already in {var_name}. ")
        sys_setting_ref.add_dict_key(var_name, var_key, user_name)

    if var_action == "delete_value":
        if var_key not in var_obj_val:
            return json_error(f"Key {var_key} is not in {var_name}. ")
        if var_value not in var_obj_val[var_key]:
            return json_error(f"Value {var_value} is not in {var_name}[{var_key}]. ")
        sys_setting_ref.delete_dict_value(var_name, var_key, var_value, user_name)

    if var_action == "add_value":
        if var_key not in var_obj_val:
            return json_error(f"Key {var_key} is not in {var_name}. ")
        if var_value in var_obj_val[var_key]:
            return json_error(f"Value {var_value} is already in {var_name}[{var_key}]. ")
        sys_setting_ref.add_dict_value(var_name, var_key, var_value, user_name)

    if var_action == "edit_key_value_pair":
        if var_key not in var_obj_val:
            return json_error(f"Key {var_key} is not in {var_name}. ")
        sys_setting_ref.edit_dict_key_value(var_name, var_key, var_value, user_name)
    if var_action == "add_dict_key_value":
        if var_key in var_obj_val:
            return json_error(f"Key {var_key} is already in {var_name}. ")
        sys_setting_ref.add_dict_key_value(var_name, var_key, var_value, user_name)

    return json_success("Value updated successfully. ")


@login_required
def sys_set(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view System Setup. {msg}"))
        return redirect("core:home")

    context["pi_list"] = [
        SysSet().get_obj("PLANT_VAR_SUM_DEFAULT"),
        SysSet().get_obj("BUSINESS_ROLE"),
        SysSet().get_obj("SAP_INVENTORY_TYPE"),
        SysSet().get_obj("SAP_ENTRY_METHOD"),
        SysSet().get_obj("BUSINESS_OPTION_CATEGORY"),
        SysSet().get_obj("DEPARTMENTS"),
        SysSet().get_obj("CYCLE_STATUS"),
        SysSet().get_obj("ONBOARDING_STATUS"),
        SysSet().get_obj("COUNT_SOURCE"),
        SysSet().get_obj("COUNT_EXCEPTION_STATUS"),
    ]

    return render(request, "site_setting/sys_set_list.html", context)


@login_required
def sys_set_detail(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view System Setup. {msg}"))
        return redirect("core:home")

    var_name = request.GET.get("var_name", "")
    context["curr_list_details"] = SysSet().get_obj(var_name)

    return render(request, "site_setting/sys_set_list_detail.html", context)
