from core._imports_for_views import *
from core.context_processors import get_basic_info
from count.models import CountRecord
from cycles.app_models.inventory_models import PartMaster
from cycles.models import PICycle
from site_setting.models import SAPLocation
from variance.models import CycleVariance

PERMISSION = "Variance.Variance by Location"


@login_required
def variance_by_location(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view variance by location. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-start_date").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return redirect("core:home")

    can_manage, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["can_manage"] = can_manage
    part_number = request.GET.get("part_number", "").strip()
    context["selected_sap_code"] = request.GET.get("sap_code", "").strip()

    if not part_number:
        return render(request, "variance/by_location.html", context)

    part = PartMaster.objects.filter(cycle=active_cycle, part_number=part_number).first()
    if not part:
        messages.error(request, f"Part {part_number} not found in the cycle {active_cycle}.")
        return render(request, "variance/by_location.html", context)

    context["part"] = part
    var_set = CycleVariance.objects.filter(cycle=active_cycle, plant=plant, part=part)
    context["var_set"] = var_set
    count_set = CountRecord.objects.filter(cycle=active_cycle, part=part).order_by("sap_location__code", "entered_at")
    context["count_set"] = count_set

    context["var_sap_code"] = list(var_set.exclude(variance_quantity=0).values_list("sap_location__code", flat=True).distinct())
    review_rows = []
    for sap_code in context["var_sap_code"]:
        review_rows.append(
            {
                "sap_location": SAPLocation.objects.filter(plant=plant, code=sap_code).first(),
                "variance": var_set.filter(sap_location__code=sap_code).first(),
                "comments": var_set.filter(sap_location__code=sap_code).first().comments.order_by("created_at"),
                "resolution": var_set.filter(sap_location__code=sap_code).first().resolutions.first(),
            }
        )
    context["review_rows"] = review_rows
    return render(request, "variance/by_location.html", context)
