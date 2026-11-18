from access_control.app_functions import my_sap_loc
from core._imports_for_views import *
from core.context_processors import get_basic_info
from django.db.models import F
from cycles.app_models.cycle_models import CycleSAPLocation
from cycles.models import PICycle
from variance.app_functions.report import get_live_var_context, get_part_sap_matrix
from variance.models import CycleVariance

PERMISSION = "Variance.Live Variance Report"


@login_required
def variance_live_report(request):
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
            return render(request, "variance/live_report.html", context)

    can_manage, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["can_decide"] = can_manage

    cycle_sap_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True)
        .values(code=F("sap_location__code"), department=F("sap_location__department"))
        .order_by("sap_location__department", "sap_location__code")
    )
    context["department_list"] = sorted(set({dept for _, dept in cycle_sap_locations}))
    context["sap_list"] = cycle_sap_locations
    context["bu_list"] = sorted(
        CycleVariance.objects.filter(cycle=active_cycle, plant=plant).values_list("part__business_unit", flat=True).distinct()
    )

    post_data = request.GET
    selected_department = post_data.get("department", "").strip()
    selected_sap = post_data.get("sap_location", "").strip().upper()
    selected_bu = post_data.get("business_unit", "").strip()
    selected_type = post_data.get("inventory_type", "").strip().upper()
    search = post_data.get("search", "").strip()
    show_var_only = post_data.get("show", "")
    has_search = False

    curr_var_set = CycleVariance.objects.filter(cycle=active_cycle, plant=plant)
    if search:
        has_search = True
        curr_var_set = curr_var_set.filter(Q(part__part_number__icontains=search) | Q(part__description__icontains=search))
        context["search"] = search
    if selected_department:
        has_search = True
        curr_var_set = curr_var_set.filter(sap_location__department__icontains=selected_department)
        context["selected_department"] = selected_department
    if selected_sap:
        has_search = True
        curr_var_set = curr_var_set.filter(sap_location__code__icontains=selected_sap)
        context["selected_sap"] = selected_sap
    if selected_bu:
        has_search = True
        curr_var_set = curr_var_set.filter(part__business_unit__icontains=selected_bu)
        context["selected_bu"] = selected_bu
    if selected_type:
        has_search = True
        curr_var_set = curr_var_set.filter(sap_location__inventory_type__icontains=selected_type)
        context["selected_type"] = selected_type
    if show_var_only != "all":
        curr_var_set = curr_var_set.exclude(variance_quantity=0)
        context["show_all"] = False
    else:
        context["show_all"] = True

    tk_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True, sap_location__inventory_type="FII_OWNED")
        .values(code=F("sap_location__code"), department=F("sap_location__department"))
        .order_by("sap_location__department", "sap_location__code")
    )
    context["tk_locations"] = tk_locations
    cs_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True, sap_location__inventory_type="CONSIGNED")
        .values(code=F("sap_location__code"), department=F("sap_location__department"))
        .order_by("sap_location__department", "sap_location__code")
    )
    context["cs_locations"] = cs_locations
    context.update(get_live_var_context(curr_var_set))
    if has_search and not curr_var_set.exists():
        messages.error(request, "No matching part found.")
        return render(request, "variance/live_report.html", context)

    context.update(get_part_sap_matrix(curr_var_set, tk_locations, cs_locations))

    # review_rows = []
    # for sap_code in context["var_sap_code"]:
    #     review_rows.append(
    #         {
    #             "sap_location": SAPLocation.objects.filter(plant=plant, code=sap_code).first(),
    #             "variance": var_set.filter(sap_location__code=sap_code).first(),
    #             "comments": var_set.filter(sap_location__code=sap_code).first().comments.order_by("created_at"),
    #             "resolution": var_set.filter(sap_location__code=sap_code).first().resolutions.first(),
    #         }
    #     )
    # context["review_rows"] = review_rows
    return render(request, "variance/live_report.html", context)


# json response for getting comments
def get_comment(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        return json_error("No Plant is available in your approved scope.")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        return json_error(mark_safe(f"You do NOT have permission to view variance by part. {msg}"))

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        context["is_closed"] = True
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-opened_at").first()
        if not active_cycle:
            return json_error("No active or closed cycle found for the plant.")

    can_manage, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["can_decide"] = can_manage
    part_number = request.GET.get("part_number")
    if not part_number:
        return json_error("Part number is required.")

    var_set = CycleVariance.objects.filter(cycle=active_cycle, plant=plant, part__part_number=part_number)
    my_sap_list = my_sap_loc(curr_user, plant)
    context["var_sap_code"] = list(var_set.exclude(variance_quantity=0).values_list("sap_location__code", flat=True).distinct())
    review_rows = []
    for sap_code in context["var_sap_code"]:
        review_rows.append(
            {
                "variance": var_set.filter(sap_location__code=sap_code).first(),
                "comments": var_set.filter(sap_location__code=sap_code).first().comments.order_by("created_at"),
                "resolution": var_set.filter(sap_location__code=sap_code).first().resolutions.first(),
            }
        )
    context["review_rows"] = review_rows
