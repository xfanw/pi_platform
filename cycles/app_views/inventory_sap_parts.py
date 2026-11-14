from decimal import Decimal, InvalidOperation

from django.db import transaction

from core._imports_for_views import *
from core.context_processors import get_basic_info
from core.excel_file_handler.inventory_sap_part import sap_part_batch_upload, sap_part_batch_validate, sap_part_excel_bytes
from cycles.app_models.cycle_models import CycleSAPLocation
from cycles.models import BookInventoryLine, PartMaster, TempSAPPartDetail, TempSAPPartMain

PERMISSION = "Book Inventary.SAP Inventary"


def _parse_quantity(value):
    try:
        quantity = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    if not quantity.is_finite() or quantity < 0:
        return None
    return quantity


@login_required
def sap_part_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view SAP inventory. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "inventory/sap_parts.html", context)

    can_act, _ = check_permission(curr_user, plant, PERMISSION, True)
    context["may_change"] = can_act

    search = request.GET.get("search", "").strip()
    sap_location_filter = request.GET.get("sap_location", "").strip()

    line_set = BookInventoryLine.objects.filter(cycle=active_cycle, sap_location__plant=plant).select_related("part", "sap_location")
    if search:
        line_set = line_set.filter(
            Q(part__part_number__icontains=search) | Q(part__description__icontains=search) | Q(part__business_unit__icontains=search)
        )
    if sap_location_filter:
        line_set = line_set.filter(sap_location__code=sap_location_filter)

    context["search"] = search
    context["sap_location_filter"] = sap_location_filter
    context["sap_locations"] = CycleSAPLocation.objects.filter(plant=plant, cycle=active_cycle, is_active=True).order_by(
        "sap_location__department", "sap_location__code"
    )
    context["sap_part_lines"] = line_set.order_by("part__part_number", "sap_location__code")

    if (search or sap_location_filter) and not line_set.exists():
        messages.warning(request, "No SAP inventory lines match this search.")
    return render(request, "inventory/sap_parts.html", context)


@login_required
def sap_part_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to change SAP inventory. {msg}"))
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    post_data = request.POST
    part_number = post_data.get("part_number", "").strip()
    sap_location_code = post_data.get("sap_location", "").strip()
    quantity = _parse_quantity(post_data.get("quantity", ""))

    if not part_number or not sap_location_code:
        messages.error(request, "P/N and SAP Location are required.")
        return redirect("cycles:sap_part_setup")
    if quantity is None:
        messages.error(request, "Qty must be a number of 0 or more.")
        return redirect("cycles:sap_part_setup")

    part_ref = PartMaster.objects.filter(cycle=active_cycle_ref, part_number=part_number).first()
    if not part_ref:
        messages.error(request, f"P/N {part_number} is not in the current PN List.")
        return redirect("cycles:sap_part_setup")

    sap_location_ref = CycleSAPLocation.objects.filter(
        plant=plant, sap_location__code=sap_location_code, cycle=active_cycle_ref, is_active=True
    ).first()
    if not sap_location_ref:
        messages.error(request, f"SAP Location {sap_location_code} is not activated in this plant for this cycle.")
        return redirect("cycles:sap_part_setup")

    if BookInventoryLine.objects.filter(cycle=active_cycle_ref, sap_location=sap_location_ref.sap_location, part=part_ref).exists():
        messages.error(request, f"P/N {part_number} already exists in SAP Location {sap_location_code}. Edit its quantity instead.")
        return redirect("cycles:sap_part_setup")

    BookInventoryLine.objects.create(
        cycle=active_cycle_ref,
        sap_location=sap_location_ref.sap_location,
        part=part_ref,
        quantity=quantity,
        created_by=curr_user,
        updated_by=curr_user,
    )
    messages.success(request, f"P/N {part_number} added to SAP Location {sap_location_code}.")
    return redirect("cycles:sap_part_setup")


@login_required
def sap_part_update(request, line_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to change SAP inventory. {msg}"))
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    quantity = _parse_quantity(request.POST.get("quantity", ""))
    if quantity is None:
        messages.error(request, "Qty must be a number of 0 or more.")
        return redirect("cycles:sap_part_setup")

    sap_part_ref = BookInventoryLine.objects.filter(id=line_id).first()
    if not sap_part_ref:
        messages.error(request, "SAP inventory line does NOT exist in current cycle.")
        return redirect("cycles:sap_part_setup")

    sap_part_ref.quantity = quantity
    sap_part_ref.updated_by = curr_user
    sap_part_ref.updated_at = datetime.now().astimezone()
    sap_part_ref.save()
    messages.success(request, f"P/N {sap_part_ref.part.part_number} in {sap_part_ref.sap_location.code} updated successfully.")
    return redirect("cycles:sap_part_setup")


@login_required
def sap_part_template_download(request):
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

    excel_file = sap_part_excel_bytes(plant)
    cycle_name = active_cycle_ref.name if active_cycle_ref else "no_active_cycle"
    return http_excel(excel_file, f"SAP Inventory {plant.code} setup {cycle_name}")


@login_required
def sap_part_file_upload(request):
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
        return redirect("cycles:sap_part_setup")

    try:
        status, result = sap_part_batch_upload(
            request.FILES.get("sap_part_file"), "SAP Inventory", plant=plant, cycle=active_cycle_ref, actor=curr_user
        )
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("cycles:sap_part_setup")

    if status == "error":
        messages.error(request, result)
        return redirect("cycles:sap_part_setup")

    batch = result
    sap_part_batch_validate(batch)
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
    return redirect("cycles:sap_part_batch", batch_id=batch.id)


@login_required
def sap_part_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view this batch. {msg}"))
        return redirect("cycles:sap_part_setup")

    batch_ref = TempSAPPartMain.objects.filter(id=batch_id, cycle=context["cycle_ref"]).first()
    if not batch_ref:
        messages.error(request, "Batch does NOT exist.")
        return redirect("cycles:sap_part_setup")

    context["batch"] = batch_ref
    context["rows"] = TempSAPPartDetail.objects.filter(batch=batch_ref).select_related("part", "sap_location").order_by("id")
    return render(request, "inventory/sap_part_batch.html", context)


@login_required
def sap_part_batch_confirm(request, batch_id):
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
        messages.error(request, mark_safe(f"You do NOT have permission to import SAP inventory. {msg}"))
        return redirect("cycles:sap_part_setup")

    if request.method != "POST":
        return redirect("cycles:sap_part_batch", batch_id=batch_id)

    batch_ref = TempSAPPartMain.objects.filter(id=batch_id, cycle=active_cycle_ref).first()
    if not batch_ref:
        messages.error(request, "Batch does NOT exist.")
        return redirect("cycles:sap_part_setup")

    if batch_ref.status != "Preview" or batch_ref.error_count:
        messages.error(request, "Only an error-free preview can be imported.")
        return redirect("cycles:sap_part_batch", batch_id=batch_ref.id)

    curr_time = datetime.now().astimezone()
    detail_set = TempSAPPartDetail.objects.filter(batch=batch_ref, is_valid=True).order_by("id")

    try:
        with transaction.atomic():
            BookInventoryLine.objects.filter(cycle=active_cycle_ref, sap_location__plant=plant).delete()
            BookInventoryLine.objects.bulk_create(
                [
                    BookInventoryLine(
                        cycle=detail.cycle,
                        sap_location=detail.sap_location,
                        part=detail.part,
                        quantity=detail.quantity,
                        created_by=curr_user,
                        updated_by=curr_user,
                    )
                    for detail in detail_set
                ]
            )
    except Exception as e:
        messages.error(request, f"Error importing SAP inventory. {clean_errors(e)}")
        return redirect("cycles:sap_part_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = detail_set.count()
    batch_ref.skipped_row = 0
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    messages.success(request, f"{batch_ref.imported_count} SAP inventory lines imported.")
    return redirect("cycles:sap_part_batch", batch_id=batch_ref.id)
