from core._imports_for_views import *
from core.context_processors import get_basic_info
from core.excel_file_handler.inventory_part import part_batch_upload, part_batch_validate, part_excel_bytes
from cycles.app_models.inventory_models import TempPartDetail, TempPartMain
from cycles.models import PartMaster

PERMISSION = "Book Inventary.PN List"


@login_required
def part_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view part list setup. {msg}"))
        return redirect("core:home")

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        return render(request, "inventory/parts.html", context)

    can_act, _ = check_permission(curr_user, plant, PERMISSION, True)
    context["may_change"] = can_act

    # !important TODO: Add file upload validator

    # Search and Filter
    search_data = request.GET
    search = search_data.get("search", "").strip()

    part_range_set = PartMaster.objects.filter(cycle=active_cycle)
    has_search = False
    if search:
        has_search = True
        part_range_set = part_range_set.filter(
            Q(part_number__icontains=search) | Q(description__icontains=search) | Q(business_unit__icontains=search)
        )

    context["search"] = search
    context["part_ranges"] = part_range_set

    if has_search and not part_range_set.exists():
        messages.warning(request, "No Part Numbers match this search..")
    return render(request, "inventory/parts.html", context)


@login_required
def part_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create part list. {msg}"))
        return redirect("core:home")

    curr_time = datetime.now().astimezone()
    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    post_data = request.POST
    part_number = post_data.get("part_number", "")
    description = post_data.get("description", "").strip()
    business_unit = post_data.get("business_unit", "").strip()
    price = post_data.get("price", "0")
    if not part_number:
        messages.error(request, "Part Number is required.")
        return redirect("cycles:part_setup")

    if not business_unit:
        messages.error(request, "Business Unit is required.")
        return redirect("cycles:part_setup")

    part_ref = PartMaster.objects.filter(cycle=active_cycle_ref, part_number=part_number).first()

    if part_ref:
        messages.error(request, f"Part {part_number} already exists in current cycle.")
        return redirect("cycles:part_setup")

    PartMaster.objects.create(
        cycle=active_cycle_ref,
        part_number=part_number,
        description=description,
        business_unit=business_unit,
        price=price,
        created_at=curr_time,
        created_by=curr_user,
        updated_by=curr_user,
    )

    messages.success(request, f"Part {part_number} created successfully.")
    return redirect("cycles:part_setup")


@login_required
def part_update(request, part_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create part list. {msg}"))
        return redirect("core:home")

    curr_time = datetime.now().astimezone()
    active_cycle_ref = context["cycle_ref"]
    if not active_cycle_ref:
        messages.error(request, "No active cycle is available.")
        return redirect("core:home")

    post_data = request.POST
    pprint(post_data)
    print(part_id)
    description = post_data.get("description", "").strip()
    business_unit = post_data.get("business_unit", "").strip()
    price = post_data.get("price", "0")

    if not business_unit:
        messages.error(request, "Business Unit is required.")
        return redirect("cycles:part_setup")

    part_ref = PartMaster.objects.filter(id=part_id).first()

    if not part_ref:
        messages.error(request, f"Part does NOT exist in current cycle.")
        return redirect("cycles:part_setup")

    part_ref.description = description
    part_ref.business_unit = business_unit
    part_ref.price = price
    part_ref.updated_by = curr_user
    part_ref.updated_at = curr_time
    part_ref.save()

    messages.success(request, f"Part {part_ref.part_number} updated successfully.")
    return redirect("cycles:part_setup")


@login_required
def part_template_download(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create part list. {msg}"))
        return redirect("core:home")

    active_cycle_ref = context["cycle_ref"]
    excel_file = part_excel_bytes(plant)
    cycle_name = active_cycle_ref.name if active_cycle_ref else "no_active_cycle"
    return http_excel(excel_file, f"Part List {plant.code} setup {cycle_name}")


@login_required
def part_file_upload(request):
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
        return redirect("cycles:part_setup")

    try:
        status, msg = part_batch_upload(
            request.FILES.get("part_file"), "PN List", plant=plant, cycle=active_cycle_ref, actor=request.user
        )
        if status == "error":
            messages.error(request, msg)
            return redirect("cycles:part_setup")
        # TODO: Keep Log

        batch = msg
        part_batch_validate(batch)
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
        return redirect("cycles:part_batch", batch_id=batch.id)
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("cycles:part_batch", batch_id=batch.id)


@login_required
def part_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view counter roster. {msg}"))
        return redirect("cycles:part_setup")

    batch_ref = TempPartMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    context["rows"] = TempPartDetail.objects.filter(batch=batch_ref).order_by("id")
    return render(request, "inventory/part_batch.html", context)


@login_required
def part_batch_confirm(request, batch_id):
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
        return redirect("cycles:part_setup")

    curr_time = datetime.now().astimezone()
    batch_ref = TempPartMain.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    part_set = TempPartDetail.objects.filter(batch=batch_ref).order_by("id")
    # TODO: Check if count started
    PartMaster.objects.filter(cycle=active_cycle_ref).delete()

    new_parts = []
    try:
        for part_detail in part_set:

            new_parts.append(
                PartMaster(
                    cycle=part_detail.cycle,
                    part_number=part_detail.part_number,
                    description=part_detail.description,
                    business_unit=part_detail.business_unit,
                    price=part_detail.price,
                    created_by=curr_user,
                    updated_by=curr_user,
                )
            )

        PartMaster.objects.bulk_create(new_parts)
    except Exception as e:
        messages.error(request, f"Error creating Cycle part lists. {str(e).replace('\n', ' ').replace('\r', '').strip()}")
        return redirect("cycles:part_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = part_set.count()
    batch_ref.skipped_row = 0
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    return redirect("cycles:part_batch", batch_id=batch_ref.id)
