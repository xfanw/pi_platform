from access_control.models import CounterRoster
from core._imports_for_views import *
from core.context_processors import get_basic_info
from count.models import CountIntakeException, CountRecord
from cycles.app_models.inventory_models import PartMaster
from cycles.models import (
    CyclePhysicalLocation,
    CycleSAPLocation,
    CycleSubLocation,
)

PERMISSION = "Count.Manual Key-In"


@login_required
def count_manual(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view manual key-in. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "count/manual.html", context)

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
            sub_name=F("sub_location__name"),
            loc_name=F("sub_location__physical_location__name"),
            sap_code=F("sub_location__physical_location__sap_location__code"),
        )
    )

    context["cycle_sap_locations"] = cycle_sap_locations
    context["cycle_physical_locations"] = cycle_physical_locations
    context["cycle_sub_locations"] = cycle_sub_locations
    plant_counter = list(
        CounterRoster.objects.filter(plant=plant, sap_location__isnull=True, is_active=True)
        .values_list("display_name", flat=True)
        .distinct()
    )
    context["plant_counter"] = plant_counter
    counter_roster_set = list(
        CounterRoster.objects.filter(plant=plant, sap_location__isnull=False, is_active=True).values(
            "sap_location__code", "display_name"
        )
    )

    context["counter_roster_set"] = counter_roster_set

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    sap_location_filter = search_data.get("sap_location", "").strip()
    location_filter = search_data.get("location", "").strip()
    sub_location_filter = search_data.get("sub_location", "").strip()
    count_record_set = CountRecord.objects.filter(cycle=active_cycle, source="Manual Key-in")
    has_search = False
    if search:
        has_search = True
        count_record_set = count_record_set.filter(
            Q(part__part_number__icontains=search)
            | Q(sap_location__code__icontains=search)
            | Q(sap_location__department__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
            | Q(counter_name__icontains=search)
        )
    if sap_location_filter:
        has_search = True
        count_record_set = count_record_set.filter(
            Q(sap_location__code__icontains=sap_location_filter) | Q(sap_location__department__icontains=sap_location_filter)
        )

    context["search"] = search
    context["location_filter"] = location_filter
    context["sap_location_filter"] = sap_location_filter
    context["sub_location_filter"] = sub_location_filter
    context["count_record_set"] = count_record_set

    if has_search and not count_record_set.exists():
        messages.warning(request, "No Count Records found matching your search criteria.")
    return render(request, "count/manual.html", context)


@login_required
def count_manual_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manual key-in. {msg}"))
        return redirect("core:home")

    curr_time = datetime.now().astimezone()
    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("count:count_manual")

    post_data = request.POST
    sap_location = post_data.get("sap_location", "")
    location = post_data.get("location", "").strip()
    sub_location = post_data.get("sub_location", "").strip()
    part_number = post_data.get("part_number", "").strip()
    quantity = post_data.get("quantity", "").strip()
    counter_name = post_data.get("counter_name", "").strip()
    if not part_number or not quantity:
        messages.error(request, "Part Number and Quantity are required.")
        return redirect("count:count_manual")

    if not counter_name:
        counter_name = curr_user.first_name

    if not sap_location or not location:
        messages.error(request, "SAP Location and Location are required.")
        return redirect("count:count_manual")

    sap_location_ref = CycleSAPLocation.objects.filter(plant=plant, cycle=active_cycle_ref, sap_location__code=sap_location).first()
    if not sap_location_ref:
        messages.error(request, "Invalid SAP Location selected.")
        return redirect("count:count_manual")

    location_ref = CyclePhysicalLocation.objects.filter(
        plant=plant,
        cycle=active_cycle_ref,
        physical_location__name=location,
        physical_location__sap_location=sap_location_ref.sap_location,
    ).first()
    if not location_ref:
        messages.error(request, "Invalid Location selected.")
        return redirect("count:count_manual")

    sub_location_ref = None
    if sub_location:
        sub_location_ref = CycleSubLocation.objects.filter(
            plant=plant,
            cycle=active_cycle_ref,
            sub_location__name=sub_location,
            sub_location__physical_location=location_ref.physical_location,
        ).first()
        if not sub_location_ref:
            messages.error(request, "Invalid Sub-location selected.")
            return redirect("count:count_manual")

    part_ref = PartMaster.objects.filter(cycle=active_cycle_ref, part_number=part_number).first()
    # counter_employee = CounterRoster.objects.filter(display_name=counter_name).order_by("-id").first()
    if part_ref:
        CountRecord.objects.create(
            cycle=active_cycle_ref,
            source="Manual Key-in",
            source_record_key=f"{counter_name}_{curr_time.strftime('%Y%m%d_%H%M%S')}",
            sap_location=sap_location_ref.sap_location,
            physical_location=location_ref.physical_location,
            sub_location=sub_location_ref.sub_location if sub_location_ref else None,
            part=part_ref,
            quantity=quantity,
            counter_name=counter_name,
            # counter_employee_id=counter_employee.employee_id if counter_employee else "",
            entered_by=curr_user,
            entered_at=curr_time,
            accepted_at=curr_time,
        )

        messages.success(request, "Count record created successfully.")
    else:
        CountIntakeException.objects.create(
            cycle=active_cycle_ref,
            raw_part_number=part_number,
            source="Manual Key-in",
            status="Pending",
            quantity=quantity,
            counter_name=counter_name,
            sap_location=sap_location_ref.sap_location if sap_location_ref else None,
            physical_location=location_ref.physical_location if location_ref else None,
            sub_location=sub_location_ref.sub_location if sub_location_ref else None,
            created_at=curr_time,
            created_by=curr_user,
            updated_by=curr_user,
        )
        messages.error(request, f"Unknown P/N {part_number} held in Pending Station for review.")
    return redirect("count:count_manual")


@login_required
def count_manual_update(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manual key-in. {msg}"))
        return redirect("core:home")

    curr_time = datetime.now().astimezone()
    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("count:count_manual")

    post_data = request.GET
    record_id = post_data.get("id")
    quantity = post_data.get("quantity")

    count_record = CountRecord.objects.filter(id=record_id, cycle=active_cycle_ref).first()
    if not count_record:
        messages.error(request, "Manual key-in part not found.")
        return redirect("count:count_manual")

    count_record.quantity = quantity
    count_record.entered_by = curr_user
    count_record.entered_at = curr_time
    count_record.save()
    messages.success(request, "Manual key-in part updated successfully.")

    return redirect(f"/count/count_manual?search={count_record.part.part_number}")


@login_required
def count_manual_delete(request, id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manual key-in. {msg}"))
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("count:count_manual")

    try:
        record = CountRecord.objects.get(id=id, cycle=active_cycle_ref)
        record.delete()
        messages.success(request, "Manual key-in part removed successfully.")
    except CountRecord.DoesNotExist:
        messages.error(request, "Manual key-in part not found.")
    return redirect("count:count_manual")
