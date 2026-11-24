from django.db import transaction

from core._imports_for_views import *
from core.context_processors import get_basic_info
from cycles.models import PICycle
from variance.models import CycleVariance, PostBatch, PostBatchLine, VarianceResolution

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
        messages.error(request, mark_safe(f"You do NOT have permission to view post batches. {msg}"))
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
    curr_time = datetime.now().astimezone()
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view post batch details. {msg}"))
        return redirect("core:home")

    # Implement the logic to fetch and display the details of a specific post batch here
    # This could involve querying the PostBatch model using the batch_id and adding it to the context
    active_cycle = context["cycle_ref"]
    if not active_cycle:
        context["is_closed"] = True
        active_cycle = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-opened_at").first()
        if not active_cycle:
            messages.error(request, "No active or closed cycle found for the plant.")
            return redirect("core:home")

    can_manage, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["can_confirm"] = can_manage
    context["is_draft"] = False
    batch = PostBatch.objects.filter(id=batch_id).first()
    if not batch:
        messages.error(request, "Post batch not found.")
        return redirect("variance:post_batches")

    context["batch"] = batch
    context["is_draft"] = True if batch.status == "Draft" else False
    batch_lines = PostBatchLine.objects.filter(batch=batch).order_by("id")
    context["batch_lines"] = batch_lines
    context["curr_date"] = curr_time.strftime("%Y-%m-%d")

    return render(request, "variance/post_batch_detail.html", context)


@login_required
def post_batch_confirm(request, batch_id):
    curr_user = request.user
    curr_time = datetime.now().astimezone()
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to confirm post batch. {msg}"))
        return redirect("core:home")

    batch = PostBatch.objects.filter(id=batch_id).first()
    if not batch:
        messages.error(request, "Post batch not found.")
        return redirect("variance:post_batches")

    post_data = request.POST
    action = post_data.get("action", "")
    sap_document_number = post_data.get("sap_document_number")
    posting_date = post_data.get("posting_date")
    exclude_line_ids = post_data.getlist("excluded_line_id")
    if action == "confirm":
        if not sap_document_number or not posting_date:
            messages.error(request, "SAP document number and posting date are required.")
            return redirect("variance:post_batches_detail", batch_id=batch_id)
        with transaction.atomic():
            batch.sap_document_number = sap_document_number
            batch.posting_date = posting_date
            batch.status = "Posted"
            batch.confirmed_by = curr_user
            batch.confirmed_at = curr_time
            batch.save()

            batch_lines = PostBatchLine.objects.filter(batch=batch)
            included_lines = batch_lines.exclude(id__in=exclude_line_ids)
            excluded_lines = batch_lines.filter(id__in=exclude_line_ids)

            # Update included lines to "Posted"
            for line in included_lines:
                # Update VarianceResolution status
                VarianceResolution.objects.filter(pk=line.resolution_id).update(
                    status="Posted",
                    sap_document_number=sap_document_number,
                    decided_at=curr_time,
                    decided_by=curr_user,
                )
                # Update CycleVariance status to match
                CycleVariance.objects.filter(pk=line.variance_id).update(status="Posted")

            # Update excluded lines to "Needs Review"
            for line in excluded_lines:
                # Update VarianceResolution status
                VarianceResolution.objects.filter(pk=line.resolution_id).update(
                    status="Needs Review",
                    decided_at=curr_time,
                    decided_by=curr_user,
                )
                # Update CycleVariance status to match
                CycleVariance.objects.filter(pk=line.variance_id).update(status="Needs Review")

        messages.success(request, "Post batch confirmed successfully.")
    elif action == "cancel":
        batch.status = "Cancelled"
        batch.posting_date = posting_date
        batch.confirmed_by = curr_user
        batch.confirmed_at = curr_time
        batch.save()
        messages.success(request, "Post batch cancelled successfully.")
    return redirect("variance:post_batches")
