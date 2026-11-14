from core._imports_for_views import *
from core.constants import TIME_ZONE_DICT
from cycles.app_functions.cycle import add_sap_location_to_cycle, remove_sap_location_from_cycle
from site_setting.models import Plant, SAPLocation
from site_setting.system_setting.sys_settings import SysSet

PERMISSION = "Setting.Plant Setup"


@login_required
def plant_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view plant Setup. {msg}"))
        return redirect("core:home")

    context["timezone_choices"] = dict(sorted(TIME_ZONE_DICT.items(), key=lambda item: item[1]))
    context["departments"] = SysSet().get_val("DEPARTMENTS")
    context["entry_methods"] = SysSet().get_val("SAP_ENTRY_METHOD")
    context["inventory_types"] = SysSet().get_val("SAP_INVENTORY_TYPE")

    sap_locations = SAPLocation.objects.filter(plant=plant)
    context["sap_locations"] = sap_locations

    return render(request, "site_setting/plant_setup.html", context)


@login_required
def create_plant(request):
    curr_user = request.user
    can_act, msg = check_permission(curr_user, "", PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create new plant. {msg}"))
        return redirect("site_setting:plant_setup")

    curr_time = datetime.now().astimezone()

    post_data = request.GET
    plant_code = post_data.get("plant_code", "").strip().upper()
    plant_name = post_data.get("plant_name", "").strip()
    site = post_data.get("site", "").strip()
    customer = post_data.get("customer", "").strip()
    timezone = post_data.get("timezone", "America/Chicago")

    if plant_code == "" or plant_name == "" or site == "" or customer == "":
        messages.error(request, "Some required fields are empty, fill all required fields. ")
        return redirect("site_setting:plant_setup")

    plant_ref = Plant.objects.filter(code=plant_code).first()
    if plant_ref:
        messages.error(request, f"Plant {plant_code} already exists.")
        return redirect("site_setting:plant_setup")

    Plant.objects.create(
        code=plant_code,
        name=plant_name,
        site=site,
        customer=customer,
        timezone=timezone,
        created_at=curr_time,
        created_by=curr_user,
        updated_at=curr_time,
        updated_by=curr_user,
    )

    messages.success(request, f"Plant {plant_code} is created successfully. ")
    return redirect("site_setting:plant_setup")


@login_required
def update_plant(request):
    curr_user = request.user
    can_act, msg = check_permission(curr_user, "", PERMISSION, True)
    if not can_act:
        return json_error(f"You do NOT have permission to Edit new plant. {msg}")

    curr_time = datetime.now().astimezone()

    post_data = request.POST
    plant_code = post_data.get("plant_code", "").strip().upper()
    plant_name = post_data.get("plant_name", "").strip()
    site = post_data.get("site", "").strip()
    customer = post_data.get("customer", "").strip()
    timezone = post_data.get("timezone", "America/Chicago")
    status = post_data.get("status", "").strip()

    if plant_code == "" or plant_name == "" or site == "" or customer == "":
        return json_error("Some required fields are empty, fill all required fields. ")

    plant_ref = Plant.objects.filter(code=plant_code).first()
    if not plant_ref:
        return json_error(f"Plant {plant_code} does not exists. Ask Global Admin to create it.")

    Plant.objects.filter(pk=plant_ref.pk).update(
        name=plant_name,
        site=site,
        customer=customer,
        timezone=timezone,
        updated_at=curr_time,
        updated_by=curr_user,
        is_active=False if status == "inactive" else True,
    )

    return json_success(f"Plant {plant_code} is updated successfully. ")


@login_required
def create_sap_location(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, f"Plant {plant_code} does not exist.")
        return redirect("site_setting:plant_setup")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create SAP Location. {msg}"))
        return redirect("site_setting:plant_setup")

    curr_time = datetime.now().astimezone()

    post_data = request.POST
    plant_code = plant.code
    active_cycle_ref = context["cycle_ref"]

    department = post_data.get("department", "")
    code = post_data.get("code", "").strip()
    address = post_data.get("address", "").strip()
    inventory_type = post_data.get("inventory_type", "").strip()
    entry_methods = post_data.getlist("count_methods", [])

    if department == "" or code == "":
        messages.error(request, "Some required fields are empty, fill all required fields. ")
        return redirect("site_setting:plant_setup")

    sap_loc_ref = SAPLocation.objects.filter(code=code, plant=plant).first()
    if sap_loc_ref:
        messages.error(request, f"Plant {plant_code} already has an SAP Location {code}.")
        return redirect("site_setting:plant_setup")

    sap_ref = SAPLocation.objects.create(
        plant=plant,
        code=code,
        department=department,
        address=address,
        inventory_type=inventory_type,
        allowed_entry_methods=entry_methods,
        created_at=curr_time,
        created_by=curr_user,
        updated_at=curr_time,
        updated_by=curr_user,
    )

    messages.success(request, f"Plant {plant_code} SAP Location {code} is created successfully. ")
    if active_cycle_ref:
        add_sap_location_to_cycle(active_cycle_ref, sap_ref, curr_user)
    return redirect("site_setting:plant_setup")


@login_required
def update_sap_location(request, sap_loc_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to update SAP Locations. {msg}"))
        return redirect("site_setting:plant_setup")

    active_cycle_ref = context["cycle_ref"]
    curr_time = datetime.now().astimezone()

    sap_location = SAPLocation.objects.filter(pk=sap_loc_id).first()
    if not sap_location:
        messages.error(request, "SAP Location not found.")
        return redirect("site_setting:plant_setup")

    post_data = request.POST

    department = post_data.get("department_id", "")
    code = post_data.get("code", "").strip()
    address = post_data.get("address", "").strip()
    inventory_type = post_data.get("inventory_type", "").strip()
    entry_methods = post_data.getlist("count_methods", [])
    active = post_data.get("is_active", "")

    if department == "" or code == "":
        messages.error(request, "Some required fields are empty, fill all required fields. ")
        return redirect("site_setting:plant_setup")

    SAPLocation.objects.filter(pk=sap_loc_id).update(
        department=department,
        code=code,
        address=address,
        inventory_type=inventory_type,
        allowed_entry_methods=entry_methods,
        updated_at=curr_time,
        updated_by=curr_user,
        is_active=active == "active",
    )

    messages.success(request, f"SAP Location {code} is updated successfully. ")
    if active_cycle_ref:
        sap_location.refresh_from_db()
        if active == "active":
            add_sap_location_to_cycle(active_cycle_ref, sap_location, curr_user)
        else:
            remove_sap_location_from_cycle(active_cycle_ref, sap_location, curr_user)

    return redirect("site_setting:plant_setup")
