from access_control.app_functions import is_global_manager, is_plant_manager, my_sap_loc
from core._imports_for_views import *
from core.app_functions import http_excel, get_paginated_obj
from core.context_processors import get_basic_info
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Subquery
from cycles.app_models.cycle_models import CycleSAPLocation
from cycles.models import PICycle
from variance.app_functions.report import get_live_var_context, get_part_sap_matrix
from variance.app_functions.excel_export import variance_export_excel_bytes
from variance.models import CycleVariance, PostBatch, PostBatchLine, VarianceResolution

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
        messages.error(request, mark_safe(f"You do NOT have permission to view variance report. {msg}"))
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
    context["department_list"] = sorted(set({dept["department"] for dept in cycle_sap_locations}))
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

    tk_set = CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True, sap_location__inventory_type="FII_OWNED")

    cs_set = CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True, sap_location__inventory_type="CONSIGNED")
    context.update(get_live_var_context(curr_var_set))
    if search:
        has_search = True
        curr_var_set = curr_var_set.filter(Q(part__part_number__icontains=search) | Q(part__description__icontains=search))
        context["search"] = search
    if selected_department:
        has_search = True
        curr_var_set = curr_var_set.filter(sap_department__icontains=selected_department)
        tk_set = tk_set.filter(sap_location__department__icontains=selected_department)
        cs_set = cs_set.filter(sap_location__department__icontains=selected_department)
        context["selected_department"] = selected_department
    if selected_sap:
        has_search = True
        curr_var_set = curr_var_set.filter(sap_code__icontains=selected_sap)
        tk_set = tk_set.filter(sap_location__code__icontains=selected_sap)
        cs_set = cs_set.filter(sap_location__code__icontains=selected_sap)
        context["selected_sap"] = selected_sap
    if selected_bu:
        has_search = True
        curr_var_set = curr_var_set.filter(part__business_unit__icontains=selected_bu)
        context["selected_bu"] = selected_bu
    if selected_type:
        has_search = True
        curr_var_set = curr_var_set.filter(sap_inventory_type__icontains=selected_type)
        context["selected_type"] = selected_type
    if show_var_only == "variance":
        has_search = True
        curr_var_set = curr_var_set.exclude(variance_quantity=0)
        context["show_all"] = False
    else:
        context["show_all"] = True

    tk_locations = list(
        tk_set.values(code=F("sap_location__code"), department=F("sap_location__department")).order_by(
            "sap_location__department", "sap_location__code"
        )
    )
    context["tk_locations"] = tk_locations

    cs_locations = list(
        cs_set.values(code=F("sap_location__code"), department=F("sap_location__department")).order_by(
            "sap_location__department", "sap_location__code"
        )
    )
    context["cs_locations"] = cs_locations
    filtered_var_context = get_live_var_context(curr_var_set)
    if has_search:
        context["has_search"] = True
        context["cs_abs_qty_filtered"] = filtered_var_context.get("cs_abs_qty")
        context["cs_avg_acc_filtered"] = filtered_var_context.get("cs_avg_acc")
        context["tk_abs_acc_filtered"] = filtered_var_context.get("tk_abs_acc")
        context["tk_abs_val_filtered"] = filtered_var_context.get("tk_abs_val")
        context["tk_net_acc_filtered"] = filtered_var_context.get("tk_net_acc")
        context["tk_net_val_filtered"] = filtered_var_context.get("tk_net_val")
        context["tk_count_value_filtered"] = filtered_var_context.get("tk_count_value")
        context["tk_book_value_filtered"] = filtered_var_context.get("tk_book_value")
    if has_search and not curr_var_set.exists():
        messages.error(request, "No matching part found.")
        return render(request, "variance/live_report.html", context)

    # Paginate variance results
    part_sap_matrix_context = get_part_sap_matrix(curr_var_set, tk_locations, cs_locations)
    rows = part_sap_matrix_context.get("rows", [])

    # Apply pagination using existing function
    rows_ordered = sorted(rows, key=lambda x: x["part"].part_number)

    pagination_context = get_paginated_obj(rows_ordered, request.GET.get("page_num", 1), request.GET.get("per_page_element", 30))

    context["variance_row_count"] = len(rows_ordered)
    context.update(pagination_context)
    context.update(part_sap_matrix_context)

    return render(request, "variance/live_report.html", context)


# json response for getting comments
@login_required
def get_comment(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        return json_error("No Plant is available in your approved scope.")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        return json_error(mark_safe(f"You do NOT have permission to view variance comment. {msg}"))

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
    if not is_global_manager(curr_user) and not is_plant_manager(curr_user, plant):
        my_sap_list = my_sap_loc(curr_user, plant)
        var_set = var_set.filter(sap_location__code__in=my_sap_list)

    var_sap_code = list(var_set.exclude(variance_quantity=0).values_list("sap_code", flat=True).distinct())
    if not var_sap_code:
        return json_error("No variance found for the given part number in your scope.")

    json_context = {}
    json_context["var_sap_code"] = var_sap_code
    review_rows = []
    for sap_code in var_sap_code:
        curr_var = var_set.filter(sap_code=sap_code).first()
        curr_res = curr_var.resolutions.first()
        curr_comments = curr_var.comments.order_by("created_at").values("created_by__username", "body", "created_at")

        review_rows.append(
            {
                "sap_code": sap_code,
                "sap_department": curr_var.sap_department,
                "sap_inventory": curr_var.sap_inventory_type,
                "book_count": float(curr_var.sap_quantity),
                "count_value": float(curr_var.count_quantity),
                "variance_quantity": float(curr_var.variance_quantity),
                "variance_value": float(curr_var.variance_value),
                "status": curr_res.status if curr_res else "Needs Review",
                "comments": [
                    {
                        "created_by": com["created_by__username"],
                        "body": com["body"],
                        "created_at": com["created_at"].strftime("%Y-%m-%d %H:%M") if com["created_at"] else "",
                    }
                    for com in curr_comments
                ],
                "resolution": {
                    "reason": curr_res.reason if curr_res and curr_res.reason else curr_res.status if curr_res else "",
                    "created_at": curr_res.created_at.strftime("%Y-%m-%d %H:%M") if curr_res and curr_res.created_at else "",
                    "created_by": curr_res.created_by.username if curr_res and curr_res.created_by else "",
                    "sap_document_number": curr_res.sap_document_number if curr_res else "",
                },
            }
        )
    json_context["review_rows"] = review_rows
    return json_success("", **json_context)


@login_required
def post_batch_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create post batches. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return json_error("No active cycle found for the plant.")
    post_data = request.POST
    batch_name = post_data.get("batch_name", "").strip()
    batch_note = post_data.get("batch_note", "").strip()
    reason = post_data.get("reason", "").strip()
    part_numbers = post_data.getlist("part_number", [])
    if not batch_name:
        messages.error(request, "Batch name is required.")
        return redirect("variance:variance_live_report")

    if not part_numbers:
        messages.error(request, "No part numbers selected.")
        return redirect("variance:variance_live_report")

    post_batch_ref = PostBatch.objects.filter(cycle=active_cycle, name=batch_name).first()
    if post_batch_ref:
        messages.error(request, f"A post batch with name '{batch_name}' already exists.")
        return redirect("variance:variance_live_report")

    with transaction.atomic():
        var_set = (
            CycleVariance.objects.filter(
                cycle=active_cycle,
                plant=plant,
                part__part_number__in=part_numbers,
            )
            .exclude(variance_quantity=0)
            .exclude(Q(status="Posted") | Q(status="Not Post"))
        )
        variances = list(
            var_set.select_related("part").annotate(
                has_included_batch=Exists(
                    PostBatchLine.objects.exclude(batch__status="Cancelled").filter(variance_id=OuterRef("pk"), is_included=True)
                ),
                first_resolution_id=Subquery(
                    VarianceResolution.objects.filter(variance_id=OuterRef("pk")).order_by("pk").values("pk")[:1]
                ),
            )
        )

        for var in variances:
            if var.has_included_batch:
                messages.error(
                    request,
                    f"Variance for part '{var.part.part_number}' in SAP {var.sap_code} already exists in a post batch.",
                )
                return redirect("variance:variance_live_report")

        post_batch_ref = PostBatch.objects.create(
            cycle=active_cycle,
            name=batch_name,
            note=batch_note,
            created_by=curr_user,
        )
        missing_variances = [var for var in variances if var.first_resolution_id is None]
        if missing_variances:
            VarianceResolution.objects.bulk_create(
                [
                    VarianceResolution(
                        variance=var,
                        reason=reason,
                        status="To Post",
                        created_by=curr_user,
                        decided_by=curr_user,
                        decided_at=datetime.now().astimezone(),
                    )
                    for var in missing_variances
                ]
            )
            resolution_ids = dict(
                VarianceResolution.objects.filter(variance__in=missing_variances).order_by("-pk").values_list("variance_id", "pk")
            )
            for var in missing_variances:
                var.first_resolution_id = resolution_ids[var.pk]

        PostBatchLine.objects.bulk_create(
            [
                PostBatchLine(
                    variance_id=var.pk,
                    batch=post_batch_ref,
                    resolution_id=var.first_resolution_id,
                    part_number_snapshot=var.part.part_number,
                    variance_quantity_snapshot=var.variance_quantity,
                    variance_value_snapshot=var.variance_value,
                    movement_type="901" if var.variance_quantity > 0 else "902",
                )
                for var in variances
            ]
        )

        # Update reason for all resolutions if provided
        VarianceResolution.objects.filter(variance__in=var_set).filter(
            Q(reason="") | Q(reason__isnull=True),
        ).update(reason=reason)

        # Sync status: update both VarianceResolution and CycleVariance to "To Post"
        VarianceResolution.objects.filter(variance__in=var_set).update(status="To Post")
        var_set.update(status="To Post")
    messages.success(request, f"Post batch {batch_name} created successfully.")
    return redirect("variance:variance_live_report")


@login_required
def variance_export(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create post batches. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return json_error("No active cycle found for the plant.")

    post_data = request.GET
    selected_department = post_data.get("department", "").strip()
    selected_sap = post_data.get("sap_location", "").strip().upper()
    selected_bu = post_data.get("business_unit", "").strip()
    selected_type = post_data.get("inventory_type", "").strip().upper()
    search = post_data.get("search", "").strip()
    show_var_only = post_data.get("show", "")

    curr_var_set = CycleVariance.objects.filter(cycle=active_cycle, plant=plant)
    if search:
        curr_var_set = curr_var_set.filter(Q(part__part_number__icontains=search) | Q(part__description__icontains=search))
    if selected_department:
        curr_var_set = curr_var_set.filter(sap_department__icontains=selected_department)
    if selected_sap:
        curr_var_set = curr_var_set.filter(sap_code__icontains=selected_sap)
    if selected_bu:
        curr_var_set = curr_var_set.filter(part__business_unit__icontains=selected_bu)
    if selected_type:
        curr_var_set = curr_var_set.filter(sap_inventory_type__icontains=selected_type)
    if show_var_only != "all":
        curr_var_set = curr_var_set.exclude(variance_quantity=0)

    excel_context = get_live_var_context(curr_var_set)
    excel_context["curr_var_set"] = curr_var_set

    # Get locations for matrix
    tk_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True, sap_location__inventory_type="FII_OWNED")
        .values(code=F("sap_location__code"), department=F("sap_location__department"))
        .order_by("sap_location__department", "sap_location__code")
    )
    cs_locations = list(
        CycleSAPLocation.objects.filter(cycle=active_cycle, is_active=True, sap_location__inventory_type="CONSIGNED")
        .values(code=F("sap_location__code"), department=F("sap_location__department"))
        .order_by("sap_location__department", "sap_location__code")
    )

    # Generate Excel file
    excel_bytes = variance_export_excel_bytes(excel_context, curr_var_set, tk_locations, cs_locations)

    return http_excel(excel_bytes, f"{active_cycle.name}_Variance")
