from core._imports_for_views import *
from cycles.app_models.cycle_models import CyclePhysicalLocation, CycleSAPLocation

PERMISSION = "Setting.PI Cycles"


@login_required
def audit_planning(request):
    # Your view logic here
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view audit planning. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "audit/planning.html", context)

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["may_create"] = can_act

    cycle_sap_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True)
        .values(code=F("sap_location__code"), department=F("sap_location__department"))
        .order_by("sap_location__department", "sap_location__code")
    )

    cycle_physical_locations = list(
        CyclePhysicalLocation.objects.filter(cycle=active_cycle, is_active=True).values(
            loc_name=F("physical_location__name"), sap_code=F("physical_location__sap_location__code")
        )
    )
    context["department_list"] = sorted(set({dept["department"] for dept in cycle_sap_locations}))
    context["sap_list"] = cycle_sap_locations
    context["physical_list"] = cycle_physical_locations
    pprint(context)

    return render(request, "audit/planning.html", context)


@login_required
def audit_planning_create(request):
    # Your view logic here
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create audit planning. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "audit/planning.html", context)

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["may_create"] = can_act

    return render(request, "audit/planning_create.html", context)


@login_required
def audit_plan_detail(request, plan_id):
    # Your view logic here
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create audit planning. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "audit/planning.html", context)

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["may_create"] = can_act

    cycle_sap_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True)
        .values(code=F("sap_location__code"), department=F("sap_location__department"))
        .order_by("sap_location__department", "sap_location__code")
    )

    cycle_physical_locations = list(
        CyclePhysicalLocation.objects.filter(cycle=active_cycle, is_active=True).values(
            loc_name=F("physical_location__name"), sap_code=F("physical_location__sap_location__code")
        )
    )
    context["department_list"] = sorted(set({dept["department"] for dept in cycle_sap_locations}))
    context["sap_list"] = cycle_sap_locations
    context["physical_list"] = cycle_physical_locations
    pprint(context)

    return render(request, "audit/planning.html", context)
