from core._imports_for_views import *
from core.context_processors import get_basic_info
from cycles.models import PICycle

PERMISSION = "Variance.Variance by PN"


@login_required
def variance_by_part_view(request):
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
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-start_date").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return redirect("core:home")

    part_number = request.GET.get("part_number", "").strip()
    if not part_number:
        return render(request, "variance/by_part.html", context)
