from audit.app_functions.planning import generate_audit_records, init_candidates, regenerate_candidates
from audit.models import AuditPlan
from core._imports_for_views import *
from cycles.app_models.cycle_models import CyclePhysicalLocation, CycleSAPLocation
from count.models import CountRecord

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
        .values(
            sap_id=F("sap_location__id"),
            code=F("sap_location__code"),
            department=F("sap_location__department"),
        )
        .order_by("sap_location__department", "sap_location__code")
    )

    cycle_physical_locations = list(
        CyclePhysicalLocation.objects.filter(cycle=active_cycle, is_active=True).values(
            loc_id=F("physical_location__id"),
            loc_name=F("physical_location__name"),
            sap_code=F("physical_location__sap_location__code"),
        )
    )
    context["department_list"] = sorted(set({dept["department"] for dept in cycle_sap_locations}))
    context["sap_list"] = cycle_sap_locations
    context["physical_list"] = cycle_physical_locations

    cycle_name = active_cycle.name
    cycle_plan_count = AuditPlan.objects.filter(cycle=active_cycle).count()
    context["audit_plan_name"] = f"{cycle_name} - Audit {cycle_plan_count + 1}"
    context["plans"] = AuditPlan.objects.filter(cycle=active_cycle).order_by("-id")
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

    post_data = request.POST

    try:
        # Validate and extract integer fields
        auditors = int(post_data.get("auditors", 0))
        pages_per_auditor = int(post_data.get("pages_per_auditor", 0))
        density = int(post_data.get("density", 0))

        if auditors < 1 or pages_per_auditor < 1 or density < 1:
            raise ValueError("Auditors, Pages per Auditor, and Density must be greater than 0")

        # Validate and extract float fields
        value_pct = float(post_data.get("value_pct", "0"))
        map_pct = float(post_data.get("map_pct", "0"))
        variance_pct = float(post_data.get("variance_pct", "0"))

        if not (0 <= value_pct <= 100 and 0 <= map_pct <= 100 and 0 <= variance_pct <= 100):
            raise ValueError("All percentage values must be between 0 and 100")

        if not value_pct + map_pct + variance_pct == 100:
            raise ValueError("The sum of value_pct, map_pct, and variance_pct must be 100")

        # Extract plan name and department
        plan_name = post_data.get("plan_name", "").strip()
        if not plan_name:
            raise ValueError("Plan name is required")

        department_id = post_data.get("department_id", "").strip()

        # Extract location IDs - empty means all
        sap_location_ids = post_data.getlist(
            "sap_location_ids",
        )
        physical_location_ids = post_data.getlist("physical_location_ids")

        # Build CountRecord filter query
        count_filter = Q(cycle=active_cycle)

        # Filter by SAP location if specified
        if sap_location_ids:
            count_filter &= Q(sap_location_id__in=sap_location_ids)
        else:
            cycle_sap_set = CycleSAPLocation.objects.filter(cycle=active_cycle)
            if department_id:
                cycle_sap_set = cycle_sap_set.filter(sap_location__department=department_id)
            sap_location_ids = cycle_sap_set.values_list("sap_location_id", flat=True)

        # Filter by physical location if specified
        if physical_location_ids:
            count_filter &= Q(physical_location_id__in=physical_location_ids)

        # Filter by department if specified (through sap_location__department)
        if department_id:
            count_filter &= Q(sap_location__department=department_id)

        # Get filtered count records
        count_records = CountRecord.objects.filter(count_filter)
        total_records = count_records.count()

        if total_records == 0:
            raise ValueError("No count records found with the selected filters")

        # Calculate target count
        target_count = auditors * pages_per_auditor * density

        # Create AuditPlan
        audit_plan = AuditPlan.objects.create(
            cycle=active_cycle,
            department=department_id or "All",
            name=plan_name,
            auditors=auditors,
            pages_per_auditor=pages_per_auditor,
            rows_per_page=density,
            target_count=target_count,
            value_pct=value_pct,
            map_pct=map_pct,
            variance_pct=variance_pct,
            created_by=curr_user,
            updated_by=curr_user,
            status="Draft",
        )

        generate_audit_records(audit_plan, count_records, curr_user)
        init_candidates(audit_plan, curr_user)
        regenerate_candidates(audit_plan, curr_user)

        messages.success(request, f"Audit Plan '{plan_name}' created successfully with {total_records} available records.")
        return redirect("audit:audit_plan_detail", plan_id=audit_plan.id)

    except ValueError as e:
        messages.error(request, f"Validation Error: {str(e)}")
        return redirect("audit:audit_planning")
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect("audit:audit_planning")


@login_required
def audit_input(request, plan_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to input audit data. {msg}"))
        return redirect("core:home")

    audit_plan = AuditPlan.objects.filter(id=plan_id).first()
    if not audit_plan:
        messages.error(request, "Audit Plan not found.")
        return redirect("audit:audit_planning")
    context["audit_plan"] = audit_plan

    return render(request, "audit/audit_input.html", context)
