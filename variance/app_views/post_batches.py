from core._imports_for_views import *
from core.context_processors import get_basic_info
from cycles.models import PICycle
from variance.models import PostBatch

PERMISSION = "Variance.Post Batches"


@login_required
def post_batches_view(request):
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
        context["is_closed"] = True
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-opened_at").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return redirect("core:home")

    can_manage, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["can_confirm"] = can_manage

    context["open_batches"] = PostBatch.objects.filter(cycle=active_cycle, status="Draft")
    context["batch_history"] = PostBatch.objects.filter(cycle=active_cycle).exclude(status="Draft")

    return render(request, "variance/post_batches.html", context)


@login_required
def post_batch_detail(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view post batch details. {msg}"))
        return redirect("core:home")

    # Implement the logic to fetch and display the details of a specific post batch here
    # This could involve querying the PostBatch model using the batch_id and adding it to the context

    return render(request, "variance/post_batch_detail.html", context)
