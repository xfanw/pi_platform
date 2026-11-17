from core._imports_for_views import *
from core.context_processors import get_basic_info
from count.models import CountRecord
from cycles.app_models.inventory_models import PartMaster
from cycles.models import PICycle
from site_setting.models import SAPLocation
from variance.models import CycleVariance, VarianceComment, VarianceResolution

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

    can_manage, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["can_manage"] = can_manage
    part_number = request.GET.get("part_number", "").strip()
    context["selected_sap_code"] = request.GET.get("sap_code", "").strip()

    if not part_number:
        return render(request, "variance/by_part.html", context)

    part = PartMaster.objects.filter(cycle=active_cycle, part_number=part_number).first()
    if not part:
        messages.error(request, f"Part {part_number} not found in the cycle {active_cycle}.")
        return render(request, "variance/by_part.html", context)

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
    return render(request, "variance/by_part.html", context)


def add_comment(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view variance by part. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-start_date").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return redirect("core:home")

    post_data = request.POST
    variance_id = post_data.get("variance_id")
    comment = post_data.get("comment", "").strip()
    variance = CycleVariance.objects.filter(id=variance_id).first()
    if not variance:
        messages.error(request, "Variance not found.")
        return redirect("variance:variance_by_part")
    if not comment:
        messages.error(request, "Comment cannot be empty.")
        return redirect(f"/variance/variance_by_part?part_number={variance.part.part_number}&sap_code={variance.sap_location.code}")

    VarianceComment.objects.create(created_by=curr_user, body=comment, variance=variance)
    messages.success(request, "Comment added successfully.")
    return redirect(f"/variance/variance_by_part?part_number={variance.part.part_number}&sap_code={variance.sap_location.code}")


def add_decision(request):
    curr_user = request.user
    curr_time = datetime.now().astimezone()
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view variance by part. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-start_date").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return redirect("core:home")

    post_data = request.POST
    variance_id = post_data.get("variance_id")
    decision = post_data.get("decision")
    reason = post_data.get("reason", "").strip()
    variance = CycleVariance.objects.filter(id=variance_id).first()
    if not variance:
        messages.error(request, "Variance not found.")
        return redirect("variance:variance_by_part")
    if not decision:
        messages.error(request, "Decision cannot be empty.")
        return redirect(f"/variance/variance_by_part?part_number={variance.part.part_number}&sap_code={variance.sap_location.code}")

    VarianceResolution.objects.create(
        created_by=curr_user, variance=variance, status=decision, reason=reason, decided_at=curr_time, decided_by=curr_user
    )
    messages.success(request, "Decision added successfully.")
    return redirect(f"/variance/variance_by_part?part_number={variance.part.part_number}&sap_code={variance.sap_location.code}")
