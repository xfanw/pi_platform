from django.db import transaction
from django.utils import timezone

from core._imports_for_views import *
from core.context_processors import get_basic_info
from core.excel_file_handler.count_batch import count_batch_upload, count_batch_validate, count_excel_bytes
from count.models import CountIntakeException, CountRecord, CycleTagDetail, TempCountLoadDetail, CountLoadBatch

PERMISSION = "Count.Count Result Upload"


@login_required
def count_upload(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view manual key-in. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "count/batches.html", context)

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()
    sap_location_filter = search_data.get("sap_location", "").strip()
    location_filter = search_data.get("location", "").strip()
    sub_location_filter = search_data.get("sub_location", "").strip()
    count_record_set = CountRecord.objects.filter(cycle=active_cycle, source="Manual Key-in")
    has_search = False
    if search:
        has_search = True
        count_record_set = count_record_set.filter(
            Q(count__count_number__icontains=search)
            | Q(sap_location__code__icontains=search)
            | Q(sap_location__department__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
            | Q(counter_name__icontains=search)
        )
    if sap_location_filter:
        has_search = True
        count_record_set = count_record_set.filter(
            Q(sap_location__code__icontains=sap_location_filter) | Q(sap_location__department__icontains=sap_location_filter)
        )

    context["search"] = search
    context["location_filter"] = location_filter
    context["sap_location_filter"] = sap_location_filter
    context["sub_location_filter"] = sub_location_filter
    context["count_record_set"] = count_record_set

    if has_search and not count_record_set.exists():
        messages.warning(request, "No Count Records found matching your search criteria.")
    return render(request, "count/batches.html", context)


@login_required
def count_template_download(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create count template. {msg}"))
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    excel_file = count_excel_bytes(plant)
    cycle_name = active_cycle_ref.name if active_cycle_ref else "no_active_cycle"
    return http_excel(excel_file, f"{plant.code}_Count_upload_Template_{cycle_name}")


@login_required
def count_file_upload(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to upload file. {msg}"))
        return redirect("count:count_upload")

    try:
        status, msg = count_batch_upload(
            request.FILES.get("file"),
            "Count Upload",
            plant=plant,
            note=request.POST.get("note", ""),
            cycle=active_cycle_ref,
            actor=request.user,
        )
        if status == "error":
            messages.error(request, msg)
            return redirect("count:count_upload")
        # TODO: Keep Log

        batch = msg
        count_batch_validate(batch)
        batch.refresh_from_db()

        if batch.error_count:
            messages.error(
                request,
                "Preview created with validation errors. Correct the workbook and upload it again.",
            )
        else:
            messages.success(
                request,
                "Preview is ready. Review every row before confirming the import.",
            )
        return redirect("count:count_batch", batch_id=batch.id)
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("count:count_upload")


@login_required
def count_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view counter roster. {msg}"))
        return redirect("count:count_upload")

    batch_ref = CountLoadBatch.objects.filter(id=batch_id, cycle__plant=plant).first()
    if not batch_ref:
        messages.error(request, "Batch does not exist.")
        return redirect("count:count_upload")

    # Get all rows first to calculate counts
    all_rows = TempCountLoadDetail.objects.filter(batch=batch_ref).order_by("id")
    error_count = all_rows.filter(is_valid=False).count()

    # Get filter parameter from request, default to 'errors' only if there are errors, otherwise 'all'
    default_filter = "errors" if error_count > 0 else "all"
    filter_type = request.GET.get("filter", default_filter).lower()
    if filter_type not in ["all", "ready", "errors"]:
        filter_type = default_filter

    # Apply filter to rows
    if filter_type == "ready":
        rows = all_rows.filter(is_valid=True)
    elif filter_type == "errors":
        rows = all_rows.filter(is_valid=False)
    else:  # "all"
        rows = all_rows

    context["batch"] = batch_ref
    context["rows"] = rows
    context["filter_type"] = filter_type
    context["total_count"] = all_rows.count()
    context["ready_count"] = all_rows.filter(is_valid=True).count()
    context["error_count"] = error_count
    return render(request, "count/batch_detail.html", context)


@login_required
def count_batch_confirm(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create part lists. {msg}"))
        return redirect("count:count_upload")
    new_records = []
    new_ex_records = []
    try:
        with transaction.atomic():
            batch_ref = (
                CountLoadBatch.objects.select_for_update().filter(id=batch_id, cycle=active_cycle_ref, cycle__plant=plant).first()
            )
            if not batch_ref:
                messages.error(request, "Batch does not exist in the active cycle.")
                return redirect("count:count_upload")
            if batch_ref.status != "Preview" or batch_ref.error_count:
                messages.error(request, "Only a valid preview batch can be confirmed.")
                return redirect("count:count_batch", batch_id=batch_ref.id)

            count_set = list(TempCountLoadDetail.objects.filter(batch=batch_ref, is_valid=True).order_by("id"))
            curr_time = timezone.now()
            for count_detail in count_set:
                if count_detail.part:
                    new_records.append(
                        CountRecord(
                            part=count_detail.part,
                            cycle=count_detail.cycle,
                            batch=batch_ref,
                            source=batch_ref.source,
                            source_record_key=str(count_detail.id),
                            sap_location=count_detail.sap_location,
                            physical_location=count_detail.physical_location,
                            sub_location=count_detail.sub_location,
                            tag_number=count_detail.tag_number,
                            quantity=count_detail.quantity,
                            counter_name=count_detail.counter_name,
                            initial_quantity=count_detail.quantity,
                            entered_by=curr_user,
                            entered_at=curr_time,
                            accepted_at=curr_time,
                            accepted_by=curr_user,
                            editable=False,
                        )
                    )
                else:
                    new_ex_records.append(
                        CountIntakeException(
                            batch=batch_ref,
                            cycle=active_cycle_ref,
                            raw_part_number=count_detail.raw_part_number,
                            source=batch_ref.source,
                            status="Pending",
                            tag_number=count_detail.tag_number,
                            quantity=count_detail.quantity,
                            counter_name=count_detail.counter_name,
                            sap_location=count_detail.sap_location,
                            physical_location=count_detail.physical_location,
                            sub_location=count_detail.sub_location,
                            created_at=curr_time,
                            created_by=curr_user,
                            updated_by=curr_user,
                        )
                    )
            new_count_record_set = CountRecord.objects.bulk_create(new_records)
            new_count_ex_record_set = CountIntakeException.objects.bulk_create(new_ex_records)

            batch_ref.status = "Imported"
            batch_ref.imported_count = len(new_records) + len(new_ex_records)
            batch_ref.updated_by = curr_user
            batch_ref.save(update_fields=["status", "imported_count", "updated_by", "updated_at"])
    except Exception as e:
        messages.error(request, f"Error importing count records. {clean_errors(e)}")
        return redirect("count:count_batch", batch_id=batch_id)

    for record in new_count_record_set:
        if record.tag_number:
            CycleTagDetail.objects.filter(tag_number=record.tag_number).update(
                count_record=record, exception_record=None, is_counted=True, updated_by=curr_user
            )
    for ex_record in new_count_ex_record_set:
        if ex_record.tag_number:
            CycleTagDetail.objects.filter(tag_number=ex_record.tag_number).update(
                count_record=None, exception_record=ex_record, is_counted=True, updated_by=curr_user
            )
    return redirect("count:count_batch", batch_id=batch_ref.id)
