from core._imports_for_views import *
from core.excel_file_handler.setting_location import (
    location_batch_upload,
    location_batch_validate,
    location_excel_bytes,
    sub_location_batch_upload,
    sub_location_batch_validate,
    sub_location_batch_validate,
    sub_location_excel_bytes,
)
from cycles.app_functions.cycle import *
from site_setting.models import (
    PhysicalLocation,
    SAPLocation,
    SubLocation,
    TempLocationDetail,
    TempLocationMain,
    TempSubLocationDetail,
    TempSubLocationMain,
)
from site_setting.system_setting.sys_settings import SysSet

# Create your views here.
PERMISSION = "Setting.Location"


@login_required
def location_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view location setup. {msg}"))
        return redirect("core:home")

    sap_locations = SAPLocation.objects.filter(plant=plant, is_active=True)
    context["sap_locations"] = sap_locations
    departments = SysSet().get_val("DEPARTMENTS")
    context["departments"] = departments

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    department_filter = search_data.get("department", "").strip()
    sap_location_filter = search_data.get("sap_location", "").strip()
    status_filter = search_data.get("status", "").strip().upper()
    location_set = PhysicalLocation.objects.filter(plant=plant)
    has_search = False
    if search:
        has_search = True
        location_set = location_set.filter(
            Q(name__icontains=search) | Q(sap_location__code__icontains=search) | Q(sap_location__department__icontains=search)
        )
    if department_filter:
        has_search = True
        location_set = location_set.filter(sap_location__department=department_filter)
    if sap_location_filter:
        has_search = True
        location_set = location_set.filter(sap_location__code=sap_location_filter)
    if status_filter == "ACTIVE":
        has_search = True
        location_set = location_set.filter(is_active=True)
    elif status_filter == "INACTIVE":
        has_search = True
        location_set = location_set.filter(is_active=False)

    context["search"] = search
    context["department_filter"] = department_filter
    context["sap_location_filter"] = sap_location_filter
    context["status_filter"] = status_filter

    # Bottom Display
    location_rows = location_set.order_by("-id").select_related("sap_location")
    context["location_rows"] = location_rows

    if has_search and not location_rows.exists():
        messages.warning(request, "No Physical Locations found matching your search criteria.")

    return render(request, "site_setting/location_setup.html", context)


@login_required
def create_location(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create new physical location. {msg}"))
        return redirect("site_setting:location_setup")

    curr_time = datetime.now().astimezone()

    active_cycle_ref = context["cycle_ref"]
    post_data = request.POST
    sap_location_id = post_data.get("sap_location_id", "")
    physical_location = post_data.get("physical_location", "").strip()

    if sap_location_id == "" or physical_location == "":
        messages.error(request, "Some required fields are empty, fill all required fields. ")
        return redirect("site_setting:location_setup")

    sap_location = SAPLocation.objects.filter(pk=sap_location_id).first()
    if not sap_location:
        messages.error(request, "Selected SAP Location not found.")
        return redirect("site_setting:location_setup")

    location_ref = PhysicalLocation.objects.filter(sap_location_id=sap_location_id, name=physical_location).first()
    if location_ref:
        messages.error(request, f"Physical Location {physical_location} already exists under the selected SAP Location.")
        return redirect("site_setting:location_setup")

    loc_ref = PhysicalLocation.objects.create(
        plant=sap_location.plant,
        sap_location_id=sap_location_id,
        name=physical_location,
        created_at=curr_time,
        created_by=curr_user,
        updated_at=curr_time,
        updated_by=curr_user,
    )

    messages.success(request, f"Physical Location {physical_location} is created successfully. ")

    if active_cycle_ref:
        add_physical_location_to_cycle(active_cycle_ref, loc_ref, curr_user)
    return redirect("site_setting:location_setup")


@login_required
def update_location(request, location_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to edit physical location. {msg}"))
        return redirect("site_setting:location_setup")

    active_cycle_ref = context["cycle_ref"]
    curr_time = datetime.now().astimezone()

    physical_location = PhysicalLocation.objects.filter(pk=location_id).first()
    if not physical_location:
        messages.error(request, "Physical Location not found.")
        return redirect("site_setting:location_setup")

    post_data = request.POST
    is_active = post_data.get("is_active", "").strip()

    PhysicalLocation.objects.filter(pk=location_id).update(
        is_active=is_active == "active",
        updated_at=curr_time,
        updated_by=curr_user,
    )

    messages.success(request, f"Physical Location {physical_location} is updated successfully. ")
    if active_cycle_ref:
        physical_location.refresh_from_db()
        if is_active == "active":
            add_physical_location_to_cycle(active_cycle_ref, physical_location, curr_user)
        else:
            remove_physical_location_from_cycle(active_cycle_ref, physical_location, curr_user)
    return redirect("site_setting:location_setup")


@login_required
def location_template_download(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")
    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to download file. {msg}"))
        return redirect("site_setting:location_setup")

    excel_file = location_excel_bytes(plant)

    return http_excel(excel_file, f"location_setup_{plant.code}")


@login_required
def location_file_upload(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to upload file. {msg}"))
        return redirect("site_setting:location_setup")

    try:
        status, msg = location_batch_upload(request.FILES.get("location_file"), "Locations", plant=plant, actor=request.user)
        if status == "error":
            messages.error(request, msg)
            return redirect("site_setting:location_setup")
        # TODO: Keep Log

        batch = msg
        location_batch_validate(batch)
        batch.refresh_from_db()

        if batch.error_count:
            messages.error(
                request,
                "Preview created with validation errors. Correct the workbook and upload it again.",
            )
        else:
            messages.success(
                request,
                "Preview is ready. Review every row before confirming the import.",
            )
        return redirect("site_setting:location_batch", batch_id=batch.id)
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("site_setting:location_setup")


@login_required
def location_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to add location. {msg}"))
        return redirect("site_setting:location_setup")

    batch_ref = TempLocationMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    context["rows"] = TempLocationDetail.objects.filter(batch=batch_ref).order_by("id")
    return render(request, "site_setting/location_batch.html", context)


@login_required
def location_batch_confirm(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create location. {msg}"))
        return redirect("site_setting:location_setup")

    curr_time = datetime.now().astimezone()
    batch_ref = TempLocationMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    location_set = TempLocationDetail.objects.filter(batch=batch_ref).order_by("id")
    existing_plant_location = list(PhysicalLocation.objects.filter(plant=plant).values_list("name", "sap_location__code"))

    new_location = []
    try:
        for location_detail in location_set:
            update_row = True

            if (
                location_detail.name,
                location_detail.sap_location.code if location_detail.sap_location else None,
            ) in existing_plant_location:
                update_row = False
            if update_row:
                new_location.append(
                    PhysicalLocation(
                        plant=batch_ref.plant,
                        name=location_detail.name,
                        sap_location=location_detail.sap_location,
                        created_by=curr_user,
                        updated_by=curr_user,
                    )
                )

        # TODO: Add Log

        active_cycle_ref = context["cycle_ref"]
        new_locs = PhysicalLocation.objects.bulk_create(new_location)
        if active_cycle_ref:
            for loc in new_locs:
                add_physical_location_to_cycle(active_cycle_ref, loc, curr_user)
    except Exception as e:
        messages.error(request, f"Error creating Physical Location. {clean_errors(e)}")
        return redirect("site_setting:location_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = len(new_location)
    batch_ref.skipped_row = location_set.count() - len(new_location)
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    return redirect("site_setting:location_batch", batch_id=batch_ref.id)


@login_required
def sub_location_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view sub location setup. {msg}"))
        return redirect("core:home")

    physical_locations = PhysicalLocation.objects.filter(plant=plant, is_active=True)
    context["physical_locations"] = physical_locations
    sap_locations = SAPLocation.objects.filter(plant=plant, is_active=True)
    context["sap_locations"] = sap_locations

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    sap_location_filter = search_data.get("sap_location", "").strip()
    location_filter = search_data.get("location", "").strip()
    scope_filter = search_data.get("scope", "").strip().upper()
    status_filter = search_data.get("status", "").strip().upper()
    sub_location_set = SubLocation.objects.filter(plant=plant)
    has_search = False
    if search:
        has_search = True
        sub_location_set = sub_location_set.filter(
            Q(name__icontains=search)
            | Q(physical_location__sap_location__code__icontains=search)
            | Q(physical_location__sap_location__department__icontains=search)
            | Q(physical_location__name__icontains=search)
        )
    if location_filter:
        has_search = True
        sub_location_set = sub_location_set.filter(physical_location__id=location_filter)
    if sap_location_filter:
        has_search = True
        sub_location_set = sub_location_set.filter(physical_location__sap_location__code=sap_location_filter)
    if scope_filter == "CURRENT":
        has_search = True
        # TODO: Sub-location scope filter logic to be implemented based on current PI
    if status_filter == "ACTIVE":
        has_search = True
        sub_location_set = sub_location_set.filter(is_active=True)
    elif status_filter == "INACTIVE":
        has_search = True
        sub_location_set = sub_location_set.filter(is_active=False)

    context["search"] = search
    context["location_filter"] = location_filter
    context["sap_location_filter"] = sap_location_filter
    context["status_filter"] = status_filter

    # Bottom Display
    sub_location_rows = sub_location_set.order_by("-id").select_related("physical_location__sap_location")
    context["sub_location_rows"] = sub_location_rows

    if has_search and not sub_location_rows.exists():
        messages.warning(request, "No Physical Sub-locations found matching your search criteria.")

    return render(request, "site_setting/location_sub_setup.html", context)


@login_required
def create_sub_location(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create new sub-location.{msg}"))
        return redirect("site_setting:sub_location_setup")

    curr_time = datetime.now().astimezone()
    active_cycle_ref = context["cycle_ref"]

    post_data = request.POST
    physical_location_id = post_data.get("physical_location_id", "")
    name = post_data.get("name", "").strip()

    if physical_location_id == "" or name == "":
        messages.error(request, "Some required fields are empty, fill all required fields. ")
        return redirect("site_setting:sub_location_setup")

    pysical_location = PhysicalLocation.objects.filter(pk=physical_location_id).first()
    if not pysical_location:
        messages.error(request, "Selected Parent Location not found.")
        return redirect("site_setting:sub_location_setup")

    sub_location_ref = SubLocation.objects.filter(physical_location_id=physical_location_id, name=name).first()
    if sub_location_ref:
        messages.error(request, f"Sub-Location {name} already exists under the selected Parent Location.")
        return redirect("site_setting:sub_location_setup")

    sub_loc = SubLocation.objects.create(
        plant=pysical_location.plant,
        physical_location_id=physical_location_id,
        name=name,
        created_at=curr_time,
        created_by=curr_user,
        updated_at=curr_time,
        updated_by=curr_user,
    )

    messages.success(request, f"Sub-Location {name} is created successfully. ")
    if active_cycle_ref:
        add_sub_location_to_cycle(active_cycle_ref, sub_loc, curr_user)
    return redirect("site_setting:sub_location_setup")


@login_required
def update_sub_location(request, sub_location_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to edit sub-location.{msg}"))
        return redirect("site_setting:location_setup")

    active_cycle_ref = context["cycle_ref"]
    curr_time = datetime.now().astimezone()

    sub_location = SubLocation.objects.filter(pk=sub_location_id).first()
    if not sub_location:
        messages.error(request, "Sub-Location not found.")
        return redirect("site_setting:sub_location_setup")

    post_data = request.POST
    is_active = post_data.get("is_active", "").strip()

    SubLocation.objects.filter(pk=sub_location_id).update(
        is_active=is_active == "active",
        updated_at=curr_time,
        updated_by=curr_user,
    )

    messages.success(request, f"Sub-Location {sub_location.name} is updated successfully. ")
    if active_cycle_ref:
        sub_location.refresh_from_db()
        if is_active == "active":
            add_sub_location_to_cycle(active_cycle_ref, sub_location, curr_user)
        else:
            remove_sub_location_from_cycle(active_cycle_ref, sub_location, curr_user)
    return redirect("site_setting:sub_location_setup")


@login_required
def sub_location_template_download(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")
    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to download file. {msg}"))
        return redirect("site_setting:sub_location_setup")

    excel_file = sub_location_excel_bytes(plant)

    return http_excel(excel_file, f"sub_location_setup_{plant.code}")


@login_required
def sub_location_file_upload(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to upload file. {msg}"))
        return redirect("site_setting:sub_location_setup")

    try:
        status, msg = sub_location_batch_upload(request.FILES.get("sub_loc_file"), "Sub Locations", plant=plant, actor=request.user)
        if status == "error":
            messages.error(request, msg)
            return redirect("site_setting:sub_location_setup")
        # TODO: Keep Log

        batch = msg
        sub_location_batch_validate(batch)
        batch.refresh_from_db()

        if batch.error_count:
            messages.error(
                request,
                "Preview created with validation errors. Correct the workbook and upload it again.",
            )
        else:
            messages.success(
                request,
                "Preview is ready. Review every row before confirming the import.",
            )
        return redirect("site_setting:sub_location_batch", batch_id=batch.id)
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("site_setting:sub_location_setup")


@login_required
def sub_location_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to add sub location. {msg}"))
        return redirect("site_setting:sub_location_setup")

    batch_ref = TempSubLocationMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    context["rows"] = TempSubLocationDetail.objects.filter(batch=batch_ref).order_by("id")
    return render(request, "site_setting/location_sub_batch.html", context)


@login_required
def sub_location_batch_confirm(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create sub location. {msg}"))
        return redirect("site_setting:sub_location_setup")

    curr_time = datetime.now().astimezone()
    batch_ref = TempSubLocationMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    sub_location_set = TempSubLocationDetail.objects.filter(batch=batch_ref).order_by("id")
    existing_plant_location = list(SubLocation.objects.filter(plant=plant).values_list("name", "physical_location__name"))

    new_location = []
    try:
        for sub_location_detail in sub_location_set:
            update_row = True

            if (
                sub_location_detail.name,
                sub_location_detail.physical_location.name if sub_location_detail.physical_location else None,
            ) in existing_plant_location:
                update_row = False
            if update_row:
                new_location.append(
                    SubLocation(
                        plant=batch_ref.plant,
                        name=sub_location_detail.name,
                        physical_location=sub_location_detail.physical_location,
                        created_by=curr_user,
                        updated_by=curr_user,
                    )
                )

        # TODO: Add Log

        active_cycle_ref = context["cycle_ref"]
        new_locs = SubLocation.objects.bulk_create(new_location)
        if active_cycle_ref:
            for loc in new_locs:
                add_sub_location_to_cycle(active_cycle_ref, loc, curr_user)
    except Exception as e:
        messages.error(request, f"Error creating SubLocation. {clean_errors(e)}")
        return redirect("site_setting:sub_location_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = len(new_location)
    batch_ref.skipped_row = sub_location_set.count() - len(new_location)
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    return redirect("site_setting:sub_location_batch", batch_id=batch_ref.id)
