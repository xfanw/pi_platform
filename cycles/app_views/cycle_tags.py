from core._imports_for_views import *
from core.context_processors import get_basic_info
from core.excel_file_handler.cycle_tag_range import tag_batch_upload, tag_batch_validate, tag_range_excel_bytes
from cycles.models import (
    CyclePhysicalLocation,
    CycleSAPLocation,
    CycleSubLocation,
    CycleTagRange,
    TempCycleTagDetail,
    TempCycleTagMain,
)

PERMISSION = "Setting.Tag Range"


def tag_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view tag range setup. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "cycles/cycle_tags.html", context)

    cycle_sap_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True).values_list(
            "sap_location__code", "sap_location__department"
        )
    )

    cycle_physical_locations = list(
        CyclePhysicalLocation.objects.filter(cycle=active_cycle, is_active=True).values(
            loc_name=F("physical_location__name"), sap_code=F("physical_location__sap_location__code")
        )
    )
    cycle_sub_locations = list(
        CycleSubLocation.objects.filter(cycle=active_cycle, is_active=True).values(
            sub_name=F("sub_location__name"), loc_name=F("sub_location__physical_location__name")
        )
    )

    context["cycle_sap_locations"] = cycle_sap_locations
    context["cycle_physical_locations"] = cycle_physical_locations
    context["cycle_sub_locations"] = cycle_sub_locations
    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    sap_location_filter = search_data.get("sap_location", "").strip()
    location_filter = search_data.get("location", "").strip()
    sub_location_filter = search_data.get("sub_location", "").strip()
    tag_range_set = CycleTagRange.objects.filter(plant=plant)
    has_search = False
    if search:
        has_search = True
        tag_range_set = tag_range_set.filter(
            Q(name__icontains=search)
            | Q(sap_location__code__icontains=search)
            | Q(sap_location__department__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
        )
    if sap_location_filter:
        has_search = True
        tag_range_set = tag_range_set.filter(
            Q(sap_location__code__icontains=sap_location_filter) | Q(sap_location__department__icontains=sap_location_filter)
        )
    if location_filter:
        has_search = True
        tag_range_set = tag_range_set.filter(physical_location__name__icontains=location_filter)
    if sub_location_filter:
        has_search = True
        tag_range_set = tag_range_set.filter(sub_location__name__icontains=sub_location_filter)

    context["search"] = search
    context["location_filter"] = location_filter
    context["sap_location_filter"] = sap_location_filter
    context["sub_location_filter"] = sub_location_filter
    context["tag_ranges"] = tag_range_set

    if has_search and not tag_range_set.exists():
        messages.warning(request, "No Tag Ranges found matching your search criteria.")
    return render(request, "cycles/cycle_tags.html", context)


def tag_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create tag range. {msg}"))
        return redirect("core:home")

    curr_time = datetime.now().astimezone()
    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    post_data = request.POST

    sap_location = post_data.get("sap_location", "")
    location = post_data.get("location", "").strip()
    sub_location = post_data.get("sub_location", "").strip()
    start_number = post_data.get("start_number", "").strip()
    end_number = post_data.get("end_number", "").strip()
    if not start_number or not end_number:
        messages.error(request, "Start Number and End Number are required.")
        return redirect("cycles:tag_setup")

    if not start_number.isnumeric() or not end_number.isnumeric():
        messages.error(request, "Start Number and End Number must be numeric.")
        return redirect("cycles:tag_setup")

    if int(start_number) > int(end_number):
        messages.error(request, "Start Number cannot be greater than End Number.")
        return redirect("cycles:tag_setup")

    sub_location_ref = CycleSubLocation.objects.filter(
        plant=plant,
        cycle=active_cycle_ref,
        sub_location__name=sub_location,
        sub_location__physical_location__name=location,
        sub_location__physical_location__sap_location__code=sap_location,
    ).first()

    if not sub_location_ref:
        messages.error(request, "Invalid Sub-location selected.")
        return redirect("cycles:tag_setup")

    existing_range = CycleTagRange.objects.filter(end_number__gte=start_number, start_number__lte=end_number).order_by("-created_at")
    if existing_range.exists():
        msg = "<table class='table-center'><tr><th>SAP Location</th><th>Physical Location</th><th>Sub Location</th><th>Start Number</th><th>End Number</th></tr>"
        for existing_item in existing_range[:5]:
            msg += f"<tr><td>{existing_item.sap_location.code}</td><td>{existing_item.physical_location.name}</td><td>{existing_item.sub_location.name}</td><td>{existing_item.start_number}</td><td>{existing_item.end_number}</td></tr>"
        msg += "</table>"

        latest_existing_range = existing_range.first()
        msg += f"<br><br>Next Available Tag Start Number is: <b>{latest_existing_range.end_number + 1}</b>"
        messages.error(request, mark_safe(f"Overlapping tag range exists.<br><br>{msg}"))
        return redirect("cycles:tag_setup")

    tag_range = CycleTagRange.objects.create(
        plant=plant,
        cycle=active_cycle_ref,
        sap_location=sub_location_ref.sub_location.physical_location.sap_location,
        physical_location=sub_location_ref.sub_location.physical_location,
        sub_location=sub_location_ref.sub_location,
        start_number=start_number,
        end_number=end_number,
        tag_count=int(end_number) - int(start_number) + 1,
        created_at=curr_time,
        created_by=curr_user,
        updated_by=curr_user,
    )

    messages.success(request, f"Tag range {start_number} {end_number} created successfully.")
    return redirect("cycles:tag_setup")


@login_required
def tag_template_download(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    active_cycle_ref = context["cycle_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create tag range. {msg}"))
        return redirect("core:home")

    excel_file = tag_range_excel_bytes(plant, active_cycle_ref)
    cycle_name = active_cycle_ref.name if active_cycle_ref else "no_active_cycle"
    return http_excel(excel_file, f"tag range {plant.code} setup {cycle_name}")


@login_required
def tag_file_upload(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    active_cycle_ref = context["cycle_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to upload file. {msg}"))
        return redirect("cycles:tag_setup")

    try:
        status, msg = tag_batch_upload(
            request.FILES.get("upload_tag_range"), "Tag Ranges", plant=plant, cycle=active_cycle_ref, actor=request.user
        )
        if status == "error":
            messages.error(request, msg)
            return redirect("cycles:tag_setup")
        # TODO: Keep Log

        batch = msg
        tag_batch_validate(batch)
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
        return redirect("cycles:tag_batch", batch_id=batch.id)
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("cycles:tag_batch", batch_id=batch.id)


@login_required
def tag_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view counter roster. {msg}"))
        return redirect("cycles:tag_setup")

    batch_ref = TempCycleTagMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    context["rows"] = TempCycleTagDetail.objects.filter(batch=batch_ref).order_by("id")
    return render(request, "cycles/cycle_tag_batch.html", context)


@login_required
def tag_batch_confirm(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create tag ranges. {msg}"))
        return redirect("cycles:tag_setup")

    curr_time = datetime.now().astimezone()
    batch_ref = TempCycleTagMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    tag_set = TempCycleTagDetail.objects.filter(batch=batch_ref).order_by("id")

    new_tag_range = []
    try:
        for tag_detail in tag_set:

            new_tag_range.append(
                CycleTagRange(
                    plant=tag_detail.plant,
                    cycle=tag_detail.cycle,
                    start_number=tag_detail.start_number,
                    end_number=tag_detail.end_number,
                    tag_count=tag_detail.end_number - tag_detail.start_number + 1,
                    sap_location=tag_detail.sap_location,
                    physical_location=tag_detail.physical_location,
                    sub_location=tag_detail.sub_location,
                    created_by=curr_user,
                    updated_by=curr_user,
                )
            )

        CycleTagRange.objects.bulk_create(new_tag_range)
    except Exception as e:
        messages.error(request, f"Error creating Cycle Tag Ranges. {clean_errors(e)}")
        return redirect("cycles:tag_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = tag_set.count()
    batch_ref.skipped_row = 0
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    return redirect("cycles:tag_batch", batch_id=batch_ref.id)
