from core._imports_for_views import *
from core.context_processors import get_basic_info
from count.models import CountRecord
from cycles.app_models.cycle_models import CycleSAPLocation
from site_setting.system_setting.sys_settings import SysSet

PERMISSION = "Count.Count Result"


@login_required
def count_result(request):
    # TODO: Add Audit Correction logic
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view Count Results. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "count/results.html", context)

    sap_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True).values_list("sap_location__code", flat=True)
    )
    count_records = CountRecord.objects.filter(cycle=active_cycle)

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    source_filter = search_data.get("source", "").strip()
    sap_location_filter = search_data.get("sap_location", "").strip()
    has_search = False
    if search:
        has_search = True
        count_records = count_records.filter(
            Q(part__part_number__icontains=search)
            | Q(part__description__icontains=search)
            | Q(tag_number__icontains=search)
            | Q(sap_location__code__icontains=search)
            | Q(sap_location__department__icontains=search)
            | Q(counter_name__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
        )

    if sap_location_filter:
        has_search = True
        count_records = count_records.filter(Q(sap_location__code__icontains=sap_location_filter))

    if source_filter:
        has_search = True
        count_records = count_records.filter(Q(source__icontains=source_filter))

    context["search"] = search
    context["source_filter"] = source_filter
    context["source_choices"] = SysSet().get_val("COUNT_SOURCE")
    context["sap_filter"] = sap_location_filter
    context["sap_locations"] = sap_locations
    context["count_records"] = count_records

    if has_search and not count_records.exists():
        messages.warning(request, "No Count Exceptions / Pending Items found matching your search criteria.")
    return render(request, "count/results.html", context)
