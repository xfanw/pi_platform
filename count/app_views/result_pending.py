from access_control.app_functions import is_global_manager, is_plant_manager, my_sap_loc
from core._imports_for_views import *
from core.context_processors import get_basic_info
from count.app_functions.input import add_tag_info
from count.models import CountIntakeException, CountRecord, CycleTagDetail
from cycles.app_models.inventory_models import PartMaster
from site_setting.system_setting.sys_settings import SysSet

PERMISSION = "Count.Pending Station"


@login_required
def pending_station(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view Pending Station. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "count/pending.html", context)
    if is_global_manager(curr_user) or is_plant_manager(curr_user, plant):
        count_ex_set = CountIntakeException.objects.filter(cycle=active_cycle)
    else:
        my_sap_list = my_sap_loc(curr_user, plant)
        count_ex_set = CountIntakeException.objects.filter(cycle=active_cycle, sap_location__code__in=my_sap_list)
    may_review, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["status_choices"] = SysSet().get_val("COUNT_EXCEPTION_STATUS")
    context["may_review"] = may_review
    context["total_count"] = count_ex_set.count()
    context["pending_count"] = count_ex_set.filter(status="Pending").count()
    context["approved_count"] = count_ex_set.filter(status="Approved New Part").count()
    context["mapped_count"] = count_ex_set.filter(status="Mapped to Existing Part").count()
    context["rejected_count"] = count_ex_set.filter(status="Rejected").count()

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    status_filter = search_data.get("status", "").strip()
    has_search = False
    if search:
        has_search = True
        count_ex_set = count_ex_set.filter(
            Q(raw_part_number__icontains=search)
            | Q(tag_number__icontains=search)
            | Q(sap_location__code__icontains=search)
            | Q(sap_location__department__icontains=search)
            | Q(counter_name__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
        )
    if status_filter:
        has_search = True
        count_ex_set = count_ex_set.filter(Q(status__icontains=status_filter))

    context["search"] = search
    context["status_filter"] = status_filter
    context["count_ex_pending_set"] = count_ex_set.filter(status="Pending").order_by("-created_at")
    context["count_ex_finished_set"] = count_ex_set.exclude(status="Pending").order_by("-created_at")

    if has_search and not count_ex_set.exists():
        messages.warning(request, "No Count Exceptions / Pending Items found matching your search criteria.")
    return render(request, "count/pending.html", context)


@login_required
def pending_part_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manage Pending Station. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return redirect("count:pending_station")

    curr_time = datetime.now().astimezone()
    post_data = request.GET
    item_id = post_data.get("item_id", "").strip()
    raw_part_no = post_data.get("part_number", "").strip()
    description = post_data.get("description", "").strip()
    price = post_data.get("price", "").strip()
    business_unit = post_data.get("business_unit", "").strip()
    note = post_data.get("note", "").strip()

    if not raw_part_no or not description or not price or not business_unit:
        messages.error(request, "All fields are required to create a new part.")
        return redirect("count:pending_station")

    existing_part = PartMaster.objects.filter(cycle=active_cycle, part_number=raw_part_no).first()
    if existing_part:
        messages.error(
            request,
            mark_safe(
                f"Part {raw_part_no} already exists. <br>BU:{existing_part.business_unit} MAP$:{existing_part.price}<br> Please use MAP to Existing Part."
            ),
        )
        return redirect("count:pending_station")
    # Create the new part here
    try:
        new_pat_ref = PartMaster.objects.create(
            cycle=active_cycle,
            part_number=raw_part_no,
            description=description,
            business_unit=business_unit,
            price=price,
            created_at=curr_time,
            created_by=curr_user,
            updated_by=curr_user,
        )
        # CountIntakeException.objects.filter(cycle=active_cycle, raw_part_number=raw_part_no).update(
        #     status="Approved New Part", part=new_pat_ref
        # )
        CountIntakeException.objects.filter(id=item_id).update(
            status="Approved New Part",
            disposition_part=new_pat_ref,
            disposition_reason=note,
            reviewed_by=curr_user,
            reviewed_at=curr_time,
        )
        ex_part = CountIntakeException.objects.filter(id=item_id).first()
        count_ref = CountRecord.objects.create(
            part=ex_part.disposition_part,
            cycle=active_cycle,
            source=ex_part.source,
            source_record_key=f"{ex_part.counter_name}_{ex_part.created_at.strftime('%Y%m%d_%H%M%S')}",
            sap_location=ex_part.sap_location,
            physical_location=ex_part.physical_location,
            sub_location=ex_part.sub_location,
            tag_number=ex_part.tag_number,
            quantity=ex_part.quantity,
            counter_name=ex_part.counter_name,
            entered_by=ex_part.created_by,
            entered_at=ex_part.created_at,
        )
        tag_ref = CycleTagDetail.objects.filter(tag_number=ex_part.tag_number, tag_range__cycle=active_cycle).first()
        if tag_ref:
            add_tag_info(tag_ref, count_ref, curr_user, ex_part_ref=None)
        messages.success(request, f"New part {raw_part_no} created successfully.")
    except Exception as e:
        messages.error(request, f"Failed to create new part: {str(e)}")

    return redirect("count:pending_station")


@login_required
def pending_part_map(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manage Pending Station. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return redirect("count:pending_station")

    curr_time = datetime.now().astimezone()
    post_data = request.GET
    item_id = post_data.get("item_id", "").strip()
    existing_part_number = post_data.get("existing_part_number", "").strip()

    if not existing_part_number:
        messages.error(request, "Existing part number field is required to map a part.")
        return redirect("count:pending_station")

    existing_part = PartMaster.objects.filter(cycle=active_cycle, part_number=existing_part_number).first()
    if not existing_part:
        messages.error(request, f"Input P/N {existing_part_number} does not exist.")
        return redirect("count:pending_station")

    try:
        CountIntakeException.objects.filter(id=item_id).update(
            status="Mapped to Existing Part", disposition_part=existing_part, reviewed_by=curr_user, reviewed_at=curr_time
        )
        ex_part = CountIntakeException.objects.filter(id=item_id).first()
        count_ref = CountRecord.objects.create(
            part=ex_part.disposition_part,
            cycle=active_cycle,
            source=ex_part.source,
            source_record_key=f"{ex_part.counter_name}_{ex_part.created_at.strftime('%Y%m%d_%H%M%S')}",
            sap_location=ex_part.sap_location,
            physical_location=ex_part.physical_location,
            sub_location=ex_part.sub_location,
            tag_number=ex_part.tag_number,
            quantity=ex_part.quantity,
            counter_name=ex_part.counter_name,
            entered_by=ex_part.created_by,
            entered_at=ex_part.created_at,
        )
        tag_ref = CycleTagDetail.objects.filter(tag_number=ex_part.tag_number, tag_range__cycle=active_cycle).first()
        if tag_ref:
            add_tag_info(tag_ref, count_ref, curr_user, ex_part_ref=None)
        messages.success(request, f"Part {existing_part_number} mapped to existing part successfully.")
    except Exception as e:
        messages.error(request, f"Failed to map part: {str(e)}")

    return redirect("count:pending_station")


@login_required
def pending_part_reject(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manage Pending Station. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return redirect("count:pending_station")

    curr_time = datetime.now().astimezone()
    post_data = request.GET
    item_id = post_data.get("item_id", "").strip()
    note = post_data.get("note", "").strip()

    try:
        CountIntakeException.objects.filter(id=item_id).update(
            status="Rejected", disposition_reason=note, reviewed_by=curr_user, reviewed_at=curr_time
        )
        messages.success(request, "Part rejected successfully.")
    except Exception as e:
        messages.error(request, f"Failed to reject part: {str(e)}")

    return redirect("count:pending_station")
