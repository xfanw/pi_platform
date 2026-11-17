from core._imports_for_views import *
from core.context_processors import get_basic_info
from cycles.app_models.inventory_models import PartMaster
from cycles.models import PICycle
from variance.models import CycleVariance

PERMISSION = "Variance.Variance by PN"


@login_required
def variance_by_part(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view variance by part. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-start_date").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return redirect("core:home")

    part_number = request.GET.get("part_number", "").strip()
    if not part_number:
        return render(request, "variance/by_part.html", context)

    part = PartMaster.objects.filter(cycle=active_cycle, part_number=part_number).first()
    if not part:
        messages.error(request, f"Part {part_number} not found in the cycle {active_cycle}.")
        return render(request, "variance/by_part.html", context)

    context["part"] = part
    has_var = CycleVariance.objects.filter(part=part).exists() if part else False
    context["has_var"] = has_var
    return render(request, "variance/by_part.html", context)
