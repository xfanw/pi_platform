from django.db.models.aggregates import Count
from django.db.models.functions import Abs

from core._imports_for_views import *
from core.context_processors import get_basic_info
from cycles.app_models.cycle_models import CycleSAPLocation
from cycles.models import PICycle
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
    post_data = request.GET
    selected_department = post_data.get("department", "")
    selected_type = post_data.get("inventory_type", "")
    context["selected_department"] = selected_department
    context["selected_type"] = selected_type

    if selected_type in ("", "FII_OWNED"):
        if not selected_department:
            tk_variance = (
                CycleVariance.objects.filter(cycle=active_cycle, plant=plant)
                .filter(sap_location__inventory_type="FII_OWNED")
                .values("sap_location__code", "sap_location__department")
                .annotate(
                    total_part_count=Count("part", distinct=True),
                    var_part_count=Count("part", filter=(~Q(variance_quantity=0)), distinct=True),
                    net_variance=Sum("variance_value"),
                    abs_variance=Sum(Abs("variance_value")),
                    book_value=Sum(F("sap_quantity") * F("map_price")),
                    net_var_percent=(1 - Abs(F("net_variance") / F("book_value"))) * 100,
                    abs_var_percent=(1 - F("abs_variance") / F("book_value")) * 100,
                )
            )
        else:
            tk_variance = (
                CycleVariance.objects.filter(cycle=active_cycle, plant=plant)
                .filter(sap_location__department=selected_department)
                .filter(sap_location__inventory_type="FII_OWNED")
                .values("sap_location__code", "sap_location__department")
                .annotate(
                    total_part_count=Count("part", distinct=True),
                    var_part_count=Count("part", filter=(~Q(variance_quantity=0)), distinct=True),
                    net_variance=Sum("variance_value"),
                    abs_variance=Sum(Abs("variance_value")),
                    book_value=Sum(F("sap_quantity") * F("map_price")),
                    net_var_percent=(1 - Abs(F("net_variance") / F("book_value"))) * 100,
                    abs_var_percent=(1 - F("abs_variance") / F("book_value")) * 100,
                )
            )
        context["tk_variance"] = tk_variance

    if selected_type in ("", "CONSIGNED"):
        if not selected_department:
            cs_variance = (
                CycleVariance.objects.filter(cycle=active_cycle, plant=plant)
                .filter(sap_location__inventory_type="CONSIGNED")
                .values("sap_location__code", "sap_location__department")
                .annotate(
                    part_count=Count("part", distinct=True),
                    variance_part_count=Count("part", filter=(~Q(variance_quantity=0)), distinct=True),
                    abs_count_variance=Sum(Abs("variance_quantity")),
                )
            )
        else:
            cs_variance = (
                CycleVariance.objects.filter(cycle=active_cycle, plant=plant)
                .filter(sap_location__department=selected_department)
                .filter(sap_location__inventory_type="CONSIGNED")
                .values("sap_location__code", "sap_location__department")
                .annotate(
                    part_count=Count("part", distinct=True),
                    variance_part_count=Count("part", filter=(~Q(variance_quantity=0)), distinct=True),
                    abs_count_variance=Sum(Abs("variance_quantity")),
                )
            )

        for item in cs_variance:
            curr_set = CycleVariance.objects.filter(cycle=active_cycle, plant=plant, sap_location__code=item["sap_location__code"])
            curr_total_acc = 0
            for curr_cs in curr_set:
                curr_total_acc += curr_cs.qty_accuracy
            item["acc_avg"] = curr_total_acc / item["part_count"]

        context["cs_variance"] = cs_variance

    context["active_department_list"] = list(
        CycleSAPLocation.objects.filter(plant=plant, cycle=active_cycle, is_active=True)
        .values_list("sap_location__department", flat=True)
        .order_by("sap_location__department")
        .distinct()
    )
    return render(request, "variance/by_location.html", context)
