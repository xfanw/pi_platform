from access_control.models import CounterRoster
from core._imports_for_views import *
from core.context_processors import get_basic_info
from count.app_functions.input import add_tag_info
from count.models import CountIntakeException, CountRecord, CycleTagDetail
from cycles.app_models.cycle_models import CycleSAPLocation
from cycles.models import PartMaster

PERMISSION = "Setting.Count.Tag Key-In"


@login_required
def count_tag(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view tag key-in. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "count/tag.html", context)

    cycle_sap_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True).values_list("sap_location__code", flat=True)
    )

    context["cycle_sap_locations"] = cycle_sap_locations

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    sap_location_filter = search_data.get("sap_location", "").strip()
    tag_number = search_data.get("tag_number", "").strip()

    tag_set = CycleTagDetail.objects.filter(tag_range__cycle=active_cycle)
    has_search = False
    if search:
        has_search = True
        tag_set = tag_set.filter(
            Q(count_record__part__part_number__icontains=search)
            | Q(tag_number=search)
            | Q(tag_range__sap_location__code__icontains=search)
            | Q(tag_range__sap_location__department__icontains=search)
            | Q(tag_range__physical_location__name__icontains=search)
            | Q(tag_range__sub_location__name__icontains=search)
        )
    if sap_location_filter:
        has_search = True
        tag_set = tag_set.filter(tag_range__sap_location__code=sap_location_filter)
    context["search"] = search
    context["tag_number"] = tag_number
    context["sap_location_filter"] = sap_location_filter

    if has_search and not tag_set.exists():
        messages.warning(request, "No Count Records found matching your search criteria.")

    if not tag_number:
        context["blank_tag_set"] = tag_set.filter(is_counted=False).order_by("tag_number")[:20]
        context["counted_tag_set"] = tag_set.filter(is_counted=True).order_by("count_record__entered_at")[:50]
        return render(request, "count/tag.html", context)

    curr_tag = CycleTagDetail.objects.filter(tag_range__cycle=active_cycle, tag_number=tag_number, is_counted=False).first()
    if not curr_tag:
        messages.error(
            request, mark_safe(f"Tag number {tag_number} is <b>NOT found</b> or <b>already counted</b> in cycle {active_cycle.name}.")
        )
        return render(request, "count/tag.html", context)

    #
    # if tag is selected
    context["curr_sap_code"] = curr_tag.tag_range.sap_location.code
    context["curr_location"] = curr_tag.tag_range.physical_location.name
    context["curr_sub_location"] = curr_tag.tag_range.sub_location.name
    context["sap_location_filter"] = curr_tag.tag_range.sap_location.code
    tag_set = tag_set.filter(tag_range__sap_location__code=curr_tag.tag_range.sap_location.code)
    context["sap_location_filter"] = curr_tag.tag_range.sap_location.code
    context["blank_tag_set"] = tag_set.filter(is_counted=False).order_by("tag_number")[:20]
    context["counted_tag_set"] = tag_set.filter(is_counted=True).order_by("count_record__entered_at")[:20]
    context["curr_counter_list"] = CounterRoster.objects.filter(plant=curr_tag.tag_range.plant).filter(
        Q(sap_location=curr_tag.tag_range.sap_location) | Q(sap_location__isnull=True)
    )
    return render(request, "count/tag.html", context)


@login_required
def count_tag_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to tag key-in. {msg}"))
        return redirect("core:home")

    curr_time = datetime.now().astimezone()
    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("count:count_tag")

    post_data = request.POST
    tag_number = post_data.get("tag_number", "").strip()
    part_number = post_data.get("part_number", "").strip()
    quantity = post_data.get("quantity", "").strip()
    counter_name = post_data.get("counter_name", "").strip()
    if not tag_number or not part_number or not quantity:
        messages.error(request, "Tag Number, Part Number and Quantity are required.")
        return redirect("count:count_tag")

    if not counter_name:
        counter_name = curr_user.first_name

    tag_ref = CycleTagDetail.objects.filter(tag_number=tag_number, tag_range__cycle=active_cycle_ref, is_counted=False).first()
    if not tag_ref:
        messages.error(request, f"Tag number {tag_number} not found or already counted in cycle {active_cycle_ref.name}.")
        return redirect(f"/count/count_tag?tag_number={tag_number}")

    part_ref = PartMaster.objects.filter(cycle=active_cycle_ref, part_number=part_number).first()
    if part_ref:
        count_record = CountRecord.objects.create(
            cycle=active_cycle_ref,
            source="Tag Key-in",
            source_record_key=f"{counter_name}_{curr_time.strftime('%Y%m%d_%H%M%S')}",
            tag_number=tag_number,
            sap_location=tag_ref.tag_range.sap_location,
            physical_location=tag_ref.tag_range.physical_location,
            sub_location=tag_ref.tag_range.sub_location,
            part=part_ref,
            quantity=quantity,
            counter_name=counter_name,
            entered_by=curr_user,
            entered_at=curr_time,
            accepted_at=curr_time,
        )
        add_tag_info(tag_ref, count_record, curr_user)

        messages.success(request, "Count record created successfully.")
    else:
        ex_part_ref = CountIntakeException.objects.create(
            cycle=active_cycle_ref,
            raw_part_number=part_number,
            source="Tag Key-in",
            status="Pending",
            tag_number=tag_number,
            quantity=quantity,
            counter_name=counter_name,
            sap_location=tag_ref.tag_range.sap_location,
            physical_location=tag_ref.tag_range.physical_location,
            sub_location=tag_ref.tag_range.sub_location,
            created_at=curr_time,
            created_by=curr_user,
            updated_by=curr_user,
        )
        add_tag_info(tag_ref, None, curr_user, ex_prt_ref=ex_part_ref)
        messages.error(request, f"Unknown P/N {part_number} held in Pending Station for review.")
    return redirect(f"/count/count_tag?tag_number={int(tag_number)+1}")
