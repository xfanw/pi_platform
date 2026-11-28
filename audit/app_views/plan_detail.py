from audit.app_functions.planning import regenerate_candidates
from audit.models import AuditCandidate, AuditPlan, AuditRecord
from core._imports_for_views import *

PERMISSION = "Setting.PI Cycles"


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

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["may_manage"] = can_act

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return redirect("audit:audit_planning")

    plan_ref = AuditPlan.objects.filter(id=plan_id).first()
    if not plan_ref:
        messages.error(request, "Audit Plan not found.")
        return redirect("audit:audit_planning")

    context["audit_plan"] = plan_ref
    context["selected"] = plan_ref.real_total_count
    context["available"] = plan_ref.records.count()
    context["difference"] = plan_ref.real_total_count - plan_ref.target_count
    context["required_pages"] = (plan_ref.target_count + plan_ref.rows_per_page - 1) // plan_ref.rows_per_page
    get_data = request.GET
    category = get_data.get("show", "selected")
    search_val = get_data.get("search", "")
    candidate_set = AuditCandidate.objects.filter(plan=plan_ref)
    context["show"] = category
    context["show"] = category
    context["search"] = search_val
    if search_val:
        candidate_set = candidate_set.filter(
            Q(part_number_snapshot__icontains=search_val)
            | Q(description_snapshot__icontains=search_val)
            | Q(sap_location__code__icontains=search_val)
        )

    if category == "selected":
        candidate_set = candidate_set.filter(selected_records__gt=0).order_by(
            "coverage_pct", "-selection_reason", "book_value", "map_price"
        )
    elif category == "unselected":
        candidate_set = candidate_set.filter(selected_records__lt=F("count_records")).order_by(
            "-coverage_pct", "-selection_reason", "book_value", "map_price"
        )

    context["candidates"] = candidate_set
    return render(request, "audit/plan_detail.html", context)


@login_required
def audit_plan_regenerate(request, plan_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manage audit plans. {msg}"))
        return redirect("core:home")

    audit_plan = AuditPlan.objects.filter(id=plan_id).first()
    if not audit_plan:
        messages.error(request, "Audit Plan not found.")
        return redirect("audit:audit_planning")

    if request.method == "POST":
        try:
            auditors = int(request.POST.get("auditors"))
            pages_per_auditor = int(request.POST.get("pages_per_auditor"))
            rows_per_page = int(request.POST.get("density"))
            value_pct = float(request.POST.get("value_pct"))
            map_pct = float(request.POST.get("map_pct"))
            variance_pct = float(request.POST.get("variance_pct"))

            audit_plan.auditors = auditors
            audit_plan.pages_per_auditor = pages_per_auditor
            audit_plan.rows_per_page = rows_per_page
            audit_plan.value_pct = value_pct
            audit_plan.map_pct = map_pct
            audit_plan.variance_pct = variance_pct
            audit_plan.save()

            AuditRecord.objects.filter(plan=audit_plan).update(selected=False)
            AuditCandidate.objects.filter(plan=audit_plan).update(selected_records=0, selection_reason="", coverage_pct=0)
            # generate_audit_records(audit_plan, audit_plan.records.count())
            regenerate_candidates(audit_plan, curr_user)

            messages.success(request, f"Audit Plan '{audit_plan.name}' regenerated successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")

    return redirect("audit:audit_plan_detail", plan_id=plan_id)


@login_required
def audit_candidate_detail(request, candidate_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        return json_error("No Plant is available in your approved scope.")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        return json_error(mark_safe(f"You do NOT have permission to manage audit plans. {msg}"))

    audit_set = (
        AuditRecord.objects.filter(candidate_id=candidate_id)
        .order_by("-selected", "id")
        .values(
            "id",
            "selected",
            "part_number_snapshot",
            "count_quantity_snapshot",
            "physical_location_snapshot",
            "sub_location_snapshot",
            "tag_number_snapshot",
        )
    )
    if not audit_set.exists():
        return json_error("Audit Record not found.")

    return json_success("", data=list(audit_set))


@login_required
def audit_candidate_update(request, candidate_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view audit plans. {msg}"))
        return redirect("core:home")

    candidate_ref = AuditCandidate.objects.filter(id=candidate_id).first()
    if not candidate_ref:
        messages.error(request, "Audit Candidate not found.")
        return redirect("audit:audit_plan_detail")

    print(request.GET)
    record_id_list = request.GET.getlist("selected_record")
    pprint(record_id_list)

    AuditRecord.objects.filter(id__in=record_id_list, candidate_id=candidate_id).update(selected=True, updated_by=curr_user)
    AuditRecord.objects.filter(candidate_id=candidate_id).exclude(id__in=record_id_list).update(selected=False, updated_by=curr_user)

    old_selected_records = candidate_ref.selected_records
    candidate_ref.selected_records = len(record_id_list)
    candidate_ref.coverage_pct = len(record_id_list) / candidate_ref.count_records * 100
    candidate_ref.selection_reason = " Manual Select"
    candidate_ref.updated_by = curr_user
    candidate_ref.save()

    plan_ref = candidate_ref.plan
    plan_ref.real_total_count += len(record_id_list) - old_selected_records
    plan_ref.updated_by = curr_user
    plan_ref.save()
    return redirect("audit:audit_plan_detail", plan_id=candidate_ref.plan_id)


@login_required
def audit_plan_finalize(request, plan_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to manage audit plans. {msg}"))
        return redirect("core:home")

    audit_plan = AuditPlan.objects.filter(id=plan_id).first()
    if not audit_plan:
        messages.error(request, "Audit Plan not found.")
        return redirect("audit:audit_planning")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "finalize":
            try:
                audit_plan.status = "Finalized"
                audit_plan.save()
                messages.success(request, f"Audit Plan '{audit_plan.name}' finalized successfully.")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")

    return redirect("audit:audit_plan_detail", plan_id=plan_id)
