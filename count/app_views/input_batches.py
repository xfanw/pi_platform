from core._imports_for_views import *
from core.context_processors import get_basic_info
from core.excel_file_handler.count_batch import count_batch_upload, count_batch_validate, count_excel_bytes
from count.models import CountRecord, TempCountLoadDetail, CountLoadBatch
from cycles.app_models.inventory_models import PartMaster, PartMaster, TempPartDetail, TempPartDetail, TempPartMain
from cycles.app_models.inventory_models import TempPartMain

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
    return http_excel(excel_file, f"{plant.code} Count upload Template {cycle_name}")


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
        return redirect("cycles:count_upload")

    try:
        status, msg = count_batch_upload(
            request.FILES.get("file"), "Count Upload", note=request.POST.get("note", ""), cycle=active_cycle_ref, actor=request.user
        )
        if status == "error":
            messages.error(request, msg)
            return redirect("cycles:count_upload")
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
        return redirect("cycles:count_batch", batch_id=batch.id)
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("cycles:count_upload")


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
        return redirect("cycles:count_upload")

    batch_ref = CountLoadBatch.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    context["rows"] = TempCountLoadDetail.objects.filter(batch=batch_ref).order_by("id")
    return render(request, "inventory/count_batch.html", context)


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
        return redirect("cycles:count_upload")

    curr_time = datetime.now().astimezone()
    batch_ref = TempPartMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    count_set = TempPartDetail.objects.filter(batch=batch_ref).order_by("id")
    # TODO: Check if count started
    PartMaster.objects.filter(cycle=active_cycle_ref).delete()

    new_parts = []
    try:
        for count_detail in count_set:

            new_parts.append(
                PartMaster(
                    cycle=count_detail.cycle,
                    count_number=count_detail.count_number,
                    description=count_detail.description,
                    business_unit=count_detail.business_unit,
                    price=count_detail.price,
                    created_by=curr_user,
                    updated_by=curr_user,
                )
            )

        PartMaster.objects.bulk_create(new_parts)
    except Exception as e:
        messages.error(request, f"Error creating Cycle part lists. {str(e).replace('\n', ' ').replace('\r', '').strip()}")
        return redirect("cycles:count_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = count_set.count()
    batch_ref.skipped_row = 0
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    return redirect("cycles:count_batch", batch_id=batch_ref.id)
