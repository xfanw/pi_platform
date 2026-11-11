from access_control.app_functions import is_global_manager, is_plant_manager, my_sap_loc
from core._imports_for_views import *
from core.context_processors import get_basic_info
from count.models import CountIntakeException
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
        messages.error(request, mark_safe(f"You do NOT have permission to view manual key-in. {msg}"))
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
    context["mapped_count"] = count_ex_set.filter(status="Mapped").count()
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
