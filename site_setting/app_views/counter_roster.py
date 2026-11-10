from access_control.models import CounterOnboardingRow, CounterRoster, UserOnboardingBatch
from core._imports_for_views import *
from core.excel_file_handler.setting_counter_roster import counter_batch_validate, counter_roster_excel_bytes, counter_batch_upload
from site_setting.models import SAPLocation

PERMISSION = "Setting.Counter"


@login_required
def counter_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view counter roster. {msg}"))
        return redirect("core:home")

    context["departments"] = set(SAPLocation.objects.filter(plant=plant, is_active=True).values_list("department", flat=True))
    context["sap_locations"] = dict(SAPLocation.objects.filter(plant=plant, is_active=True).values_list("code", "department"))

    roster = CounterRoster.objects.filter(plant=plant).select_related("sap_location", "updated_by").order_by("-id")

    search = request.GET.get("q", "").strip()
    if search:
        context["search"] = search
        roster = roster.filter(
            Q(employee_id__icontains=search)
            | Q(display_name__icontains=search)
            | Q(department__icontains=search)
            | Q(sap_location__code__icontains=search)
        )
    context["roster"] = roster
    return render(request, "site_setting/counter_setup.html", context)


@login_required
def counter_create(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create counter roster. {msg}"))
        return redirect("site_setting:counter_setup")

    post_data = request.POST
    employee_id = post_data.get("employee_id", "").strip()
    display_name = post_data.get("display_name", "").strip()
    department_id = post_data.get("department_id", "").strip()
    sap_location_id = post_data.get("sap_location_id", "").strip()

    if not employee_id or not display_name:
        messages.error(request, "Employee ID and display name cannot be empty. ")
        return redirect("site_setting:counter_setup")

    sap_location = SAPLocation.objects.filter(plant=plant, code=sap_location_id).first()
    if not sap_location:
        messages.error(request, "Selected SAP Location does NOT exist. ")
        return redirect("site_setting:counter_setup")

    curr_roster = CounterRoster.objects.filter(plant=plant, department=department_id, sap_location=sap_location).first()
    if curr_roster:
        messages.error(request, "Current Setup already exists. ")
        return redirect("site_setting:counter_setup")

    CounterRoster.objects.create(
        plant=plant,
        sap_location=sap_location,
        employee_id=employee_id,
        display_name=display_name,
        updated_by=curr_user,
        created_by=curr_user,
    )
    # TODO create Log
    return redirect("site_setting:counter_setup")


@login_required
def counter_status(request, ct_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to change counter roster. {msg}"))
        return redirect("site_setting:counter_setup")

    is_active = request.POST.get("is_active", "1") == "1"
    CounterRoster.objects.filter(id=ct_id).update(is_active=is_active)
    # TODO create Log
    return redirect("site_setting:counter_setup")


@login_required
def counter_template_download(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")
    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to download file. {msg}"))
        return redirect("site_setting:counter_setup")

    excel_file = counter_roster_excel_bytes(plant)

    return http_excel(excel_file, f"people_onboarding_{plant.code}")


@login_required
def counter_file_upload(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to upload file. {msg}"))
        return redirect("site_setting:counter_setup")

    try:
        status, msg = counter_batch_upload(request.FILES.get("workbook"), "Counter", plant=plant, actor=request.user)
        if status == "error":
            messages.error(request, msg)
            return redirect("site_setting:counter_setup")
        # TODO: Keep Log

        batch = msg
        counter_batch_validate(batch)
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
        return redirect("site_setting:counter_batch", batch_id=batch.id)
    except Exception as e:
        messages.error(request, f"File Validation Error, {clean_errors(e)}")
        return redirect("site_setting:counter_setup")


@login_required
def counter_batch(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view counter roster. {msg}"))
        return redirect("site_setting:counter_setup")

    batch_ref = UserOnboardingBatch.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    context["rows"] = CounterOnboardingRow.objects.filter(batch=batch_ref).order_by("row_number")
    return render(request, "site_setting/counter_batch.html", context)


@login_required
def counter_batch_confirm(request, batch_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to create counter roster. {msg}"))
        return redirect("site_setting:counter_setup")

    curr_time = datetime.now().astimezone()
    batch_ref = UserOnboardingBatch.objects.filter(id=batch_id).first()
    if not batch_ref:
        messages.error(request, "Batch doesn NOT exist. ")
    context["batch"] = batch_ref
    counter_set = CounterOnboardingRow.objects.filter(batch=batch_ref).order_by("row_number")
    existing_plant_counter = list(
        CounterRoster.objects.filter(plant=plant).values_list("employee_id", "display_name", "department", "sap_location__code")
    )

    new_counter_roster = []

    for counter_detail in counter_set:
        update_row = True
        if counter_detail.sap_location:
            if (
                counter_detail.employee_id,
                counter_detail.display_name,
                counter_detail.department,
                counter_detail.sap_location.code,
            ) in existing_plant_counter:
                update_row = False
        else:
            if (
                counter_detail.employee_id,
                counter_detail.display_name,
                counter_detail.department,
                None,
            ) in existing_plant_counter:
                update_row = False
        if update_row:
            new_counter_roster.append(
                CounterRoster(
                    plant=batch_ref.plant,
                    department=counter_detail.department,
                    sap_location=counter_detail.sap_location,
                    employee_id=counter_detail.employee_id,
                    display_name=counter_detail.display_name,
                    created_by=curr_user,
                    updated_by=curr_user,
                )
            )
            if counter_detail.sap_location:
                existing_plant_counter.append(
                    (
                        counter_detail.employee_id,
                        counter_detail.display_name,
                        counter_detail.department,
                        counter_detail.sap_location.code,
                    )
                )
            else:
                existing_plant_counter.append(
                    (
                        counter_detail.employee_id,
                        counter_detail.display_name,
                        counter_detail.department,
                        None,
                    )
                )

    # TODO: Add Log

    try:
        CounterRoster.objects.bulk_create(new_counter_roster)
    except Exception as e:
        messages.error(request, f"Error creating Counter Roster. {clean_errors(e)}")
        return redirect("site_setting:counter_batch", batch_id=batch_ref.id)

    batch_ref.status = "Imported"
    batch_ref.imported_count = len(new_counter_roster)
    batch_ref.skipped_row = counter_set.count() - len(new_counter_roster)
    batch_ref.confirmed_at = curr_time
    batch_ref.confirmed_by = curr_user
    batch_ref.updated_by = curr_user
    batch_ref.updated_at = curr_time
    batch_ref.save()
    return redirect("site_setting:counter_batch", batch_id=batch_ref.id)


@login_required
def data_entry_setup(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view counter roster. {msg}"))
        return redirect("core:home")

    context["departments"] = list(SAPLocation.objects.filter(plant=plant).values_list("department", flat=True))
    context["sap_locations"] = dict(SAPLocation.objects.filter(plant=plant).values("code", "department"))

    search = request.GET.get("q", "").strip()
    roster = CounterRoster.objects.filter(plant=plant).select_related("department", "sap_location", "updated_by")
    if search:
        context["search"] = search
        roster = roster.filter(
            Q(employee_id__icontains=search)
            | Q(display_name__icontains=search)
            | Q(email__icontains=search)
            | Q(department__name__icontains=search)
            | Q(sap_location__code__icontains=search)
        )
    return render(
        request,
        "site_setting/data_enrty_setup.html",
        context,
        # {
        #     "plant": plant,
        #     "sap_locations": SAPLocation.objects.filter(plant=plant, is_active=True).select_related("department"),
        #     "roster": roster,
        #     "search": search,
        # },
    )
