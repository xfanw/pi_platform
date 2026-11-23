from collections import defaultdict

from django.db.models import Case, DecimalField, Value, When
from django.db.models.aggregates import Count
from django.db.models.functions import Abs

from core._imports_for_views import *
from core.context_processors import get_basic_info
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
        context["is_closed"] = True
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-opened_at").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return render(request, "variance/by_location.html", context)
    post_data = request.GET
    selected_department = post_data.get("department", "")
    selected_type = post_data.get("inventory_type", "")
    context["selected_department"] = selected_department
    context["selected_type"] = selected_type

    variance_set = CycleVariance.objects.filter(cycle=active_cycle, plant=plant)
    if selected_department:
        variance_set = variance_set.filter(sap_department=selected_department)

    if selected_type in ("", "FII_OWNED"):
        tk_variance = (
            variance_set.filter(sap_inventory_type="FII_OWNED")
            .values("sap_code", "sap_department")
            .annotate(
                total_part_count=Count("part", distinct=True),
                var_part_count=Count("part", filter=(~Q(variance_quantity=0)), distinct=True),
                net_variance=Sum("variance_value"),
                abs_variance=Sum(Abs("variance_value")),
                book_value=Sum(F("sap_quantity") * F("map_price")),
                count_value=Sum(F("count_quantity") * F("map_price")),
                net_var_percent=Case(
                    When(book_value=0, count_value=0, then=Value(100)),
                    When(book_value=0, then=Value(0)),
                    default=(
                        1
                        - Case(
                            When(net_variance__gte=0, book_value__gte=0, then=Case(
                                When(net_variance__lte=F("book_value"), then=F("net_variance") / F("book_value")),
                                default=F("book_value") / F("net_variance")
                            )),
                            When(net_variance__lt=0, book_value__lt=0, then=Case(
                                When(net_variance__gte=F("book_value"), then=-F("net_variance") / (-F("book_value"))),
                                default=(-F("book_value")) / (-F("net_variance"))
                            )),
                            When(net_variance__gte=0, book_value__lt=0, then=F("net_variance") / (-F("book_value"))),
                            default=(-F("net_variance")) / F("book_value")
                        )
                    )
                    * 100,
                    output_field=DecimalField(),
                ),
                abs_var_percent=Case(
                    When(book_value=0, abs_variance=0, then=Value(100)),
                    When(book_value=0, then=Value(0)),
                    default=(
                        1
                        - Case(
                            When(abs_variance__gte=0, book_value__gte=0, then=Case(
                                When(abs_variance__lte=F("book_value"), then=F("abs_variance") / F("book_value")),
                                default=F("book_value") / F("abs_variance")
                            )),
                            When(abs_variance__lt=0, book_value__lt=0, then=Case(
                                When(abs_variance__gte=F("book_value"), then=-F("abs_variance") / (-F("book_value"))),
                                default=(-F("book_value")) / (-F("abs_variance"))
                            )),
                            When(abs_variance__gte=0, book_value__lt=0, then=F("abs_variance") / (-F("book_value"))),
                            default=(-F("abs_variance")) / F("book_value")
                        )
                    )
                    * 100,
                    output_field=DecimalField(),
                ),
            )
        )
        context["tk_variance"] = tk_variance

    if selected_type in ("", "CONSIGNED"):
        cs_variance = list(
            variance_set.filter(sap_inventory_type="CONSIGNED")
            .values("sap_code", "sap_department")
            .annotate(
                part_count=Count("part", distinct=True),
                variance_part_count=Count("part", filter=(~Q(variance_quantity=0)), distinct=True),
                abs_count_variance=Sum(Abs("variance_quantity")),
            )
        )
        accuracy_totals = defaultdict(int)
        sap_codes = [item["sap_code"] for item in cs_variance]
        if sap_codes:
            accuracy_rows = CycleVariance.objects.filter(cycle=active_cycle, plant=plant, sap_code__in=sap_codes).only(
                "sap_code", "sap_quantity", "count_quantity"
            )
            for variance in accuracy_rows.iterator():
                accuracy_totals[variance.sap_code] += variance.qty_accuracy
        for item in cs_variance:
            item["acc_avg"] = accuracy_totals[item["sap_code"]] / item["part_count"]

        context["cs_variance"] = cs_variance

    context["active_department_list"] = list(
        CycleVariance.objects.filter(plant=plant, cycle=active_cycle)
        .values_list("sap_department", flat=True)
        .order_by("sap_department")
        .distinct()
    )
    return render(request, "variance/by_location.html", context)
