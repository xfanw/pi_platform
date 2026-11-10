from django.db import transaction

from core._imports_for_views import *
from core.context_processors import get_basic_info
from core.excel_file_handler.inventory_ex_part import ex_part_batch_upload, ex_part_batch_validate, ex_part_excel_bytes
from cycles.models import ExcludedPart, PartMaster, TempExPartDetail, TempExPartMain
from site_setting.models import SAPLocation

PERMISSION = "Book Inventary.Exclude PN List"
REASON_MAX_LENGTH = 240


@login_required
def ex_part_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view the exclude PN list. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "inventory/ex_parts.html", context)

    can_act, _ = check_permission(curr_user, plant, PERMISSION, True)
    context["may_change"] = can_act

    search = request.GET.get("search", "").strip()
    sap_location_filter = request.GET.get("sap_location", "").strip()

    ex_set = ExcludedPart.objects.filter(cycle=active_cycle).filter(Q(sap_location__plant=plant) | Q(sap_location__isnull=True))
    ex_set = ex_set.select_related("part", "sap_location")
    if search:
        ex_set = ex_set.filter(
            Q(part__part_number__icontains=search) | Q(part__description__icontains=search) | Q(reason__icontains=search)
        )
    if sap_location_filter == "ALL":
        ex_set = ex_set.filter(sap_location__isnull=True)
    elif sap_location_filter:
        ex_set = ex_set.filter(sap_location__code=sap_location_filter)

    context["search"] = search
    context["sap_location_filter"] = sap_location_filter
    context["sap_locations"] = SAPLocation.objects.filter(plant=plant).order_by("code")
    context["ex_part_lines"] = ex_set.order_by("part__part_number", "sap_location__code")

    if (search or sap_location_filter) and not ex_set.exists():
        messages.warning(request, "No excluded P/Ns match this search.")
    return render(request, "inventory/ex_parts.html", context)


@login_required
def ex_part_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to change the exclude PN list. {msg}"))
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    post_data = request.POST
    part_number = post_data.get("part_number", "").strip()
    sap_location_code = post_data.get("sap_location", "").strip()
    reason = post_data.get("reason", "").strip()

    if not part_number or not sap_location_code or not reason:
        messages.error(request, "P/N, SAP Location and Reason are required.")
        return redirect("cycles:ex_part_setup")
    if len(reason) > REASON_MAX_LENGTH:
        messages.error(request, f"Reason cannot exceed {REASON_MAX_LENGTH} characters.")
        return redirect("cycles:ex_part_setup")

    part_ref = PartMaster.objects.filter(cycle=active_cycle_ref, part_number=part_number).first()
    if not part_ref:
        messages.error(request, f"P/N {part_number} is not in the current PN List.")
        return redirect("cycles:ex_part_setup")

    sap_location_ref = None
    if sap_location_code.upper() != "ALL":
        sap_location_ref = SAPLocation.objects.filter(plant=plant, code=sap_location_code).first()
        if not sap_location_ref:
            messages.error(request, f"SAP Location {sap_location_code} is not in this plant.")
            return redirect("cycles:ex_part_setup")

    if ExcludedPart.objects.filter(cycle=active_cycle_ref, sap_location=sap_location_ref, part=part_ref).exists():
        messages.error(request, f"P/N {part_number} is already excluded for {sap_location_code}.")
        return redirect("cycles:ex_part_setup")

    ExcludedPart.objects.create(
        cycle=active_cycle_ref,
        sap_location=sap_location_ref,
        part=part_ref,
        reason=reason,
        created_by=curr_user,
        updated_by=curr_user,
    )
    messages.success(request, f"P/N {part_number} excluded for {sap_location_code}.")
    return redirect("cycles:ex_part_setup")


@login_required
def ex_part_delete(request, ex_part_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to change the exclude PN list. {msg}"))
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    existing_ex_part = ExcludedPart.objects.filter(id=ex_part_id)
    if not existing_ex_part.exists():
        messages.error(request, "Excluded part does NOT exist.")
        return redirect("cycles:ex_part_setup")

    existing_ex_part.delete()
    messages.success(request, "Excluded part deleted successfully.")
    return redirect("cycles:ex_part_setup")


@login_required
def ex_part_template_download(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    active_cycle_ref = context["cycle_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to download the template. {msg}"))
        return redirect("core:home")

    excel_file = ex_part_excel_bytes(plant)
    cycle_name = active_cycle_ref.name if active_cycle_ref else "no_active_cycle"
    return http_excel(excel_file, f"Exclude PN {plant.code} setup {cycle_name}")


@login_required
def ex_part_file_upload(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    active_cycle_ref = context["cycle_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to upload file. {msg}"))
        return redirect("cycles:ex_part_setup")

    try:
        status, result = ex_part_batch_upload(
            request.FILES.get("ex_part_file"), "Exclude PN", plant=plant, cycle=active_cycle_ref, actor=curr_user
        )
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("cycles:ex_part_setup")

    if status == "error":
        messages.error(request, result)
        return redirect("cycles:ex_part_setup")

    ex_part_batch_validate(result)
    messages.success(request, "Preview is ready. Review every row before confirming the import.")
    return redirect("cycles:ex_part_batch", batch_id=result.id)


@login_required
def ex_part_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view this batch. {msg}"))
        return redirect("cycles:ex_part_setup")

    batch_ref = TempExPartMain.objects.filter(id=batch_id, cycle=context["cycle_ref"]).first()
    if not batch_ref:
        messages.error(request, "Batch does NOT exist.")
        return redirect("cycles:ex_part_setup")

    context["batch"] = batch_ref
    context["rows"] = TempExPartDetail.objects.filter(batch=batch_ref).select_related("part", "sap_location").order_by("id")
    return render(request, "inventory/ex_part_batch.html", context)


@login_required
def ex_part_batch_confirm(request, batch_id):
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
        messages.error(request, mark_safe(f"You do NOT have permission to import the exclude PN list. {msg}"))
        return redirect("cycles:ex_part_setup")

    if request.method != "POST":
        return redirect("cycles:ex_part_batch", batch_id=batch_id)

    batch_ref = TempExPartMain.objects.filter(id=batch_id, cycle=active_cycle_ref).first()
    if not batch_ref:
        messages.error(request, "Batch does NOT exist.")
        return redirect("cycles:ex_part_setup")

    if batch_ref.status != "Preview" or batch_ref.error_count:
        messages.error(request, "Only an error-free preview can be imported.")
        return redirect("cycles:ex_part_batch", batch_id=batch_ref.id)

    curr_time = datetime.now().astimezone()
    detail_set = TempExPartDetail.objects.filter(batch=batch_ref, is_valid=True).order_by("id")

    try:
        with transaction.atomic():
            ExcludedPart.objects.filter(cycle=active_cycle_ref).filter(
                Q(sap_location__plant=plant) | Q(sap_location__isnull=True)
            ).delete()
            ExcludedPart.objects.bulk_create(
                [
                    ExcludedPart(
                        cycle=detail.cycle,
                        sap_location=detail.sap_location,
                        part=detail.part,
                        reason=detail.reason,
                        created_by=curr_user,
                        updated_by=curr_user,
                    )
                    for detail in detail_set
                ]
            )
    except Exception as e:
        messages.error(request, f"Error importing exclude PN list. {clean_errors(e)}")
        return redirect("cycles:ex_part_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = detail_set.count()
    batch_ref.skipped_row = 0
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    messages.success(request, f"{batch_ref.imported_count} excluded P/N lines imported.")
    return redirect("cycles:ex_part_batch", batch_id=batch_ref.id)
