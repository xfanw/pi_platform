from collections import defaultdict
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from core.context_processors import get_basic_info
from core.init_functions.db_init import *
from site_setting.models import Plant
from django.contrib.auth import logout

# from apps.access_control.models import BusinessRole
# from apps.access_control.policy import (
#     active_assignments,
#     allowed_department_ids,
#     allowed_sap_location_ids,
#     require_any_plant_scope,
#     user_has_action,
#     user_has_scoped_action,
# )
# from apps.audit.models import (
#     AuditCandidate,
#     AuditErrorType,
#     AuditPlan,
#     AuditPlanStatus,
#     AuditRecord,
#     AuditResultStatus,
#     PageDensity,
# )
# from apps.audit.services import (
#     audit_accuracy,
#     build_audit_workbook,
#     create_audit_plan,
#     finalize_plan,
#     mark_pages_correct,
#     save_audit_result,
#     set_candidate_selection,
#     submit_audit_results,
#     update_and_regenerate_plan,
# )
# from apps.counting.effective import effective_count_records
# from apps.counting.models import (
#     BatchStatus,
#     CountIntakeException,
#     CountLoadBatch,
#     CountRecord,
#     CountCorrection,
#     CountSource,
#     CorrectionStatus,
#     ExceptionStatus,
#     VirtualTagScan,
#     VirtualTagScanStatus,
# )
# from apps.counting.services import (
#     accept_count_submission,
#     apply_count_correction,
#     create_count_exception,
#     reverse_count_batch,
#     review_count_correction,
#     resolve_count_exception,
#     submit_virtual_tag_scans,
#     submit_count_correction,
# )
# from apps.cycles.models import (
#     CyclePhysicalLocation,
#     CycleSAPLocation,
#     CycleStatus,
#     CycleSubLocation,
#     CycleTagRange,
#     PICycle,
# )
# from apps.cycles.services import close_cycle, create_open_cycle
# from apps.cycles.tag_ranges import tag_matches_range, tag_range_values_overlap
# from apps.captures.models import CaptureType, CaptureVarianceLine, PICapture
# from apps.captures.services import capture_readiness, cycle_close_readiness
# from apps.follow_up.models import FollowUpItem, TERMINAL_FOLLOW_UP_STATUSES
# from apps.inventory.models import BookInventoryLine, ExcludedPart, PartMaster
# from apps.inventory.services import (
#     add_exclusions,
#     delete_exclusion,
#     replace_book_lines,
#     replace_parts,
#     update_book_quantity,
#     upsert_book_lines,
#     upsert_parts,
# )
# from apps.plants.models import (
#     BusinessOption,
#     BusinessOptionCategory,
#     CounterRoster,
#     Department,
#     EntryMethod,
#     InventoryType,
#     PhysicalLocation,
#     Plant,
#     SAPLocation,
#     SubLocation,
#     VarianceSummaryGrouping,
# )
# from apps.plants.options import ensure_default_options, option_usage
# from apps.variance.engine import build_live_variance
# from apps.variance.formulas import variance_summary
# from apps.variance.models import (
#     PostBatch,
#     PostBatchLine,
#     PostBatchStatus,
#     VarianceResolution,
#     VarianceResolutionStatus,
# )
# from apps.variance.services import (
#     append_comment,
#     cancel_post_batch,
#     confirm_post_batch,
#     create_post_batch,
#     mark_not_post,
#     submit_lines_to_post,
# )

# from .forms import (
#     CounterRosterForm,
#     CycleCreateForm,
#     BookLineForm,
#     BookQuantityForm,
#     DepartmentForm,
#     PhysicalLocationForm,
#     PartForm,
#     PlantForm,
#     ManualCountForm,
#     SAPLocationForm,
#     SAP_LOCATION_COUNT_METHOD_CHOICES,
#     SubLocationForm,
#     TagRangeForm,
#     VirtualTagScanForm,
# )
# from .workbooks import (
#     read_book_rows,
#     data_workbook_response,
#     read_count_rows,
#     read_exclusion_rows,
#     read_location_rows,
#     read_part_rows,
#     read_sub_location_rows,
#     read_tag_range_rows,
#     workbook_response,
# )


# import uuid
def init_db(request):
    # init_admin_user()
    init_role()

    messages.success(request, "DB Init Finished")
    return redirect("core:home")


@login_required
def log_out(request):
    logout(request)
    return redirect("core:home")


def signup(request):
    if request.method == "POST":
        # Handle sign-up form submission
        username = request.POST.get("username")
        password = request.POST.get("password")
        # Add logic to create a new user
        # For example:
        # User.objects.create_user(username=username, password=password)
        messages.success(request, "Account created successfully. Please log in.")
        return redirect("core:login")
    return render(request, "core/signup.html")


@login_required
def home(request):
    context = get_basic_info(request)
    return render(request, "core/home.html", context)
    plant = _selected_plant(request, required=False)
    if plant is None:
        return render(request, "core/home.html", {"needs_first_plant": True})

    can_set_variance_default = user_has_scoped_action(request.user, "cycles.add_picycle", plant_id=plant.pk)
    if request.method == "POST" and request.POST.get("action") == "variance_summary_default":
        if not can_set_variance_default:
            raise PermissionDenied("Plant Admin access is required to set the dashboard default.")
        grouping = request.POST.get("variance_summary_default", "")
        if grouping not in VarianceSummaryGrouping.values:
            messages.error(request, "Select a valid Variance Summary default.")
        else:
            plant.variance_summary_default = grouping
            plant.updated_by = request.user
            plant.save(update_fields=["variance_summary_default", "updated_by", "updated_at"])
            messages.success(request, "Plant dashboard default updated.")
        return redirect("portal:home")

    cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()
    metrics = {
        "departments": Department.objects.filter(plant=plant, is_active=True).count(),
        "sap_locations": SAPLocation.objects.filter(plant=plant, is_active=True).count(),
        "physical_locations": PhysicalLocation.objects.filter(sap_location__plant=plant, is_active=True).count(),
        "parts": 0,
        "book_lines": 0,
        "count_records": 0,
        "book_qty": 0,
        "count_qty": 0,
    }
    if cycle:
        book = BookInventoryLine.objects.filter(cycle=cycle).aggregate(lines=Count("id"), qty=Sum("quantity"))
        counts = effective_count_records(cycle.pk).aggregate(lines=Count("record_id"), qty=Sum("quantity"))
        metrics.update(
            parts=PartMaster.objects.filter(cycle=cycle).count(),
            book_lines=book["lines"] or 0,
            count_records=counts["lines"] or 0,
            book_qty=book["qty"] or 0,
            count_qty=counts["qty"] or 0,
        )
    variance_metrics = None
    variance_group_rows = {}
    if cycle and user_has_action(request.user, "variance.view"):
        variance_locations, variance_allowed_ids = _variance_scope(request, plant, cycle)
        variance_lines = build_live_variance(cycle.pk, variance_allowed_ids)
        variance_metrics = variance_summary(variance_lines)
        variance_group_rows = {
            value: _variance_summary_group_rows(variance_lines, variance_locations, value) for value in VarianceSummaryGrouping.values
        }
    recent_captures = PICapture.objects.filter(cycle__plant=plant).select_related("cycle", "captured_by")[:5]
    return render(
        request,
        "portal/home.html",
        {
            "plant": plant,
            "cycle": cycle,
            "metrics": metrics,
            "variance_summary": variance_metrics,
            "variance_group_rows": variance_group_rows,
            "variance_group_choices": VarianceSummaryGrouping.choices,
            "variance_group_default": plant.variance_summary_default,
            "can_set_variance_default": can_set_variance_default,
            "recent_captures": recent_captures,
        },
    )


@login_required
def select_plant(request):
    from django.utils.http import url_has_allowed_host_and_scheme

    plant = Plant.objects.filter(pk=request.POST.get("plant_id")).first()
    if not plant:
        messages.error(request, "Selected plant does not exist.")
        return redirect("core:home")

    request.session["selected_plant_id"] = plant.pk
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("core:home")


@login_required
def select_role(request):
    from django.utils.http import url_has_allowed_host_and_scheme

    role = RoleAction.objects.filter(role=request.POST.get("role_id")).first()
    if not role:
        messages.error(request, "Selected Role does not exist.")
        return redirect("core:home")

    request.session["selected_role_id"] = role.role
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect("core:home")


# def _may_manage_plant(user, plant=None):
#     if user.is_superuser:
#         return True
#     if plant is None:
#         return active_assignments(user).filter(role=BusinessRole.Global Admin).exists()
#     return user_has_scoped_action(user, "cycles.add_picycle", plant_id=plant.pk)


# def _may_manage_plant_master(user, plant):
#     if user.is_superuser:
#         return True
#     if active_assignments(user).filter(role=BusinessRole.Global Admin).exists():
#         return True
#     if plant is None:
#         return False
#     return user_has_scoped_action(
#         user,
#         "plants.manage_plantsetup",
#         plant_id=plant.pk,
#     )


# def _may_create_plant(user):
#     return bool(user.is_superuser or active_assignments(user).filter(role=BusinessRole.Global Admin).exists())


def _open_cycle_for_plant(plant):
    if plant is None:
        return None
    return PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()


def _include_physical_location_in_open_cycle(physical_location, cycle):
    if cycle is None or not physical_location.is_active:
        return
    sap_is_active = CycleSAPLocation.objects.filter(
        cycle=cycle,
        sap_location=physical_location.sap_location,
        is_active=True,
    ).exists()
    if sap_is_active:
        CyclePhysicalLocation.objects.update_or_create(
            cycle=cycle,
            physical_location=physical_location,
            defaults={"is_active": True},
        )


def _include_sub_location_in_open_cycle(sub_location, cycle):
    if cycle is None or not sub_location.is_active:
        return
    _include_physical_location_in_open_cycle(sub_location.physical_location, cycle)
    physical_is_active = CyclePhysicalLocation.objects.filter(
        cycle=cycle,
        physical_location=sub_location.physical_location,
        is_active=True,
    ).exists()
    if physical_is_active:
        CycleSubLocation.objects.update_or_create(
            cycle=cycle,
            sub_location=sub_location,
            defaults={"is_active": True},
        )


def _tag_range_overlaps(cycle, sub_location, prefix, start_number, end_number):
    del sub_location  # Tag Numbers are unique across the entire PI Cycle.
    return any(
        tag_range_values_overlap(
            prefix,
            start_number,
            end_number,
            item.prefix,
            item.start_number,
            item.end_number,
        )
        for item in CycleTagRange.objects.filter(cycle=cycle).only("prefix", "start_number", "end_number")
    )


def _form_error_message(form):
    messages_by_field = []
    for field_name, errors in form.errors.items():
        label = form.fields[field_name].label if field_name in form.fields else "Form"
        messages_by_field.extend(f"{label}: {error}" for error in errors)
    return " ".join(messages_by_field)


def _book_cycle(request, view_action):
    plant = _selected_plant(request)
    cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()
    if cycle is None:
        messages.warning(request, "Open a PI Cycle before using Book Inventory.")
        return plant, None
    if not user_has_scoped_action(request.user, view_action, plant_id=plant.pk):
        raise PermissionDenied("Your role cannot access this Book Inventory page.")
    return plant, cycle


def _count_cycle(request, view_action):
    plant = _selected_plant(request)
    cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()
    if cycle is None:
        messages.warning(request, "Open a PI Cycle before using Count.")
        return plant, None
    if not user_has_action(request.user, view_action):
        raise PermissionDenied("Your role cannot access this Count page.")
    require_any_plant_scope(request.user, view_action, plant_id=plant.pk)
    return plant, cycle


def _variance_cycle(request):
    """Return the active cycle, or the latest closed cycle for read-only review."""
    plant = _selected_plant(request)
    if not user_has_action(request.user, "variance.view"):
        raise PermissionDenied("Your role cannot access Variance.")
    require_any_plant_scope(request.user, "variance.view", plant_id=plant.pk)
    cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()
    if cycle is None:
        cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.CLOSED).first()
    if cycle is None:
        messages.warning(request, "Create a PI Cycle before using Variance.")
    return plant, cycle


def _variance_scope(request, plant, cycle):
    allowed_ids = allowed_sap_location_ids(request.user, "variance.view", plant_id=plant.pk)
    query = SAPLocation.objects.filter(
        cycle_scope__cycle=cycle,
        cycle_scope__is_active=True,
        is_active=True,
    ).select_related("department")
    if allowed_ids is not None:
        query = query.filter(pk__in=allowed_ids)
    locations = list(query.distinct().order_by("department__sort_order", "department__name", "code"))
    return locations, {item.pk for item in locations}


def _variance_location_rows(lines, locations):
    grouped = defaultdict(list)
    for line in lines:
        grouped[line["sap_location_id"]].append(line)
    rows = []
    for location in locations:
        location_lines = grouped.get(location.pk, [])
        rows.append(
            {
                "location": location,
                "metric": variance_summary(location_lines),
                "part_count": len({line["part_id"] for line in location_lines}),
                "variance_part_count": len({line["part_id"] for line in location_lines if line["variance_quantity"] != 0}),
            }
        )
    rows.sort(key=lambda row: row["location"].inventory_type == "CS")
    return rows


def _variance_summary_group_rows(lines, locations, grouping):
    location_index = {item.pk: item for item in locations}
    grouped = defaultdict(list)
    metadata = {}
    for line in lines:
        location = location_index.get(line["sap_location_id"])
        if location is None:
            continue
        if grouping == VarianceSummaryGrouping.BUSINESS_UNIT:
            key = line["business_unit"] or "Unassigned"
            metadata[key] = {
                "label": key,
                "detail": "Business Unit",
                "filter_name": "business_unit",
                "filter_value": line["business_unit"],
            }
        elif grouping == VarianceSummaryGrouping.OWNERSHIP:
            key = location.department_id
            metadata[key] = {
                "label": location.department.name,
                "detail": "Ownership",
                "filter_name": "department",
                "filter_value": str(location.department_id),
            }
        else:
            key = location.pk
            metadata[key] = {
                "label": location.code,
                "detail": location.department.name,
                "filter_name": "sap_location",
                "filter_value": location.code,
            }
        grouped[key].append(line)
    rows = []
    for key, group_lines in grouped.items():
        types = {line["inventory_type"] for line in group_lines}
        rows.append(
            {
                **metadata[key],
                "metric": variance_summary(group_lines),
                "part_count": len({line["part_id"] for line in group_lines}),
                "variance_part_count": len({line["part_id"] for line in group_lines if line["variance_quantity"] != 0}),
                "has_tk": "TK" in types,
                "has_cs": "CS" in types,
                "inventory_type": " / ".join(sorted(types)),
            }
        )
    rows.sort(key=lambda row: row["label"].casefold())
    return rows


def _count_scope(request, plant, cycle, action):
    allowed_ids = allowed_sap_location_ids(request.user, action, plant_id=plant.pk)
    sap_query = SAPLocation.objects.filter(
        cycle_scope__cycle=cycle,
        cycle_scope__is_active=True,
        is_active=True,
    ).select_related("department")
    if allowed_ids is not None:
        sap_query = sap_query.filter(pk__in=allowed_ids)
    sap_locations = list(sap_query.distinct())
    sap_ids = {item.pk for item in sap_locations}
    physical_locations = list(
        PhysicalLocation.objects.filter(
            cycle_scope__cycle=cycle,
            cycle_scope__is_active=True,
            sap_location_id__in=sap_ids,
            is_active=True,
        ).select_related("sap_location")
    )
    physical_ids = {item.pk for item in physical_locations}
    sub_locations = list(
        SubLocation.objects.filter(
            cycle_scope__cycle=cycle,
            cycle_scope__is_active=True,
            physical_location_id__in=physical_ids,
            is_active=True,
        ).select_related("physical_location__sap_location")
    )
    return sap_locations, physical_locations, sub_locations


def _resolve_count_scope(
    *,
    sap_locations,
    physical_locations,
    sub_locations,
    sap_id=None,
    physical_id=None,
    sub_id=None,
    sap_code="",
    physical_name="",
    sub_name="",
):
    if sap_id:
        sap = next((item for item in sap_locations if item.pk == sap_id), None)
    else:
        sap = next(
            (item for item in sap_locations if item.code.upper() == sap_code.upper()),
            None,
        )
    if sap is None:
        raise ValidationError("SAP Location is not active or is outside your scope.")
    if physical_id:
        physical = next(
            (item for item in physical_locations if item.pk == physical_id and item.sap_location_id == sap.pk),
            None,
        )
    else:
        physical = next(
            (
                item
                for item in physical_locations
                if item.sap_location_id == sap.pk and item.name.strip().upper() == physical_name.strip().upper()
            ),
            None,
        )
    if physical is None:
        raise ValidationError("Location is required and must belong to the SAP Location.")
    sub = None
    if sub_id or sub_name:
        sub = next(
            (
                item
                for item in sub_locations
                if item.physical_location_id == physical.pk
                and ((sub_id and item.pk == sub_id) or (not sub_id and item.name.strip().upper() == sub_name.strip().upper()))
            ),
            None,
        )
        if sub is None:
            raise ValidationError("Sub-location does not belong to the selected Location.")
    return sap, physical, sub


def _show_validation_error(request, exc):
    for message in exc.messages[:10]:
        messages.error(request, message)
    if len(exc.messages) > 10:
        messages.error(request, f"{len(exc.messages) - 10} additional error(s) were omitted.")


def _show_upload_errors(request, errors):
    for message in errors[:10]:
        messages.error(request, message)
    if len(errors) > 10:
        messages.error(request, f"{len(errors) - 10} additional error(s) were omitted.")


@login_required
def part_list(request):
    plant, cycle = _book_cycle(request, "inventory.view_partmaster")
    if cycle is None:
        return redirect("portal:cycles")
    may_change = user_has_scoped_action(request.user, "inventory.change_partmaster", plant_id=plant.pk)

    if request.method == "POST":
        if not may_change:
            raise PermissionDenied("Your role cannot maintain the PN List.")
        action = request.POST.get("action")
        try:
            if action in {"add", "edit"}:
                form = PartForm(request.POST)
                if not form.is_valid():
                    raise ValidationError(_form_error_message(form))
                part_number = form.cleaned_data["part_number"]
                if action == "add" and PartMaster.objects.filter(cycle=cycle, part_number=part_number).exists():
                    raise ValidationError(f"P/N {part_number} already exists.")
                if action == "edit":
                    item = get_object_or_404(PartMaster, pk=request.POST.get("part_id"), cycle=cycle)
                    if item.part_number != part_number:
                        raise ValidationError("P/N cannot be changed after it is created.")
                upsert_parts(cycle_id=cycle.pk, rows=[form.cleaned_data], user=request.user)
                messages.success(request, f"P/N {part_number} saved.")
            elif action == "upload":
                upload = request.FILES.get("file")
                if not upload:
                    raise ValidationError("Choose a completed PN List .xlsx file.")
                rows, errors = read_part_rows(upload)
                if errors:
                    _show_upload_errors(request, errors)
                elif not rows:
                    raise ValidationError("The workbook has no PN data rows.")
                else:
                    replace_parts(cycle_id=cycle.pk, rows=rows, user=request.user)
                    messages.success(
                        request,
                        f"PN List replaced with {len(rows):,} P/N(s). Existing SAP Book lines and exclusions were cleared.",
                    )
            else:
                raise ValidationError("Unknown PN List action.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:part-list")

    search = request.GET.get("search", "").strip()
    query = PartMaster.objects.filter(cycle=cycle)
    if search:
        query = query.filter(Q(part_number__icontains=search) | Q(description__icontains=search) | Q(business_unit__icontains=search))
    total = query.count()
    return render(
        request,
        "portal/parts.html",
        {
            "plant": plant,
            "cycle": cycle,
            "rows": query[:300],
            "total": total,
            "search": search,
            "may_change": may_change,
        },
    )


@login_required
def part_template(request):
    _, cycle = _book_cycle(request, "inventory.view_partmaster")
    if cycle is None:
        return redirect("portal:cycles")
    return workbook_response(
        "pn_list_template.xlsx",
        "PN List",
        ("PN", "Description", "MAP$", "BU"),
        ("68-104848-01", "Example part", 125.50, "SAVBU"),
        (20, 48, 14, 18),
    )


@login_required
def book_inventory(request):
    plant, cycle = _book_cycle(request, "inventory.view_bookinventoryline")
    if cycle is None:
        return redirect("portal:cycles")
    may_change = user_has_scoped_action(request.user, "inventory.change_bookinventoryline", plant_id=plant.pk)
    visible_ids = allowed_sap_location_ids(request.user, "inventory.view_bookinventoryline", plant_id=plant.pk)
    scope_query = SAPLocation.objects.filter(cycle_scope__cycle=cycle, cycle_scope__is_active=True, is_active=True).select_related(
        "department"
    )
    if visible_ids is not None:
        scope_query = scope_query.filter(pk__in=visible_ids)
    sap_locations = list(scope_query.distinct())
    sap_by_id = {item.pk: item for item in sap_locations}

    if request.method == "POST":
        if not may_change:
            raise PermissionDenied("Your role cannot maintain SAP Inventory.")
        action = request.POST.get("action")
        try:
            if action == "add":
                form = BookLineForm(request.POST)
                if not form.is_valid():
                    raise ValidationError(_form_error_message(form))
                sap = sap_by_id.get(form.cleaned_data["sap_location_id"])
                if sap is None:
                    raise PermissionDenied("That SAP Location is outside your scope.")
                row = {
                    "part_number": form.cleaned_data["part_number"],
                    "sap_location_code": sap.code,
                    "quantity": form.cleaned_data["quantity"],
                    "source_batch_key": "manual",
                }
                if BookInventoryLine.objects.filter(
                    cycle=cycle,
                    sap_location=sap,
                    part__part_number=row["part_number"],
                ).exists():
                    raise ValidationError(f'{sap.code} / {row["part_number"]} already exists. Edit its Qty in the table.')
                upsert_book_lines(cycle_id=cycle.pk, rows=[row], user=request.user)
                messages.success(request, "SAP Inventory line added.")
            elif action == "edit":
                form = BookQuantityForm(request.POST)
                if not form.is_valid():
                    raise ValidationError(_form_error_message(form))
                line = get_object_or_404(BookInventoryLine, pk=request.POST.get("line_id"), cycle=cycle)
                if line.sap_location_id not in sap_by_id:
                    raise PermissionDenied("That line is outside your scope.")
                update_book_quantity(
                    line_id=line.pk,
                    quantity=form.cleaned_data["quantity"],
                    user=request.user,
                )
                messages.success(request, "Book Qty updated.")
            elif action == "upload":
                change_scope_ids = allowed_sap_location_ids(
                    request.user,
                    "inventory.change_bookinventoryline",
                    plant_id=plant.pk,
                )
                if change_scope_ids is not None:
                    raise PermissionDenied("A full SAP Inventory replacement requires Plant-wide Book access.")
                upload = request.FILES.get("file")
                if not upload:
                    raise ValidationError("Choose a completed SAP Inventory .xlsx file.")
                rows, errors = read_book_rows(upload)
                if errors:
                    _show_upload_errors(request, errors)
                elif not rows:
                    raise ValidationError("The workbook has no SAP Inventory rows.")
                else:
                    replace_book_lines(cycle_id=cycle.pk, rows=rows, user=request.user)
                    messages.success(request, f"SAP Inventory replaced with {len(rows):,} line(s).")
            else:
                raise ValidationError("Unknown SAP Inventory action.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:book-inventory")

    search = request.GET.get("search", "").strip()
    sap_filter = request.GET.get("sap_location", "").strip()
    query = BookInventoryLine.objects.filter(cycle=cycle, sap_location_id__in=sap_by_id).select_related(
        "part", "sap_location__department", "updated_by"
    )
    if search:
        query = query.filter(Q(part__part_number__icontains=search) | Q(part__description__icontains=search))
    if sap_filter:
        query = query.filter(sap_location__code=sap_filter)
    total = query.count()
    return render(
        request,
        "portal/book_inventory.html",
        {
            "plant": plant,
            "cycle": cycle,
            "rows": query[:300],
            "total": total,
            "search": search,
            "sap_filter": sap_filter,
            "sap_locations": sap_locations,
            "may_change": may_change,
        },
    )


@login_required
def book_template(request):
    _, cycle = _book_cycle(request, "inventory.view_bookinventoryline")
    if cycle is None:
        return redirect("portal:cycles")
    return workbook_response(
        "sap_inventory_template.xlsx",
        "SAP Inventory",
        ("PN", "SAP Location", "Qty"),
        ("68-104848-01", "0CHK", 25),
        (20, 18, 14),
    )


def _split_part_numbers(value):
    import re

    return list(dict.fromkeys(token.strip().upper() for token in re.split(r"[\s,;]+", value or "") if token.strip()))


@login_required
def excluded_parts(request):
    plant, cycle = _book_cycle(request, "inventory.view_excludedpart")
    if cycle is None:
        return redirect("portal:cycles")
    may_change = user_has_scoped_action(request.user, "inventory.add_excludedpart", plant_id=plant.pk)
    visible_ids = allowed_sap_location_ids(request.user, "inventory.view_excludedpart", plant_id=plant.pk)
    scope_query = SAPLocation.objects.filter(cycle_scope__cycle=cycle, cycle_scope__is_active=True, is_active=True).select_related(
        "department"
    )
    if visible_ids is not None:
        scope_query = scope_query.filter(pk__in=visible_ids)
    sap_locations = list(scope_query.distinct())
    sap_by_id = {item.pk: item for item in sap_locations}

    if request.method == "POST":
        if not may_change:
            raise PermissionDenied("Your role cannot maintain exclusions.")
        action = request.POST.get("action")
        try:
            if action == "manual":
                part_numbers = _split_part_numbers(request.POST.get("part_numbers"))
                if not part_numbers:
                    raise ValidationError("Enter at least one P/N.")
                if len(part_numbers) > 100:
                    raise ValidationError("Manual paste is limited to 100 unique P/Ns.")
                selected_ids = [int(value) for value in request.POST.getlist("sap_location_ids") if value.isdigit()]
                selected = [sap_by_id[item_id] for item_id in selected_ids if item_id in sap_by_id]
                if selected_ids and len(selected) != len(set(selected_ids)):
                    raise PermissionDenied("One or more SAP Locations are outside your scope.")
                rows = [
                    {
                        "part_number": pn,
                        "sap_location_code": sap.code if sap else "ALL",
                        "reason": request.POST.get("reason", "").strip(),
                    }
                    for pn in part_numbers
                    for sap in (selected or [None])
                ]
                created, skipped = add_exclusions(cycle_id=cycle.pk, rows=rows, user=request.user)
                messages.success(request, f"{created:,} exclusion(s) added.")
                _show_upload_errors(request, skipped)
            elif action == "upload":
                upload = request.FILES.get("file")
                if not upload:
                    raise ValidationError("Choose a completed Exclude PN .xlsx file.")
                rows, errors = read_exclusion_rows(upload)
                if errors:
                    _show_upload_errors(request, errors)
                elif not rows:
                    raise ValidationError("The workbook has no exclusion rows.")
                else:
                    created, skipped = add_exclusions(cycle_id=cycle.pk, rows=rows, user=request.user)
                    messages.success(request, f"{created:,} exclusion(s) added.")
                    _show_upload_errors(request, skipped)
            else:
                raise ValidationError("Unknown exclusion action.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:excluded-parts")

    search = request.GET.get("search", "").strip()
    query = (
        ExcludedPart.objects.filter(cycle=cycle)
        .filter(Q(sap_location_id__in=sap_by_id) | Q(sap_location__isnull=True))
        .select_related("part", "sap_location", "created_by")
    )
    if search:
        query = query.filter(
            Q(part__part_number__icontains=search)
            | Q(part__description__icontains=search)
            | Q(sap_location__code__icontains=search)
            | Q(reason__icontains=search)
            | Q(created_by__username__icontains=search)
        )
    return render(
        request,
        "portal/excluded_parts.html",
        {
            "plant": plant,
            "cycle": cycle,
            "rows": query[:500],
            "total": query.count(),
            "search": search,
            "sap_locations": sap_locations,
            "may_change": may_change,
        },
    )


@login_required
@require_POST
def excluded_part_delete(request, exclusion_id):
    plant, cycle = _book_cycle(request, "inventory.view_excludedpart")
    if cycle is None:
        return redirect("portal:cycles")
    item = get_object_or_404(ExcludedPart, pk=exclusion_id, cycle=cycle)
    if item.sap_location and item.sap_location.plant_id != plant.pk:
        raise PermissionDenied("That exclusion is outside your Plant.")
    delete_exclusion(exclusion_id=item.pk, user=request.user)
    messages.success(request, "Exclusion removed.")
    return redirect("portal:excluded-parts")


@login_required
def exclusion_template(request):
    _, cycle = _book_cycle(request, "inventory.view_excludedpart")
    if cycle is None:
        return redirect("portal:cycles")
    return workbook_response(
        "exclude_pn_template.xlsx",
        "Exclude PN",
        ("PN", "SAP Location or ALL", "Reason"),
        ("68-104848-01", "ALL", "Approved exclusion"),
        (20, 24, 42),
    )


def _accept_or_hold_count(
    *,
    cycle,
    source,
    sap,
    physical,
    sub,
    part_number,
    quantity,
    counter_name,
    tag_number,
    request_user,
    idempotency_key,
    batch=None,
    source_record_key="",
):
    part = PartMaster.objects.filter(cycle=cycle, part_number=part_number.strip().upper()).first()
    if part:
        record, created = accept_count_submission(
            idempotency_key=idempotency_key,
            cycle_id=cycle.pk,
            source=source,
            sap_location=sap,
            physical_location=physical,
            sub_location=sub,
            tag_number=tag_number,
            part=part,
            quantity=quantity,
            counter_name=counter_name,
            entered_by=request_user,
            batch=batch,
            source_record_key=source_record_key,
        )
        return "accepted", created, record
    item, created = create_count_exception(
        idempotency_key=idempotency_key,
        cycle_id=cycle.pk,
        source=source,
        sap_location=sap,
        physical_location=physical,
        sub_location=sub,
        tag_number=tag_number,
        raw_part_number=part_number,
        quantity=quantity,
        counter_name=counter_name,
        entered_by=request_user,
        batch=batch,
    )
    return "pending", created, item


def _process_count_upload(*, request, cycle, source, sap_locations, physical_locations, sub_locations):
    upload = request.FILES.get("file")
    channel_name = "WMS Feed" if source == CountSource.WMS else "Count Upload"
    if not upload:
        raise ValidationError(f"Choose a completed {channel_name} .xlsx file.")
    rows, parse_errors = read_count_rows(upload)
    if not rows and not parse_errors:
        raise ValidationError("The workbook has no Count rows.")
    batch = CountLoadBatch.objects.create(
        cycle=cycle,
        source=source,
        source_filename=upload.name,
        note=request.POST.get("note", "").strip(),
        status=BatchStatus.PROCESSING,
        row_count=len(rows) + len(parse_errors),
        created_by=request.user,
        updated_by=request.user,
    )
    accepted = pending = 0
    row_errors = list(parse_errors)
    for row in rows:
        row_number = row["row_number"]
        try:
            sap, physical, sub = _resolve_count_scope(
                sap_locations=sap_locations,
                physical_locations=physical_locations,
                sub_locations=sub_locations,
                sap_code=row["sap_location_code"],
                physical_name=row["physical_location_name"],
                sub_name=row["sub_location_name"],
            )
            outcome, created, _ = _accept_or_hold_count(
                cycle=cycle,
                source=source,
                sap=sap,
                physical=physical,
                sub=sub,
                part_number=row["part_number"],
                quantity=row["quantity"],
                counter_name=row["counter_name"],
                tag_number=row["tag_number"],
                request_user=request.user,
                idempotency_key=f"{source.lower()}:{batch.pk}:{row_number}",
                batch=batch,
                source_record_key=f"{batch.pk}:{row_number}",
            )
            if created and outcome == "accepted":
                accepted += 1
            elif created:
                pending += 1
        except (ValidationError, PermissionDenied) as exc:
            details = getattr(exc, "messages", [str(exc)])
            row_errors.extend(f"Row {row_number}: {message}" for message in details)
    batch.accepted_count = accepted
    batch.pending_count = pending
    batch.rejected_count = len(row_errors)
    batch.error_details = row_errors
    if row_errors and not (accepted or pending):
        batch.status = BatchStatus.FAILED
    elif row_errors:
        batch.status = BatchStatus.PARTIAL
    else:
        batch.status = BatchStatus.ACCEPTED
    batch.updated_by = request.user
    batch.save()
    messages.success(
        request,
        f"{channel_name} processed: {accepted:,} accepted, {pending:,} pending, " f"{len(row_errors):,} error(s).",
    )
    _show_upload_errors(request, row_errors)
    return batch


def _count_page_scope(request):
    plant, cycle = _count_cycle(request, "counting.add_countrecord")
    if cycle is None:
        return plant, cycle, [], [], []
    sap_locations, physical_locations, sub_locations = _count_scope(request, plant, cycle, "counting.add_countrecord")
    return plant, cycle, sap_locations, physical_locations, sub_locations


@login_required
def count_intake(request):
    return redirect("portal:count-tag")


@login_required
def count_tag(request):
    plant, cycle, sap_locations, physical_locations, sub_locations = _count_page_scope(request)
    if cycle is None:
        return redirect("portal:cycles")

    if request.method == "POST":
        try:
            form = ManualCountForm(request.POST)
            if not form.is_valid():
                raise ValidationError(_form_error_message(form))
            data = form.cleaned_data
            sap, physical, sub = _resolve_count_scope(
                sap_locations=sap_locations,
                physical_locations=physical_locations,
                sub_locations=sub_locations,
                sap_id=data["sap_location_id"],
                physical_id=data["physical_location_id"],
                sub_id=data["sub_location_id"],
            )
            source = CountSource.TAG if data["tag_number"] else CountSource.MANUAL
            outcome, created, _ = _accept_or_hold_count(
                cycle=cycle,
                source=source,
                sap=sap,
                physical=physical,
                sub=sub,
                part_number=data["part_number"],
                quantity=data["quantity"],
                counter_name=data["counter_name"],
                tag_number=data["tag_number"],
                request_user=request.user,
                idempotency_key=data["submission_key"],
            )
            if not created:
                messages.warning(request, "This submission was already received; no duplicate was added.")
            elif outcome == "accepted":
                messages.success(request, "Count Record accepted.")
            else:
                messages.warning(request, "Unknown P/N held in Pending Station for review.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:count-tag")

    scoped_sap_ids = [sap.pk for sap in sap_locations]
    counter_roster = (
        CounterRoster.objects.filter(plant=plant, is_active=True)
        .filter(Q(sap_location__isnull=True) | Q(sap_location_id__in=scoped_sap_ids))
        .select_related("department", "sap_location")
    )
    search = request.GET.get("search", "").strip()
    sap_filter = request.GET.get("sap_location", "").strip()
    counted_query = (
        effective_count_records(cycle.pk, scoped_sap_ids)
        .filter(tag_number__gt="")
        .select_related("sap_location", "physical_location", "sub_location", "part")
    )
    if sap_filter:
        counted_query = counted_query.filter(sap_location_id=sap_filter)
    if search:
        counted_query = counted_query.filter(
            Q(tag_number__icontains=search)
            | Q(effective_part_number__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
        )
    counted_rows = list(counted_query.order_by("-accepted_at")[:500])
    counted_tag_values = effective_count_records(cycle.pk).filter(tag_number__gt="").values_list("tag_number", flat=True)
    counted_tags = {value.casefold() for value in counted_tag_values}
    pending_tag_values = CountIntakeException.objects.filter(
        cycle=cycle,
        status=ExceptionStatus.PENDING,
        tag_number__gt="",
    ).values_list("tag_number", flat=True)
    pending_tags = {value.casefold() for value in pending_tag_values}
    empty_tags = []
    tag_ranges = CycleTagRange.objects.filter(
        cycle=cycle,
        sub_location__physical_location__sap_location_id__in=scoped_sap_ids,
    ).select_related("sub_location__physical_location__sap_location")
    if sap_filter:
        tag_ranges = tag_ranges.filter(sub_location__physical_location__sap_location_id=sap_filter)
    tag_ranges = list(
        tag_ranges.order_by(
            "sub_location__physical_location__sap_location__code",
            "sub_location__physical_location__name",
            "sub_location__name",
            "prefix",
            "start_number",
            "pk",
        )
    )
    all_cycle_tag_ranges = list(CycleTagRange.objects.filter(cycle=cycle).only("prefix", "start_number", "end_number"))
    seen_tags = set()
    ambiguous_tag_count = 0
    for tag_range in tag_ranges:
        for number in range(tag_range.start_number, tag_range.end_number + 1):
            tag = f"{tag_range.prefix}{number}"
            normalized_tag = tag.casefold()
            if normalized_tag in seen_tags:
                continue
            seen_tags.add(normalized_tag)
            if normalized_tag in counted_tags or normalized_tag in pending_tags:
                continue
            search_text = " ".join(
                (
                    tag,
                    tag_range.sub_location.name,
                    tag_range.sub_location.physical_location.name,
                    tag_range.sub_location.physical_location.sap_location.code,
                )
            ).lower()
            if search and search.lower() not in search_text:
                continue
            if sum(tag_matches_range(tag, item) for item in all_cycle_tag_ranges) != 1:
                ambiguous_tag_count += 1
                continue
            empty_tags.append({"tag": tag, "sub": tag_range.sub_location})
            if len(empty_tags) >= 500:
                break
        if len(empty_tags) >= 500:
            break
    return render(
        request,
        "portal/count_tag.html",
        {
            "plant": plant,
            "cycle": cycle,
            "sap_locations": sap_locations,
            "physical_locations": physical_locations,
            "sub_locations": sub_locations,
            "counter_roster": counter_roster,
            "empty_tags": empty_tags,
            "ambiguous_tag_count": ambiguous_tag_count,
            "counted_rows": counted_rows,
            "search": search,
            "sap_filter": sap_filter,
            "submission_key": uuid.uuid4().hex,
        },
    )


def _count_batch_page(request, source):
    plant, cycle, sap_locations, physical_locations, sub_locations = _count_page_scope(request)
    if cycle is None:
        return redirect("portal:cycles")
    if request.method == "POST":
        try:
            _process_count_upload(
                request=request,
                cycle=cycle,
                source=source,
                sap_locations=sap_locations,
                physical_locations=physical_locations,
                sub_locations=sub_locations,
            )
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:count-wms" if source == CountSource.WMS else "portal:count-upload")
    batches = CountLoadBatch.objects.filter(cycle=cycle, source=source).select_related("created_by").order_by("-created_at")[:50]
    return render(
        request,
        "portal/count_batches.html",
        {
            "plant": plant,
            "cycle": cycle,
            "source": source,
            "batches": batches,
            "page_title": "WMS Feed" if source == CountSource.WMS else "Count Result Upload",
        },
    )


@login_required
def count_upload(request):
    return _count_batch_page(request, CountSource.UPLOAD)


@login_required
def count_wms(request):
    return _count_batch_page(request, CountSource.WMS)


@login_required
def count_virtual_tag(request):
    plant, cycle, sap_locations, physical_locations, sub_locations = _count_page_scope(request)
    if cycle is None:
        return redirect("portal:cycles")
    if request.method == "POST":
        try:
            form = VirtualTagScanForm(request.POST)
            if not form.is_valid():
                raise ValidationError(_form_error_message(form))
            data = form.cleaned_data
            sap, physical, sub = _resolve_count_scope(
                sap_locations=sap_locations,
                physical_locations=physical_locations,
                sub_locations=sub_locations,
                sap_id=data["sap_location_id"],
                physical_id=data["physical_location_id"],
                sub_id=data["sub_location_id"],
            )
            scans, created_count = submit_virtual_tag_scans(
                idempotency_key=data["submission_key"],
                cycle_id=cycle.pk,
                sap_location=sap,
                physical_location=physical,
                sub_location=sub,
                serial_numbers=data["serial_numbers"],
                submitted_by=request.user,
            )
            existing_count = len(scans) - created_count
            if created_count:
                summary = f"{created_count} S/N queued for BOM lookup."
                if existing_count:
                    summary += f" {existing_count} already existed; no duplicate was added."
                messages.success(
                    request,
                    summary,
                )
            else:
                messages.warning(
                    request,
                    f"All {existing_count} S/N were already scanned; no duplicate was added.",
                )
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:count-virtual-tag")

    search = request.GET.get("search", "").strip()
    sap_filter = request.GET.get("sap_location", "").strip()
    status_filter = request.GET.get("status", "").strip()
    scans = (
        VirtualTagScan.objects.filter(
            cycle=cycle,
            sap_location_id__in=[item.pk for item in sap_locations],
        )
        .select_related(
            "sap_location",
            "physical_location",
            "sub_location",
            "submitted_by",
            "resolved_by",
            "batch",
        )
        .prefetch_related("components")
    )
    if search:
        scans = scans.filter(
            Q(serial_number__icontains=search)
            | Q(external_reference__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
        )
    if sap_filter:
        scans = scans.filter(sap_location_id=sap_filter)
    if status_filter in VirtualTagScanStatus.values:
        scans = scans.filter(status=status_filter)
    return render(
        request,
        "portal/count_virtual_tag.html",
        {
            "plant": plant,
            "cycle": cycle,
            "sap_locations": sap_locations,
            "physical_locations": physical_locations,
            "sub_locations": sub_locations,
            "scans": scans.order_by("-created_at")[:100],
            "status_choices": VirtualTagScanStatus.choices,
            "search": search,
            "sap_filter": sap_filter,
            "status_filter": status_filter,
            "submission_key": uuid.uuid4().hex,
        },
    )


@login_required
def count_virtual_tag_detail(request, scan_id):
    plant, cycle = _count_cycle(request, "counting.view_countrecord")
    if cycle is None:
        return redirect("portal:cycles")
    allowed_ids = allowed_sap_location_ids(request.user, "counting.view_countrecord", plant_id=plant.pk)
    scans = (
        VirtualTagScan.objects.filter(cycle=cycle)
        .select_related(
            "sap_location",
            "physical_location",
            "sub_location",
            "submitted_by",
            "resolved_by",
            "batch",
        )
        .prefetch_related("components__part")
    )
    if allowed_ids is not None:
        scans = scans.filter(sap_location_id__in=allowed_ids)
    scan = get_object_or_404(scans, pk=scan_id)
    return render(
        request,
        "portal/count_virtual_tag_detail.html",
        {"plant": plant, "cycle": cycle, "scan": scan},
    )


@login_required
def count_batch_detail(request, batch_id):
    plant, cycle = _count_cycle(request, "counting.view_countrecord")
    if cycle is None:
        return redirect("portal:cycles")
    batch = get_object_or_404(CountLoadBatch.objects.select_related("created_by"), pk=batch_id, cycle=cycle)
    records = (
        effective_count_records(cycle.pk, include_reversed=True)
        .filter(batch=batch)
        .select_related("sap_location", "physical_location", "sub_location", "part")
        .order_by("accepted_at")
    )
    pending = CountIntakeException.objects.filter(batch=batch).select_related("sap_location", "physical_location", "sub_location")
    return render(
        request,
        "portal/count_batch_detail.html",
        {
            "plant": plant,
            "cycle": cycle,
            "batch": batch,
            "records": records[:1000],
            "pending": pending[:1000],
        },
    )


@login_required
@require_POST
def count_batch_reverse(request, batch_id):
    _, cycle = _count_cycle(request, "counting.add_countrecord")
    if cycle is None:
        return redirect("portal:cycles")
    batch = get_object_or_404(CountLoadBatch, pk=batch_id, cycle=cycle)
    try:
        reverse_count_batch(
            batch_id=batch.pk,
            expected_row_version=int(request.POST.get("row_version", batch.row_version)),
            user=request.user,
        )
        messages.success(request, f"Batch {batch.batch_id} reversed. Its accepted rows no longer affect Count Results.")
    except (ValidationError, ValueError) as exc:
        _show_validation_error(request, exc)
    return redirect("portal:count-batch-detail", batch_id=batch.pk)


@login_required
@require_POST
def count_record_correct(request, record_id):
    plant, cycle = _count_cycle(request, "counting.add_countcorrection")
    if cycle is None:
        return redirect("portal:cycles")
    record = get_object_or_404(
        effective_count_records(cycle.pk, include_reversed=True).select_related("batch", "part"),
        pk=record_id,
    )
    try:
        part_number = request.POST.get("corrected_part_number", "").strip().upper()
        quantity_text = request.POST.get("corrected_quantity", "").strip()
        corrected_part = None
        corrected_quantity = None
        if part_number and part_number != record.effective_part_number:
            corrected_part = get_object_or_404(PartMaster, cycle=cycle, part_number=part_number)
        if quantity_text:
            corrected_quantity = Decimal(quantity_text)
        submit_count_correction(
            count_record=record,
            corrected_part=corrected_part,
            corrected_quantity=corrected_quantity,
            reason_code=request.POST.get("reason_code", "Count intake correction"),
            comment=request.POST.get("comment", ""),
            user=request.user,
        )
        messages.success(request, "Correction submitted for independent review. The original Count Record was not overwritten.")
    except (ValidationError, InvalidOperation) as exc:
        _show_validation_error(request, exc)
    if record.batch_id:
        return redirect("portal:count-batch-detail", batch_id=record.batch_id)
    return redirect("portal:count-tag")


@login_required
def count_template(request):
    _, cycle = _count_cycle(request, "counting.add_countrecord")
    if cycle is None:
        return redirect("portal:cycles")
    return workbook_response(
        "count_upload_template.xlsx",
        "Count Upload",
        ("PN", "SAP Location", "Location", "Sub Location", "Tag Number", "Qty", "Counter"),
        ("68-104848-01", "0CHK", "ASSEMBLY #1", "BLADES-A-LINE", "935256", 17, "Counter Name"),
        (20, 18, 26, 26, 16, 12, 22),
    )


@login_required
def count_results(request):
    plant, cycle = _count_cycle(request, "counting.view_countrecord")
    if cycle is None:
        return redirect("portal:cycles")
    sap_locations, _, _ = _count_scope(request, plant, cycle, "counting.view_countrecord")
    sap_ids = {item.pk for item in sap_locations}
    query = effective_count_records(cycle.pk, sap_ids).select_related(
        "sap_location__department",
        "physical_location",
        "sub_location",
        "part",
        "entered_by",
    )
    search = request.GET.get("search", "").strip()
    sap_filter = request.GET.get("sap_location", "").strip()
    source_filter = request.GET.get("source", "").strip()
    if search:
        query = query.filter(
            Q(effective_part_number__icontains=search)
            | Q(effective_description__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
            | Q(tag_number__icontains=search)
            | Q(counter_name__icontains=search)
        )
    if sap_filter:
        query = query.filter(sap_location__code=sap_filter)
    if source_filter:
        query = query.filter(source=source_filter)
    query = query.order_by("effective_part_number", "sap_location__code", "accepted_at")
    if request.GET.get("export") == "1":
        return data_workbook_response(
            f"count_results_{cycle.pk}.xlsx",
            "Count Results",
            (
                "PN",
                "Description",
                "Ownership",
                "SAP Location",
                "Location",
                "Sub Location",
                "Tag Number",
                "Qty",
                "Counter",
                "Source",
                "Entered By",
                "Entered At",
                "Record ID",
            ),
            (
                (
                    item.effective_part_number,
                    item.effective_description,
                    item.sap_location.department.name,
                    item.sap_location.code,
                    item.physical_location.name if item.physical_location else "",
                    item.sub_location.name if item.sub_location else "",
                    item.tag_number,
                    item.effective_quantity,
                    item.counter_name,
                    item.source,
                    item.entered_by.username if item.entered_by else "",
                    item.entered_at.replace(tzinfo=None),
                    str(item.record_id),
                )
                for item in query
            ),
            (20, 42, 20, 16, 26, 26, 16, 12, 22, 14, 16, 20, 38),
        )
    total = query.count()
    return render(
        request,
        "portal/count_results.html",
        {
            "plant": plant,
            "cycle": cycle,
            "rows": query[:500],
            "total": total,
            "search": search,
            "sap_filter": sap_filter,
            "source_filter": source_filter,
            "sap_locations": sap_locations,
            "source_choices": CountSource.choices,
        },
    )


@login_required
def pending_station(request):
    plant, cycle = _count_cycle(request, "counting.view_countintakeexception")
    if cycle is None:
        return redirect("portal:cycles")
    sap_locations, _, _ = _count_scope(request, plant, cycle, "counting.view_countintakeexception")
    sap_ids = {item.pk for item in sap_locations}
    review_sap_ids = allowed_sap_location_ids(
        request.user,
        "counting.review_countintakeexception",
        plant_id=plant.pk,
    )
    review_scope_ids = sap_ids if review_sap_ids is None else sap_ids.intersection(review_sap_ids)
    may_review = bool(user_has_action(request.user, "counting.review_countintakeexception") and review_scope_ids)
    if request.method == "POST":
        if not may_review:
            raise PermissionDenied("Your role cannot review Pending Count records.")
        try:
            item = CountIntakeException.objects.filter(
                pk=request.POST.get("exception_id"),
                cycle=cycle,
                sap_location_id__in=review_scope_ids,
            ).first()
            if item is None:
                messages.error(
                    request,
                    "That Pending Station record is no longer available in your review scope. Refresh and try again.",
                )
                return redirect("portal:pending-station")
            decision = request.POST.get("decision", "")
            mapped_part = None
            new_data = None
            if decision == ExceptionStatus.MAPPED:
                mapped_part = PartMaster.objects.filter(
                    cycle=cycle,
                    part_number=request.POST.get("mapped_part_number", "").strip().upper(),
                ).first()
            elif decision == ExceptionStatus.APPROVED_NEW_PART:
                part_form = PartForm(
                    {
                        "part_number": item.raw_part_number,
                        "description": request.POST.get("description", ""),
                        "price": request.POST.get("price", "0"),
                        "business_unit": request.POST.get("business_unit", ""),
                    }
                )
                if not part_form.is_valid():
                    raise ValidationError(_form_error_message(part_form))
                new_data = part_form.cleaned_data
            resolved, record = resolve_count_exception(
                exception_id=item.pk,
                decision=decision,
                expected_row_version=int(request.POST.get("row_version", "0")),
                user=request.user,
                mapped_part=mapped_part,
                new_part_data=new_data,
                reason=request.POST.get("reason", ""),
            )
            if record:
                messages.success(request, f"{resolved.raw_part_number} resolved and moved to Count Results.")
            else:
                messages.success(request, f"{resolved.raw_part_number} rejected and retained in history.")
        except (ValidationError, ValueError) as exc:
            if isinstance(exc, ValidationError):
                _show_validation_error(request, exc)
            else:
                messages.error(request, "The Pending record version is invalid.")
        return redirect("portal:pending-station")

    status_filter = request.GET.get("status", ExceptionStatus.PENDING)
    if status_filter not in ExceptionStatus.values and status_filter != "ALL":
        status_filter = ExceptionStatus.PENDING
    search = request.GET.get("search", "").strip()
    query = CountIntakeException.objects.filter(cycle=cycle, sap_location_id__in=sap_ids).select_related(
        "sap_location__department",
        "physical_location",
        "sub_location",
        "created_by",
        "reviewed_by",
        "disposition_part",
    )
    if status_filter != "ALL":
        query = query.filter(status=status_filter)
    if search:
        query = query.filter(
            Q(raw_part_number__icontains=search)
            | Q(sap_location__code__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(sub_location__name__icontains=search)
            | Q(tag_number__icontains=search)
            | Q(counter_name__icontains=search)
        )
    pending_count = CountIntakeException.objects.filter(
        cycle=cycle, sap_location_id__in=sap_ids, status=ExceptionStatus.PENDING
    ).count()
    return render(
        request,
        "portal/pending_station.html",
        {
            "plant": plant,
            "cycle": cycle,
            "rows": query.order_by("-created_at")[:300],
            "total": query.count(),
            "pending_count": pending_count,
            "search": search,
            "status_filter": status_filter,
            "status_choices": ExceptionStatus.choices,
            "may_review": may_review,
        },
    )


@login_required
def location_management(request):
    return _location_management_page(request, "location")


@login_required
def sub_location_management(request):
    return _location_management_page(request, "sub_location")


@login_required
def tag_range_management(request):
    return _location_management_page(request, "tag_range")


def _location_management_page(request, page):
    plant = _selected_plant(request)
    if not _may_manage_plant(request.user, plant):
        raise PermissionDenied("Location setup requires Plant Admin access.")
    cycle = _open_cycle_for_plant(plant)

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            with transaction.atomic():
                if action == "add_physical":
                    form = PhysicalLocationForm(request.POST)
                    if not form.is_valid():
                        raise ValidationError(_form_error_message(form))
                    sap_location = SAPLocation.objects.get(
                        pk=form.cleaned_data.pop("sap_location_id"),
                        plant=plant,
                        is_active=True,
                    )
                    if PhysicalLocation.objects.filter(
                        sap_location=sap_location,
                        name__iexact=form.cleaned_data["name"],
                    ).exists():
                        raise ValidationError("That Location already exists under this SAP Location.")
                    item = PhysicalLocation.objects.create(
                        sap_location=sap_location,
                        **form.cleaned_data,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    _include_physical_location_in_open_cycle(item, cycle)
                    messages.success(request, "Location added.")

                elif action == "add_sub":
                    form = SubLocationForm(request.POST)
                    if not form.is_valid():
                        raise ValidationError(_form_error_message(form))
                    physical = PhysicalLocation.objects.get(
                        pk=form.cleaned_data.pop("physical_location_id"),
                        sap_location__plant=plant,
                        is_active=True,
                    )
                    if SubLocation.objects.filter(
                        physical_location=physical,
                        name__iexact=form.cleaned_data["name"],
                    ).exists():
                        raise ValidationError("That Sub-location already exists under this Location.")
                    item = SubLocation.objects.create(
                        physical_location=physical,
                        **form.cleaned_data,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    _include_sub_location_in_open_cycle(item, cycle)
                    messages.success(request, "Sub-location added.")

                elif action == "add_tag_range":
                    if cycle is None:
                        raise ValidationError("Open a PI Cycle before adding a Tag Range.")
                    form = TagRangeForm(request.POST)
                    if not form.is_valid():
                        raise ValidationError(_form_error_message(form))
                    sub_location = SubLocation.objects.get(
                        pk=form.cleaned_data.pop("sub_location_id"),
                        physical_location__sap_location__plant=plant,
                        is_active=True,
                        cycle_scope__cycle=cycle,
                        cycle_scope__is_active=True,
                    )
                    range_values = {
                        "prefix": "",
                        "start_number": form.cleaned_data["start_number"],
                        "end_number": form.cleaned_data["end_number"],
                    }
                    PICycle.objects.select_for_update().get(pk=cycle.pk)
                    if _tag_range_overlaps(cycle, sub_location, **range_values):
                        raise ValidationError(
                            "This range overlaps an existing range and would duplicate Tag Numbers already configured elsewhere in the current PI."
                        )
                    CycleTagRange.objects.create(
                        cycle=cycle,
                        sub_location=sub_location,
                        **range_values,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    messages.success(request, "Tag Range added to the current PI.")

                elif action == "upload_physical":
                    upload = request.FILES.get("file")
                    if not upload:
                        raise ValidationError("Choose a completed Location .xlsx file.")
                    rows, errors = read_location_rows(upload)
                    if errors:
                        _show_upload_errors(request, errors)
                    elif not rows:
                        raise ValidationError("The workbook has no Location rows.")
                    else:
                        created = skipped = 0
                        row_errors = []
                        for row in rows:
                            sap = SAPLocation.objects.filter(
                                plant=plant,
                                code__iexact=row["sap_location_code"],
                                is_active=True,
                            ).first()
                            if sap is None:
                                row_errors.append(f'Row {row["row_number"]}: SAP Location {row["sap_location_code"]} was not found.')
                                continue
                            existing = PhysicalLocation.objects.filter(sap_location=sap, name__iexact=row["name"]).first()
                            if existing is not None:
                                _include_physical_location_in_open_cycle(existing, cycle)
                                skipped += 1
                                continue
                            item = PhysicalLocation.objects.create(
                                sap_location=sap,
                                name=row["name"],
                                created_by=request.user,
                                updated_by=request.user,
                            )
                            _include_physical_location_in_open_cycle(item, cycle)
                            created += 1
                        messages.success(
                            request,
                            f"{created:,} Location(s) imported; {skipped:,} existing row(s) reused in the current PI.",
                        )
                        _show_upload_errors(request, row_errors)

                elif action == "upload_sub":
                    upload = request.FILES.get("file")
                    if not upload:
                        raise ValidationError("Choose a completed Sub-location .xlsx file.")
                    rows, errors = read_sub_location_rows(upload)
                    if errors:
                        _show_upload_errors(request, errors)
                    elif not rows:
                        raise ValidationError("The workbook has no Sub-location rows.")
                    else:
                        created = reused = scope_added = scope_existing = 0
                        row_errors = []
                        for row in rows:
                            physical = PhysicalLocation.objects.filter(
                                sap_location__plant=plant,
                                sap_location__code__iexact=row["sap_location_code"],
                                name__iexact=row["physical_location_name"],
                                is_active=True,
                            ).first()
                            if physical is None:
                                row_errors.append(
                                    f'Row {row["row_number"]}: parent {row["sap_location_code"]} / {row["physical_location_name"]} was not found.'
                                )
                                continue
                            existing = SubLocation.objects.filter(physical_location=physical, name__iexact=row["name"]).first()
                            if existing is not None:
                                already_in_scope = bool(
                                    cycle
                                    and CycleSubLocation.objects.filter(
                                        cycle=cycle,
                                        sub_location=existing,
                                        is_active=True,
                                    ).exists()
                                )
                                _include_sub_location_in_open_cycle(existing, cycle)
                                reused += 1
                                if already_in_scope:
                                    scope_existing += 1
                                elif (
                                    cycle
                                    and CycleSubLocation.objects.filter(
                                        cycle=cycle,
                                        sub_location=existing,
                                        is_active=True,
                                    ).exists()
                                ):
                                    scope_added += 1
                                continue
                            item = SubLocation.objects.create(
                                physical_location=physical,
                                name=row["name"],
                                created_by=request.user,
                                updated_by=request.user,
                            )
                            _include_sub_location_in_open_cycle(item, cycle)
                            created += 1
                            if (
                                cycle
                                and CycleSubLocation.objects.filter(
                                    cycle=cycle,
                                    sub_location=item,
                                    is_active=True,
                                ).exists()
                            ):
                                scope_added += 1
                        if cycle:
                            messages.success(
                                request,
                                f"Plant Master: {created:,} new and {reused:,} existing Sub-location(s). "
                                f"Current PI: {scope_added:,} added and {scope_existing:,} already included. "
                                "Only rows present in this workbook are added to the current PI.",
                            )
                        else:
                            messages.success(
                                request,
                                f"Plant Master: {created:,} new and {reused:,} existing Sub-location(s). "
                                "No open PI Cycle was changed.",
                            )
                        _show_upload_errors(request, row_errors)

                elif action == "upload_tag_range":
                    if cycle is None:
                        raise ValidationError("Open a PI Cycle before uploading Tag Ranges.")
                    upload = request.FILES.get("file")
                    if not upload:
                        raise ValidationError("Choose a completed Tag Range .xlsx file.")
                    rows, errors = read_tag_range_rows(upload)
                    if errors:
                        _show_upload_errors(request, errors)
                    elif not rows:
                        raise ValidationError("The workbook has no Tag Range rows.")
                    else:
                        PICycle.objects.select_for_update().get(pk=cycle.pk)
                        created = skipped = 0
                        row_errors = []
                        for row in rows:
                            sub = SubLocation.objects.filter(
                                physical_location__sap_location__plant=plant,
                                physical_location__sap_location__code__iexact=row["sap_location_code"],
                                physical_location__name__iexact=row["physical_location_name"],
                                name__iexact=row["sub_location_name"],
                                is_active=True,
                                cycle_scope__cycle=cycle,
                                cycle_scope__is_active=True,
                            ).first()
                            if sub is None:
                                row_errors.append(
                                    f'Row {row["row_number"]}: current-PI Sub-location {row["sap_location_code"]} / {row["physical_location_name"]} / {row["sub_location_name"]} was not found.'
                                )
                                continue
                            range_values = {
                                "prefix": row["prefix"],
                                "start_number": row["start_number"],
                                "end_number": row["end_number"],
                            }
                            if CycleTagRange.objects.filter(cycle=cycle, sub_location=sub, **range_values).exists():
                                skipped += 1
                                continue
                            if _tag_range_overlaps(cycle, sub, **range_values):
                                row_errors.append(
                                    f'Row {row["row_number"]}: range overlaps an existing range and would duplicate Tag Numbers already configured elsewhere in the current PI.'
                                )
                                continue
                            CycleTagRange.objects.create(
                                cycle=cycle,
                                sub_location=sub,
                                **range_values,
                                created_by=request.user,
                                updated_by=request.user,
                            )
                            created += 1
                        messages.success(
                            request,
                            f"{created:,} Tag Range(s) imported; {skipped:,} exact duplicate(s) skipped.",
                        )
                        _show_upload_errors(request, row_errors)

                elif action == "update_physical":
                    item = PhysicalLocation.objects.get(
                        pk=request.POST.get("location_id"),
                        sap_location__plant=plant,
                    )
                    item.is_active = request.POST.get("is_active") == "1"
                    item.updated_by = request.user
                    item.save(update_fields=["is_active", "updated_by", "updated_at"])
                    if cycle:
                        if item.is_active:
                            _include_physical_location_in_open_cycle(item, cycle)
                        else:
                            CyclePhysicalLocation.objects.filter(cycle=cycle, physical_location=item).update(is_active=False)
                            CycleSubLocation.objects.filter(
                                cycle=cycle,
                                sub_location__physical_location=item,
                            ).update(is_active=False)
                    messages.success(request, "Location updated.")

                elif action == "update_sub":
                    item = SubLocation.objects.get(
                        pk=request.POST.get("sub_location_id"),
                        physical_location__sap_location__plant=plant,
                    )
                    item.is_active = request.POST.get("is_active") == "1"
                    item.updated_by = request.user
                    item.save(update_fields=["is_active", "updated_by", "updated_at"])
                    if cycle:
                        if item.is_active:
                            _include_sub_location_in_open_cycle(item, cycle)
                        else:
                            CycleSubLocation.objects.filter(cycle=cycle, sub_location=item).update(is_active=False)
                    messages.success(request, "Sub-location updated.")

                elif action == "delete_tag_range":
                    if cycle is None:
                        raise ValidationError("There is no open PI Tag Range to remove.")
                    item = CycleTagRange.objects.get(
                        pk=request.POST.get("tag_range_id"),
                        cycle=cycle,
                        sub_location__physical_location__sap_location__plant=plant,
                    )
                    used = any(
                        tag_matches_range(value, item)
                        for value in CountRecord.objects.filter(
                            cycle=cycle,
                            sub_location=item.sub_location,
                        )
                        .exclude(tag_number="")
                        .values_list("tag_number", flat=True)
                    )
                    if used:
                        raise ValidationError("This Tag Range is already referenced by accepted Count Records and cannot be deleted.")
                    item.delete()
                    messages.success(request, "Unused Tag Range removed.")
                else:
                    raise ValidationError("Unknown Location setup action.")
        except (
            IntegrityError,
            SAPLocation.DoesNotExist,
            PhysicalLocation.DoesNotExist,
            SubLocation.DoesNotExist,
            CycleTagRange.DoesNotExist,
        ):
            messages.error(request, "That value already exists or is outside this Plant/current PI.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        destination = {
            "add_physical": "portal:location-management",
            "upload_physical": "portal:location-management",
            "update_physical": "portal:location-management",
            "add_sub": "portal:sub-location-management",
            "upload_sub": "portal:sub-location-management",
            "update_sub": "portal:sub-location-management",
            "add_tag_range": "portal:tag-range-management",
            "upload_tag_range": "portal:tag-range-management",
            "delete_tag_range": "portal:tag-range-management",
        }.get(
            action,
            {
                "location": "portal:location-management",
                "sub_location": "portal:sub-location-management",
                "tag_range": "portal:tag-range-management",
            }[page],
        )
        return redirect(destination)

    search = request.GET.get("q", "").strip()
    physical_query = (
        PhysicalLocation.objects.filter(sap_location__plant=plant)
        .select_related("sap_location__department")
        .annotate(sub_location_count=Count("sub_locations", distinct=True))
    )
    current_sub_scope = (
        CycleSubLocation.objects.filter(
            cycle=cycle,
            sub_location_id=OuterRef("pk"),
            is_active=True,
        )
        if cycle
        else CycleSubLocation.objects.none()
    )
    sub_query = (
        SubLocation.objects.filter(physical_location__sap_location__plant=plant)
        .select_related("physical_location__sap_location__department")
        .annotate(in_current_pi=Exists(current_sub_scope))
    )
    tag_query = CycleTagRange.objects.none()
    if cycle:
        tag_query = CycleTagRange.objects.filter(cycle=cycle).select_related("sub_location__physical_location__sap_location")
    if search:
        physical_query = physical_query.filter(
            Q(name__icontains=search) | Q(sap_location__code__icontains=search) | Q(sap_location__department__name__icontains=search)
        )
        sub_query = sub_query.filter(
            Q(name__icontains=search)
            | Q(physical_location__name__icontains=search)
            | Q(physical_location__sap_location__code__icontains=search)
        )
        tag_query = tag_query.filter(
            Q(sub_location__name__icontains=search)
            | Q(sub_location__physical_location__name__icontains=search)
            | Q(sub_location__physical_location__sap_location__code__icontains=search)
        )
    sap_location_filter = request.GET.get("sap_location", "").strip()
    location_filter = request.GET.get("location", "").strip()
    sub_location_filter = request.GET.get("sub_location", "").strip()
    department_filter = request.GET.get("department", "").strip()
    status_filter = request.GET.get("status", "").strip().upper()
    scope_filter = request.GET.get("scope", "").strip().upper()
    if page == "sub_location" and not scope_filter:
        scope_filter = "CURRENT" if cycle else "ALL"
    if sap_location_filter.isdigit():
        physical_query = physical_query.filter(sap_location_id=sap_location_filter)
        sub_query = sub_query.filter(physical_location__sap_location_id=sap_location_filter)
        tag_query = tag_query.filter(sub_location__physical_location__sap_location_id=sap_location_filter)
    if department_filter.isdigit():
        physical_query = physical_query.filter(sap_location__department_id=department_filter)
    if location_filter.isdigit():
        sub_query = sub_query.filter(physical_location_id=location_filter)
        tag_query = tag_query.filter(sub_location__physical_location_id=location_filter)
    if sub_location_filter.isdigit():
        tag_query = tag_query.filter(sub_location_id=sub_location_filter)
    if status_filter in {"ACTIVE", "INACTIVE"}:
        is_active = status_filter == "ACTIVE"
        physical_query = physical_query.filter(is_active=is_active)
        sub_query = sub_query.filter(is_active=is_active)
    if scope_filter == "CURRENT" and cycle:
        sub_query = sub_query.filter(in_current_pi=True)
    elif scope_filter == "OUTSIDE" and cycle:
        sub_query = sub_query.filter(in_current_pi=False)
    tag_ranges = list(tag_query)
    for item in tag_ranges:
        item.tag_count = item.end_number - item.start_number + 1
    cycle_sub_locations = (
        SubLocation.objects.filter(
            cycle_scope__cycle=cycle,
            cycle_scope__is_active=True,
            is_active=True,
            physical_location__is_active=True,
            physical_location__sap_location__plant=plant,
        ).select_related("physical_location__sap_location")
        if cycle
        else SubLocation.objects.none()
    )
    cycle_physical_locations = (
        PhysicalLocation.objects.filter(
            cycle_scope__cycle=cycle,
            cycle_scope__is_active=True,
            is_active=True,
            sap_location__plant=plant,
        )
        .select_related("sap_location")
        .distinct()
        .order_by("sap_location__code", "name")
        if cycle
        else PhysicalLocation.objects.none()
    )
    return render(
        request,
        {
            "location": "portal/location_management.html",
            "sub_location": "portal/sub_location_management.html",
            "tag_range": "portal/tag_range_management.html",
        }[page],
        {
            "plant": plant,
            "cycle": cycle,
            "sap_locations": SAPLocation.objects.filter(plant=plant, is_active=True).select_related("department"),
            "physical_locations": PhysicalLocation.objects.filter(sap_location__plant=plant, is_active=True).select_related(
                "sap_location"
            ),
            "cycle_sub_locations": cycle_sub_locations,
            "cycle_physical_locations": cycle_physical_locations,
            "location_rows": physical_query,
            "sub_location_rows": sub_query,
            "tag_ranges": tag_ranges,
            "search": search,
            "departments": Department.objects.filter(plant=plant, is_active=True).order_by("sort_order", "name"),
            "sap_location_filter": sap_location_filter,
            "location_filter": location_filter,
            "sub_location_filter": sub_location_filter,
            "department_filter": department_filter,
            "status_filter": status_filter,
            "scope_filter": scope_filter,
        },
    )


@login_required
def location_template(request):
    plant = _selected_plant(request)
    if not _may_manage_plant(request.user, plant):
        raise PermissionDenied("Location setup requires Plant Admin access.")
    return workbook_response(
        "location_setup_template.xlsx",
        "Locations",
        ("SAP Location", "Location"),
        ("0CHK", "ASSEMBLY #1"),
        (18, 32),
    )


@login_required
def sub_location_template(request):
    plant = _selected_plant(request)
    if not _may_manage_plant(request.user, plant):
        raise PermissionDenied("Location setup requires Plant Admin access.")
    return workbook_response(
        "sub_location_setup_template.xlsx",
        "Sub Locations",
        ("SAP Location", "Location", "Sub Location"),
        ("0CHK", "ASSEMBLY #1", "BLADES-A-LINE"),
        (18, 32, 32),
    )


@login_required
def tag_range_template(request):
    plant = _selected_plant(request)
    if not _may_manage_plant(request.user, plant):
        raise PermissionDenied("Location setup requires Plant Admin access.")
    return workbook_response(
        "tag_range_setup_template.xlsx",
        "Tag Ranges",
        ("SAP Location", "Location", "Sub Location", "Start", "End"),
        ("0CHK", "ASSEMBLY #1", "BLADES-A-LINE", 935200, 935299),
        (18, 30, 30, 14, 14),
    )


@login_required
def counter_roster(request):
    plant = _selected_plant(request)
    if not user_has_scoped_action(request.user, "plants.manage_counterroster", plant_id=plant.pk):
        raise PermissionDenied("Counter roster management requires Plant Admin access.")

    if request.method == "POST":
        action = request.POST.get("action")
        try:
            with transaction.atomic():
                if action == "add":
                    form = CounterRosterForm(request.POST)
                    if not form.is_valid():
                        raise ValidationError(_form_error_message(form))
                    department_id = form.cleaned_data.pop("department_id", None)
                    sap_location_id = form.cleaned_data.pop("sap_location_id", None)
                    department = Department.objects.get(pk=department_id, plant=plant, is_active=True) if department_id else None
                    sap_location = (
                        SAPLocation.objects.get(pk=sap_location_id, plant=plant, is_active=True) if sap_location_id else None
                    )
                    item = CounterRoster(
                        plant=plant,
                        department=department,
                        sap_location=sap_location,
                        **form.cleaned_data,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    item.full_clean()
                    item.save()
                    messages.success(request, f"Counter {item.display_name} added.")
                elif action == "status":
                    item = CounterRoster.objects.select_for_update().get(pk=request.POST.get("roster_id"), plant=plant)
                    item.is_active = request.POST.get("is_active") == "1"
                    item.updated_by = request.user
                    item.save(update_fields=["is_active", "updated_by", "updated_at"])
                    messages.success(request, "Counter roster status updated.")
                else:
                    raise ValidationError("Unknown roster action.")
        except (
            IntegrityError,
            Department.DoesNotExist,
            SAPLocation.DoesNotExist,
            CounterRoster.DoesNotExist,
        ):
            messages.error(
                request,
                "That Employee ID already exists in this Plant or the scope is invalid.",
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        return redirect("portal:counter-roster")

    search = request.GET.get("q", "").strip()
    roster = CounterRoster.objects.filter(plant=plant).select_related("department", "sap_location", "updated_by")
    if search:
        roster = roster.filter(
            Q(employee_id__icontains=search)
            | Q(display_name__icontains=search)
            | Q(email__icontains=search)
            | Q(department__name__icontains=search)
            | Q(sap_location__code__icontains=search)
        )
    return render(
        request,
        "portal/counter_roster.html",
        {
            "plant": plant,
            "departments": Department.objects.filter(plant=plant, is_active=True),
            "sap_locations": SAPLocation.objects.filter(plant=plant, is_active=True).select_related("department"),
            "roster": roster,
            "search": search,
        },
    )


@login_required
def dropdown_management(request):
    plant = _selected_plant(request)
    require_any_plant_scope(
        request.user,
        "plants.manage_businessoption",
        plant_id=plant.pk,
    )
    ensure_default_options(plant)

    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        category = request.POST.get("category", "").strip()
        category_labels = dict(BusinessOptionCategory.choices)
        try:
            if category not in category_labels:
                raise ValidationError("Choose a valid dropdown category.")

            with transaction.atomic():
                if action == "add":
                    value = request.POST.get("value", "").strip()
                    if not value:
                        raise ValidationError("Option text is required.")
                    if len(value) > 120:
                        raise ValidationError("Option text cannot exceed 120 characters.")
                    if BusinessOption.objects.filter(
                        plant=plant,
                        category=category,
                        value__iexact=value,
                    ).exists():
                        raise ValidationError("That option already exists in this category.")
                    try:
                        sort_order = int(request.POST.get("sort_order") or 999)
                    except (TypeError, ValueError):
                        raise ValidationError("Order must be a whole number.")
                    if sort_order < 0:
                        raise ValidationError("Order cannot be negative.")
                    item = BusinessOption(
                        plant=plant,
                        category=category,
                        value=value,
                        sort_order=sort_order,
                        created_by=request.user,
                        updated_by=request.user,
                    )
                    item.full_clean()
                    item.save()
                    messages.success(request, f"{value} added.")

                elif action in {"save", "delete"}:
                    item = BusinessOption.objects.select_for_update().get(
                        pk=request.POST.get("option_id"),
                        plant=plant,
                        category=category,
                    )
                    usage_count = option_usage(item)

                    if action == "delete":
                        if item.is_protected:
                            raise ValidationError(f"{item.value} is system protected and cannot be deleted.")
                        if usage_count:
                            raise ValidationError(
                                f"{item.value} is used by {usage_count} historical record(s). " "Deactivate it instead of deleting it."
                            )
                        if (
                            item.is_active
                            and BusinessOption.objects.filter(
                                plant=plant,
                                category=category,
                                is_active=True,
                            ).count()
                            <= 1
                        ):
                            raise ValidationError("Keep at least one active option in each category.")
                        value = item.value
                        item.delete()
                        messages.success(request, f"{value} deleted.")
                    else:
                        value = request.POST.get("value", "").strip()
                        is_active = request.POST.get("is_active") == "1"
                        if not value:
                            raise ValidationError("Option text is required.")
                        if len(value) > 120:
                            raise ValidationError("Option text cannot exceed 120 characters.")
                        try:
                            sort_order = int(request.POST.get("sort_order") or 0)
                        except (TypeError, ValueError):
                            raise ValidationError("Order must be a whole number.")
                        if sort_order < 0:
                            raise ValidationError("Order cannot be negative.")
                        if item.is_protected and (value != item.value or not is_active):
                            raise ValidationError(f"{item.value} is required by system validation and must remain active.")
                        if usage_count and value.casefold() != item.value.casefold():
                            raise ValidationError(
                                f"{item.value} is used by {usage_count} historical record(s). "
                                "Deactivate it and add a replacement instead of renaming it."
                            )
                        if (
                            BusinessOption.objects.filter(
                                plant=plant,
                                category=category,
                                value__iexact=value,
                            )
                            .exclude(pk=item.pk)
                            .exists()
                        ):
                            raise ValidationError("That option already exists in this category.")
                        if (
                            item.is_active
                            and not is_active
                            and BusinessOption.objects.filter(
                                plant=plant,
                                category=category,
                                is_active=True,
                            ).count()
                            <= 1
                        ):
                            raise ValidationError("Keep at least one active option in each category.")
                        item.value = value
                        item.sort_order = sort_order
                        item.is_active = is_active
                        item.updated_by = request.user
                        item.full_clean()
                        item.save()
                        messages.success(request, f"{item.value} updated.")
                else:
                    raise ValidationError("Unknown dropdown action.")
        except BusinessOption.DoesNotExist:
            messages.error(request, "That option no longer exists. Refresh and try again.")
        except (ValidationError, IntegrityError) as exc:
            if isinstance(exc, ValidationError):
                messages.error(request, " ".join(exc.messages))
            else:
                messages.error(request, "The option conflicts with an existing value.")
        return redirect("portal:dropdown-management")

    category_meta = {
        BusinessOptionCategory.ROOT_CAUSE: {
            "description": "Used when a Count Update is submitted from the 5-Day Update page.",
            "impact": "Deactivated values disappear from new requests; historical requests keep their original text.",
        },
        BusinessOptionCategory.SAP_CORRECTION_TYPE: {
            "description": "Used when a SAP Transaction Correction is submitted from the 5-Day Update page.",
            "impact": "311 Transfer remains protected because its multi-location balance rule depends on this value.",
        },
    }
    sections = []
    for category, label in BusinessOptionCategory.choices:
        options = list(BusinessOption.objects.filter(plant=plant, category=category).select_related("updated_by"))
        for item in options:
            item.usage_count = option_usage(item)
        sections.append(
            {
                "category": category,
                "label": label,
                "description": category_meta[category]["description"],
                "impact": category_meta[category]["impact"],
                "options": options,
            }
        )

    return render(
        request,
        "portal/dropdown_management.html",
        {
            "plant": plant,
            "sections": sections,
        },
    )


@login_required
def cycles(request):
    plant = _selected_plant(request, required=False)
    if plant is None:
        messages.warning(
            request,
            "Create the first Plant and at least one SAP Location before opening a PI Cycle.",
        )
        return redirect("portal:plant-setup")
    may_manage = user_has_scoped_action(request.user, "cycles.add_picycle", plant_id=plant.pk)
    may_close = user_has_scoped_action(request.user, "cycles.close_picycle", plant_id=plant.pk)
    open_cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()
    preview = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "close":
            if not may_close:
                raise PermissionDenied("Your role cannot close this PI Cycle.")
            if open_cycle is None or str(open_cycle.pk) != request.POST.get("cycle_id"):
                messages.error(request, "That open PI Cycle is no longer available. Refresh and try again.")
                return redirect("portal:cycles")
            try:
                closed = close_cycle(
                    cycle_id=open_cycle.pk,
                    closed_by=request.user,
                    blocker_checks=(lambda cycle: " ".join(cycle_close_readiness(cycle)) or None,),
                )
                messages.success(
                    request,
                    f"{closed.name} closed. {closed.follow_up_created_count} unresolved P/N × SAP Location item(s) were carried to Follow-up.",
                )
                return redirect("portal:cycles")
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            form = CycleCreateForm(plant=plant)
        else:
            if not may_manage:
                raise PermissionDenied("Your role cannot create a PI Cycle for this Plant.")
            form = CycleCreateForm(request.POST, plant=plant)
        if action != "close" and form.is_valid():
            if action == "preview":
                preview = form.cleaned_data
            elif action == "create":
                try:
                    cycle = create_open_cycle(
                        plant_id=plant.pk,
                        name=form.cleaned_data["name"],
                        opened_by=request.user,
                        sap_location_ids=form.cleaned_data["sap_location_ids"],
                        physical_location_ids=form.cleaned_data["physical_location_ids"],
                        sub_location_ids=form.cleaned_data["sub_location_ids"],
                    )
                    messages.success(request, f"{cycle.name} created and opened.")
                    return redirect("portal:cycles")
                except ValidationError as exc:
                    messages.error(request, " ".join(exc.messages))
        elif action != "close":
            messages.error(request, "Please complete the required PI name and SAP Location scope.")
    else:
        form = CycleCreateForm(plant=plant)

    close_final_capture = None
    close_blockers = []
    if open_cycle:
        close_final_capture = (
            PICapture.objects.filter(
                cycle=open_cycle,
                capture_type__in=[CaptureType.FIVE_DAY_FINAL, CaptureType.CLOSE_FINAL],
            )
            .order_by("-captured_at")
            .first()
        )
        close_blockers = cycle_close_readiness(open_cycle)

    cycle_history = list(
        PICycle.objects.filter(plant=plant)
        .select_related("opened_by", "closed_by")
        .prefetch_related(
            Prefetch(
                "captures",
                queryset=PICapture.objects.filter(
                    capture_type__in=[
                        CaptureType.FIVE_DAY_FINAL,
                        CaptureType.CLOSE_FINAL,
                    ]
                ).order_by("-captured_at"),
                to_attr="final_captures",
            )
        )
        .annotate(
            follow_up_count=Count("follow_up_items", distinct=True),
            follow_up_open_count=Count(
                "follow_up_items",
                filter=~Q(follow_up_items__status__in=TERMINAL_FOLLOW_UP_STATUSES),
                distinct=True,
            ),
        )
    )
    for item in cycle_history:
        item.final_capture = next(
            (capture for capture in item.final_captures if capture.capture_type == CaptureType.FIVE_DAY_FINAL),
            item.final_captures[0] if item.final_captures else None,
        )
    return render(
        request,
        "portal/cycles.html",
        {
            "plant": plant,
            "open_cycle": open_cycle,
            "cycle_history": cycle_history,
            "form": form,
            "preview": preview,
            "may_manage": may_manage,
            "may_close": may_close,
            "close_final_capture": close_final_capture,
            "close_blockers": close_blockers,
        },
    )


def _audit_cycle(request, action):
    plant = _selected_plant(request)
    cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()
    if cycle is None:
        messages.warning(request, "Open a PI Cycle before using Audit.")
        return plant, None
    if not user_has_action(request.user, action):
        raise PermissionDenied("Your role cannot access this Audit page.")
    require_any_plant_scope(request.user, action, plant_id=plant.pk)
    return plant, cycle


def _audit_plan_for_user(request, plan_id, action="audit.view_auditplan"):
    plan = get_object_or_404(
        AuditPlan.objects.select_related("cycle__plant", "department"),
        pk=plan_id,
    )
    plant = _selected_plant(request)
    if plan.cycle.plant_id != plant.pk or not user_has_scoped_action(
        request.user,
        action,
        plant_id=plant.pk,
        department_id=plan.department_id,
    ):
        raise PermissionDenied("This Audit Plan is outside your approved scope.")
    return plan


def _audit_plans_in_scope(request, cycle, action="audit.view_auditplan"):
    query = AuditPlan.objects.filter(cycle=cycle).select_related("department")
    department_ids = allowed_department_ids(request.user, action, plant_id=cycle.plant_id)
    if department_ids is not None:
        query = query.filter(department_id__in=department_ids)
    return query


def _post_int(request, name, *, minimum=0):
    try:
        value = int(request.POST.get(name, ""))
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name.replace('_', ' ').title()} must be a whole number.") from exc
    if value < minimum:
        raise ValidationError(f"{name.replace('_', ' ').title()} must be at least {minimum}.")
    return value


def _post_decimal(request, name):
    try:
        value = Decimal(request.POST.get(name, ""))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"{name.replace('_', ' ').title()} must be numeric.") from exc
    if not value.is_finite():
        raise ValidationError(f"{name.replace('_', ' ').title()} must be finite.")
    return value


@login_required
def audit_planning(request):
    plant, cycle = _audit_cycle(request, "audit.view_auditplan")
    if cycle is None:
        return redirect("portal:cycles")
    create_department_ids = allowed_department_ids(request.user, "audit.add_auditplan", plant_id=plant.pk)
    departments = Department.objects.filter(plant=plant, is_active=True)
    if create_department_ids is not None:
        departments = departments.filter(pk__in=create_department_ids)
    departments = list(departments.order_by("sort_order", "name"))
    may_create = bool(departments) and user_has_action(request.user, "audit.add_auditplan")
    sap_locations = list(
        SAPLocation.objects.filter(
            cycle_scope__cycle=cycle,
            cycle_scope__is_active=True,
            department_id__in=[item.pk for item in departments],
            is_active=True,
        )
        .select_related("department")
        .distinct()
        .order_by("department__sort_order", "code")
    )
    physical_locations = list(
        PhysicalLocation.objects.filter(
            cycle_scope__cycle=cycle,
            cycle_scope__is_active=True,
            sap_location_id__in=[item.pk for item in sap_locations],
            is_active=True,
        )
        .select_related("sap_location")
        .distinct()
        .order_by("sap_location__code", "name")
    )
    base_plan_name = f"{cycle.name} Audit"
    default_plan_name = base_plan_name
    suffix = 2
    existing_plan_names = set(AuditPlan.objects.filter(cycle=cycle).values_list("name", flat=True))
    while default_plan_name in existing_plan_names:
        default_plan_name = f"{base_plan_name} {suffix}"
        suffix += 1
    if request.method == "POST":
        if not may_create:
            raise PermissionDenied("Your role cannot create Audit Plans.")
        try:
            name = request.POST.get("name", "").strip()
            if not name:
                raise ValidationError("Plan Name is required.")
            plan = create_audit_plan(
                cycle=cycle,
                department_id=_post_int(request, "department_id", minimum=1),
                name=name,
                sap_location_ids=[int(value) for value in request.POST.getlist("sap_location_ids")],
                physical_location_ids=[int(value) for value in request.POST.getlist("physical_location_ids")],
                auditors=_post_int(request, "auditors", minimum=1),
                pages_per_auditor=_post_int(request, "pages_per_auditor", minimum=1),
                density=request.POST.get("density", PageDensity.NORMAL),
                value_pct=_post_decimal(request, "value_pct"),
                map_pct=_post_decimal(request, "map_pct"),
                variance_pct=_post_decimal(request, "variance_pct"),
                user=request.user,
            )
            messages.success(request, "Audit recommendation generated. Review the selected P/Ns before finalizing.")
            return redirect("portal:audit-plan", plan_id=plan.plan_id)
        except (ValidationError, ValueError) as exc:
            if isinstance(exc, ValidationError):
                _show_validation_error(request, exc)
            else:
                messages.error(request, "One or more selected scope values are invalid.")

    plans = _audit_plans_in_scope(request, cycle).annotate(selected_total=Sum("candidates__selected_records")).order_by("-updated_at")
    return render(
        request,
        "portal/audit_planning.html",
        {
            "plant": plant,
            "cycle": cycle,
            "departments": departments,
            "sap_locations": sap_locations,
            "physical_locations": physical_locations,
            "plans": plans,
            "may_create": may_create,
            "default_plan_name": default_plan_name,
            "density_choices": PageDensity.choices,
        },
    )


@login_required
def audit_plan(request, plan_id):
    plan = _audit_plan_for_user(request, plan_id)
    may_change = user_has_scoped_action(
        request.user,
        "audit.change_auditplan",
        plant_id=plan.cycle.plant_id,
        department_id=plan.department_id,
    )
    may_finalize = user_has_scoped_action(
        request.user,
        "audit.finalize_auditplan",
        plant_id=plan.cycle.plant_id,
        department_id=plan.department_id,
    )
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "regenerate":
                if not may_change:
                    raise PermissionDenied("Your role cannot regenerate this Audit Plan.")
                update_and_regenerate_plan(
                    plan_id=plan.plan_id,
                    expected_row_version=_post_int(request, "row_version", minimum=1),
                    auditors=_post_int(request, "auditors", minimum=1),
                    pages_per_auditor=_post_int(request, "pages_per_auditor", minimum=1),
                    density=request.POST.get("density", PageDensity.NORMAL),
                    value_pct=_post_decimal(request, "value_pct"),
                    map_pct=_post_decimal(request, "map_pct"),
                    variance_pct=_post_decimal(request, "variance_pct"),
                    user=request.user,
                )
                messages.success(request, "Capacity, sampling mix and recommendation regenerated.")
            elif action == "candidate":
                if not may_change:
                    raise PermissionDenied("Your role cannot adjust this sample.")
                set_candidate_selection(
                    candidate_id=request.POST.get("candidate_id"),
                    selected_records=_post_int(request, "selected_records"),
                    expected_plan_version=_post_int(request, "row_version", minimum=1),
                    user=request.user,
                )
                messages.success(request, "Candidate selection updated.")
            elif action == "finalize":
                if not may_finalize:
                    raise PermissionDenied("Your role cannot finalize this Audit Plan.")
                finalize_plan(
                    plan_id=plan.plan_id,
                    expected_row_version=_post_int(request, "row_version", minimum=1),
                    user=request.user,
                )
                messages.success(request, "Audit Plan finalized and records frozen.")
            else:
                raise ValidationError("Unknown Audit Plan action.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:audit-plan", plan_id=plan.plan_id)

    tab = request.GET.get("show", "selected")
    if tab not in {"selected", "unselected", "all"}:
        tab = "selected"
    search = request.GET.get("search", "").strip()
    candidates = plan.candidates.select_related("sap_location")
    if tab == "selected":
        candidates = candidates.filter(selected_records__gt=0)
    elif tab == "unselected":
        candidates = candidates.filter(selected_records=0)
    if search:
        candidates = candidates.filter(
            Q(part_number_snapshot__icontains=search)
            | Q(description_snapshot__icontains=search)
            | Q(sap_location__code__icontains=search)
        )
    candidates = candidates.order_by("sap_location__code", "-book_value", "part_number_snapshot")
    totals = plan.candidates.aggregate(selected=Sum("selected_records"), records=Sum("count_records"))
    selected = totals["selected"] or 0
    required_pages = (selected + plan.rows_per_page - 1) // plan.rows_per_page
    return render(
        request,
        "portal/audit_plan.html",
        {
            "plan": plan,
            "candidates": candidates,
            "candidate_total": candidates.count(),
            "selected": selected,
            "available": totals["records"] or 0,
            "difference": selected - plan.target_count,
            "required_pages": required_pages,
            "tab": tab,
            "search": search,
            "may_change": may_change,
            "may_finalize": may_finalize,
            "density_choices": PageDensity.choices,
        },
    )


@login_required
def audit_workbook(request, plan_id):
    plan = _audit_plan_for_user(request, plan_id)
    try:
        payload = build_audit_workbook(plan.plan_id)
    except ValidationError as exc:
        _show_validation_error(request, exc)
        return redirect("portal:audit-plan", plan_id=plan.plan_id)
    response = HttpResponse(
        payload,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    safe_name = "".join(character if character.isalnum() else "_" for character in plan.name)
    response["Content-Disposition"] = f'attachment; filename="{safe_name}_Audit_Sheet.xlsx"'
    return response


@login_required
def audit_results(request, plan_id):
    plan = _audit_plan_for_user(request, plan_id)
    may_submit = user_has_scoped_action(
        request.user,
        "audit.submit_auditresult",
        plant_id=plan.cycle.plant_id,
        department_id=plan.department_id,
    )
    if request.method == "POST":
        if not may_submit:
            raise PermissionDenied("Your role cannot enter Audit Results.")
        action = request.POST.get("action")
        return_page = request.POST.get("page", "1")
        try:
            if action == "mark_pages":
                mark_pages_correct(
                    plan_id=plan.plan_id,
                    page_numbers=request.POST.getlist("page_numbers"),
                    auditor_name=request.POST.get("auditor_name", ""),
                    user=request.user,
                )
                messages.success(request, "Pending records on the selected page(s) were marked Correct.")
            elif action == "save_record":
                result_status = request.POST.get("result_status", AuditResultStatus.PENDING)
                audit_quantity = None
                if request.POST.get("audit_quantity", "").strip():
                    audit_quantity = _post_decimal(request, "audit_quantity")
                corrected_part = None
                corrected_pn = request.POST.get("corrected_part_number", "").strip().upper()
                if corrected_pn:
                    corrected_part = PartMaster.objects.filter(cycle=plan.cycle, part_number=corrected_pn).first()
                save_audit_result(
                    audit_record_id=request.POST.get("audit_record_id"),
                    result_status=result_status,
                    audit_quantity=audit_quantity,
                    error_type=request.POST.get("error_type", ""),
                    corrected_part=corrected_part,
                    comment=request.POST.get("comment", ""),
                    auditor_name=request.POST.get("auditor_name", ""),
                    expected_row_version=_post_int(request, "row_version", minimum=1),
                    user=request.user,
                )
                messages.success(request, "Audit Result saved; any error is now in Audit Corrections.")
            elif action == "submit":
                submit_audit_results(
                    plan_id=plan.plan_id,
                    expected_row_version=_post_int(request, "row_version", minimum=1),
                    user=request.user,
                )
                messages.success(request, "Audit Results submitted and locked.")
            else:
                raise ValidationError("Unknown Audit Result action.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect(f"{request.path}?page={return_page}")

    page_summaries = list(
        plan.records.values("page_number", "auditor_number")
        .annotate(
            total=Count("audit_record_id"),
            complete=Count(
                "audit_record_id",
                filter=~Q(result_status=AuditResultStatus.PENDING),
            ),
            errors=Count(
                "audit_record_id",
                filter=Q(result_status=AuditResultStatus.ERROR),
            ),
        )
        .order_by("page_number")
    )
    selected_page = request.GET.get("page", "")
    valid_pages = {str(item["page_number"]) for item in page_summaries}
    if selected_page not in valid_pages:
        selected_page = str(page_summaries[0]["page_number"]) if page_summaries else "1"
    rows = plan.records.select_related("count_correction", "corrected_part")
    search = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "")
    if search:
        rows = rows.filter(
            Q(part_number_snapshot__icontains=search)
            | Q(tag_number_snapshot__icontains=search)
            | Q(physical_location_snapshot__icontains=search)
            | Q(sub_location_snapshot__icontains=search)
        )
    else:
        rows = rows.filter(page_number=int(selected_page))
    if status_filter in AuditResultStatus.values:
        rows = rows.filter(result_status=status_filter)
    metrics = audit_accuracy(plan.plan_id)
    pending = plan.records.filter(result_status=AuditResultStatus.PENDING).count()
    completion_pct = ((metrics["total"] - pending) / metrics["total"] * 100) if metrics["total"] else 0
    return render(
        request,
        "portal/audit_results.html",
        {
            "plan": plan,
            "rows": rows.order_by("audit_record_id"),
            "page_summaries": page_summaries,
            "selected_page": selected_page,
            "search": search,
            "status_filter": status_filter,
            "status_choices": AuditResultStatus.choices,
            "error_choices": AuditErrorType.choices,
            "metrics": metrics,
            "pending": pending,
            "completed": metrics["total"] - pending,
            "completion_pct": completion_pct,
            "may_submit": may_submit,
        },
    )


@login_required
def audit_corrections(request):
    plant, cycle = _audit_cycle(request, "counting.view_countcorrection")
    if cycle is None:
        return redirect("portal:cycles")
    if request.method == "POST":
        correction = get_object_or_404(
            CountCorrection.objects.select_related("count_record__sap_location"),
            pk=request.POST.get("correction_id"),
            count_record__cycle=cycle,
            audit_record__isnull=False,
        )
        action = request.POST.get("action")
        try:
            if action in {"approve", "reject"}:
                review_count_correction(
                    correction_id=correction.correction_id,
                    decision=(CorrectionStatus.APPROVED if action == "approve" else CorrectionStatus.REJECTED),
                    expected_row_version=_post_int(request, "row_version", minimum=1),
                    review_comment=request.POST.get("review_comment", ""),
                    user=request.user,
                )
                messages.success(request, f"Audit Correction {action}d.")
            elif action == "apply":
                apply_count_correction(
                    correction_id=correction.correction_id,
                    expected_row_version=_post_int(request, "row_version", minimum=1),
                    user=request.user,
                )
                messages.success(request, "Audit Correction applied to the Count Result; live variance is updated.")
            else:
                raise ValidationError("Unknown Audit Correction action.")
        except ValidationError as exc:
            _show_validation_error(request, exc)
        return redirect("portal:audit-corrections")

    query = CountCorrection.objects.filter(count_record__cycle=cycle, audit_record__isnull=False).select_related(
        "count_record__sap_location__department",
        "count_record__part",
        "corrected_part",
        "submitted_by",
        "reviewed_by",
        "applied_by",
        "audit_record__plan",
    )
    allowed_ids = allowed_sap_location_ids(request.user, "counting.view_countcorrection", plant_id=plant.pk)
    if allowed_ids is not None:
        query = query.filter(count_record__sap_location_id__in=allowed_ids)
    status_filter = request.GET.get("status", "")
    search = request.GET.get("search", "").strip()
    if status_filter in CorrectionStatus.values:
        query = query.filter(status=status_filter)
    if search:
        query = query.filter(
            Q(count_record__part__part_number__icontains=search)
            | Q(corrected_part__part_number__icontains=search)
            | Q(count_record__sap_location__code__icontains=search)
            | Q(audit_record__plan__name__icontains=search)
        )
    rows = list(query.order_by("-submitted_at"))
    for item in rows:
        scope = {
            "plant_id": plant.pk,
            "department_id": item.count_record.sap_location.department_id,
            "sap_location_id": item.count_record.sap_location_id,
        }
        item.may_review = user_has_scoped_action(request.user, "counting.review_countcorrection", **scope)
        item.may_apply = user_has_scoped_action(request.user, "counting.apply_countcorrection", **scope)
    count_query = CountCorrection.objects.filter(count_record__cycle=cycle, audit_record__isnull=False)
    if allowed_ids is not None:
        count_query = count_query.filter(count_record__sap_location_id__in=allowed_ids)
    counts = count_query.values("status").annotate(total=Count("correction_id"))
    status_counts = {item["status"]: item["total"] for item in counts}
    return render(
        request,
        "portal/audit_corrections.html",
        {
            "cycle": cycle,
            "rows": rows,
            "status_filter": status_filter,
            "status_choices": CorrectionStatus.choices,
            "status_counts": status_counts,
            "submitted_count": status_counts.get(CorrectionStatus.SUBMITTED, 0),
            "approved_count": status_counts.get(CorrectionStatus.APPROVED, 0),
            "applied_count": status_counts.get(CorrectionStatus.APPLIED, 0),
            "rejected_count": status_counts.get(CorrectionStatus.REJECTED, 0),
            "search": search,
        },
    )


@login_required
def audit_accuracy_page(request):
    plant, cycle = _audit_cycle(request, "audit.view_auditaccuracy")
    if cycle is None:
        return redirect("portal:cycles")
    plans = list(_audit_plans_in_scope(request, cycle, "audit.view_auditaccuracy").order_by("-updated_at"))
    rows = []
    combined = {"total": 0, "reviewed": 0, "correct": 0, "errors": 0, "excluded": 0}
    for plan in plans:
        metric = audit_accuracy(plan.plan_id)
        rows.append({"plan": plan, "metric": metric})
        for key in combined:
            combined[key] += metric[key]
    combined["record_accuracy"] = Decimal(combined["correct"]) / Decimal(combined["reviewed"]) * 100 if combined["reviewed"] else None
    return render(
        request,
        "portal/audit_accuracy.html",
        {"cycle": cycle, "rows": rows, "combined": combined},
    )


def _filtered_variance_data(request, plant, cycle):
    locations, allowed_ids = _variance_scope(request, plant, cycle)
    selected_department = request.GET.get("department", "").strip()
    selected_sap = request.GET.get("sap_location", "").strip().upper()
    selected_bu = request.GET.get("business_unit", "").strip()
    selected_type = request.GET.get("inventory_type", "").strip().upper()
    search = request.GET.get("search", "").strip()
    show_all = request.GET.get("show", "variance") == "all"

    filtered_locations = locations
    if selected_department:
        filtered_locations = [item for item in filtered_locations if str(item.department_id) == selected_department]
    if selected_sap:
        filtered_locations = [item for item in filtered_locations if item.code.upper() == selected_sap]
    if selected_type in {"TK", "CS"}:
        filtered_locations = [item for item in filtered_locations if item.inventory_type == selected_type]

    filtered_ids = {item.pk for item in filtered_locations} & allowed_ids
    metric_lines = build_live_variance(cycle.pk, filtered_ids)
    if selected_bu:
        metric_lines = [line for line in metric_lines if line["business_unit"] == selected_bu]
    if search:
        needle = search.casefold()
        metric_lines = [
            line
            for line in metric_lines
            if needle in line["part_number"].casefold()
            or needle in line["description"].casefold()
            or needle in line["sap_location_code"].casefold()
        ]
    lines = metric_lines if show_all else [line for line in metric_lines if line["variance_quantity"] != 0]

    display_parts = None
    if show_all:
        part_query = PartMaster.objects.filter(cycle=cycle)
        if selected_bu:
            part_query = part_query.filter(business_unit=selected_bu)
        if search:
            part_query = part_query.filter(Q(part_number__icontains=search) | Q(description__icontains=search))
        display_parts = list(part_query.order_by("part_number"))

    departments = sorted(
        {item.department for item in locations},
        key=lambda item: (item.sort_order, item.name.casefold()),
    )
    business_units = list(
        PartMaster.objects.filter(cycle=cycle)
        .exclude(business_unit="")
        .order_by("business_unit")
        .values_list("business_unit", flat=True)
        .distinct()
    )
    return {
        "locations": locations,
        "filtered_locations": filtered_locations,
        "lines": lines,
        "metric_lines": metric_lines,
        "display_parts": display_parts,
        "departments": departments,
        "business_units": business_units,
        "selected_department": selected_department,
        "selected_sap": selected_sap,
        "selected_bu": selected_bu,
        "selected_type": selected_type,
        "search": search,
        "show_all": show_all,
    }


def _pivot_variance(lines, locations, display_parts=None):
    tk_locations = [item for item in locations if item.inventory_type != "CS"]
    cs_locations = [item for item in locations if item.inventory_type == "CS"]
    by_part = {}
    line_index = {(line["part_id"], line["sap_location_id"]): line for line in lines}
    for part in display_parts or []:
        by_part[part.pk] = {
            "part_id": part.pk,
            "part_number": part.part_number,
            "description": part.description,
            "business_unit": part.business_unit,
            "price": Decimal(part.price or 0),
            "types": set(),
            "tk_var_qty": Decimal("0"),
            "tk_var_value": Decimal("0"),
            "cs_var_qty": Decimal("0"),
            "cs_abs_qty": Decimal("0"),
            "cs_accuracy_values": [],
        }
    for line in lines:
        row = by_part.setdefault(
            line["part_id"],
            {
                "part_id": line["part_id"],
                "part_number": line["part_number"],
                "description": line["description"],
                "business_unit": line["business_unit"],
                "price": line["price"],
                "types": set(),
                "tk_var_qty": Decimal("0"),
                "tk_var_value": Decimal("0"),
                "cs_var_qty": Decimal("0"),
                "cs_abs_qty": Decimal("0"),
                "cs_accuracy_values": [],
            },
        )
        row["types"].add(line["inventory_type"])
        if line["inventory_type"] == "CS":
            row["cs_var_qty"] += line["variance_quantity"]
            row["cs_abs_qty"] += abs(line["variance_quantity"])
            if line["quantity_accuracy"] is not None:
                row["cs_accuracy_values"].append(line["quantity_accuracy"])
        else:
            row["tk_var_qty"] += line["variance_quantity"]
            row["tk_var_value"] += line["variance_value"]

    rows = []
    for row in by_part.values():
        row["inventory_type"] = " / ".join(sorted(row.pop("types"))) or "—"
        row["tk_abs_var"] = abs(row["tk_var_value"])
        accuracies = row.pop("cs_accuracy_values")
        row["cs_accuracy"] = sum(accuracies, Decimal("0")) / len(accuracies) if accuracies else None
        row["tk_cells"] = [{"location": location, "line": line_index.get((row["part_id"], location.pk))} for location in tk_locations]
        row["cs_cells"] = [{"location": location, "line": line_index.get((row["part_id"], location.pk))} for location in cs_locations]
        rows.append(row)
    rows.sort(
        key=lambda row: (
            -max(abs(row["tk_var_value"]), abs(row["cs_var_qty"])),
            row["part_number"],
        )
    )
    return rows, tk_locations, cs_locations


def _attach_previous_pi_variance_history(*, user, plant, cycle, rows):
    """Attach the previous PI's immutable final variance lines by P/N."""
    for row in rows:
        row["previous_pi_history"] = None
    if not rows:
        return

    previous_cycle = (
        PICycle.objects.filter(plant=plant, status=CycleStatus.CLOSED)
        .exclude(pk=cycle.pk)
        .order_by("-closed_at", "-created_at")
        .first()
    )
    if previous_cycle is None:
        return

    previous_capture = (
        PICapture.objects.filter(
            cycle=previous_cycle,
            capture_type=CaptureType.FIVE_DAY_FINAL,
        )
        .order_by("-captured_at")
        .first()
        or PICapture.objects.filter(
            cycle=previous_cycle,
            capture_type=CaptureType.CLOSE_FINAL,
        )
        .order_by("-captured_at")
        .first()
    )
    if previous_capture is None:
        return

    part_numbers = {row["part_number"] for row in rows}
    history_query = CaptureVarianceLine.objects.filter(
        capture=previous_capture,
        part_number__in=part_numbers,
    ).exclude(variance_quantity=0)
    allowed_ids = allowed_sap_location_ids(user, "variance.view", plant_id=plant.pk)
    if allowed_ids is not None:
        history_query = history_query.filter(source_sap_location_id__in=allowed_ids)

    status_labels = dict(VarianceResolutionStatus.choices)
    history_by_part = defaultdict(list)
    for line in history_query.order_by("part_number", "sap_location"):
        line.history_status_label = status_labels.get(
            line.resolution_status,
            "Open / No PI-day decision",
        )
        history_by_part[line.part_number].append(line)

    for row in rows:
        history_lines = history_by_part.get(row["part_number"], [])
        if history_lines:
            row["previous_pi_history"] = {
                "cycle": previous_cycle,
                "capture": previous_capture,
                "lines": history_lines,
            }


@login_required
def variance_report(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    data = _filtered_variance_data(request, plant, cycle)
    rows, tk_locations, cs_locations = _pivot_variance(data["lines"], data["filtered_locations"], data["display_parts"])
    resolution_objects = VarianceResolution.objects.filter(cycle=cycle, part_id__in=[row["part_id"] for row in rows]).prefetch_related(
        "comments__created_by"
    )
    resolution_by_line = {(item.part_id, item.sap_location_id): item for item in resolution_objects}
    status_by_line = {key: item.status for key, item in resolution_by_line.items()}
    for row in rows:
        active_lines = [
            cell["line"] for cell in row["tk_cells"] + row["cs_cells"] if cell["line"] and cell["line"]["variance_quantity"] != 0
        ]
        statuses = [
            status_by_line.get(
                (line["part_id"], line["sap_location_id"]),
                VarianceResolutionStatus.NEEDS_REVIEW,
            )
            for line in active_lines
        ]
        if not active_lines:
            row["resolution_label"] = "Settled"
            row["resolution_class"] = "settled"
        elif all(item == VarianceResolutionStatus.POSTED for item in statuses):
            row["resolution_label"] = "Fully Posted"
            row["resolution_class"] = "posted"
        elif all(item == VarianceResolutionStatus.NOT_POST for item in statuses):
            row["resolution_label"] = "Not Post"
            row["resolution_class"] = "not-post"
        elif all(
            item
            in {
                VarianceResolutionStatus.POSTED,
                VarianceResolutionStatus.NOT_POST,
            }
            for item in statuses
        ):
            row["resolution_label"] = "Partially Resolved"
            row["resolution_class"] = "review"
        elif VarianceResolutionStatus.TO_POST in statuses:
            if all(item == VarianceResolutionStatus.TO_POST for item in statuses):
                row["resolution_label"] = "To Post"
                row["resolution_class"] = "to-post"
            else:
                row["resolution_label"] = "Mixed / Review"
                row["resolution_class"] = "review"
        else:
            row["resolution_label"] = "Review Required"
            row["resolution_class"] = "review"
        comment_locations = []
        for cell in row["tk_cells"] + row["cs_cells"]:
            line = cell["line"]
            if not line or line["variance_quantity"] == 0:
                continue
            resolution = resolution_by_line.get((line["part_id"], line["sap_location_id"]))
            comment_locations.append(
                {
                    "location": cell["location"],
                    "line": line,
                    "resolution": resolution,
                    "comments": list(resolution.comments.all()) if resolution else [],
                    "submission_key": uuid.uuid4(),
                    "can_decide_line": not resolution or resolution.status == VarianceResolutionStatus.NEEDS_REVIEW,
                }
            )
        row["comment_locations"] = comment_locations
    _attach_previous_pi_variance_history(
        user=request.user,
        plant=plant,
        cycle=cycle,
        rows=rows,
    )
    is_closed = cycle.status == CycleStatus.CLOSED
    can_decide = user_has_action(request.user, "variance.post_decision")
    context = {
        **data,
        "plant": plant,
        "cycle": cycle,
        "rows": rows,
        "tk_locations": tk_locations,
        "cs_locations": cs_locations,
        "summary": variance_summary(data["metric_lines"]),
        "is_closed": is_closed,
        "can_decide": can_decide,
        "can_comment": user_has_action(request.user, "variance.comment"),
        "variance_colspan": (13 + len(tk_locations) + len(cs_locations) + (1 if can_decide and not is_closed else 0)),
    }
    return render(request, "portal/variance_report.html", context)


@login_required
def variance_by_part(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    locations, allowed_ids = _variance_scope(request, plant, cycle)
    part_number = request.GET.get("pn", "").strip().upper()
    part = PartMaster.objects.filter(cycle=cycle, part_number=part_number).first()
    lines = []
    records = []
    review_rows = []
    if part:
        lines = [line for line in build_live_variance(cycle.pk, allowed_ids) if line["part_id"] == part.pk]
        records = list(
            effective_count_records(cycle.pk, allowed_ids)
            .filter(effective_part_id=part.pk)
            .select_related(
                "sap_location__department",
                "physical_location",
                "sub_location",
                "entered_by",
            )
            .order_by("sap_location__code", "physical_location__name", "tag_number")
        )
        resolutions = {
            item.sap_location_id: item
            for item in VarianceResolution.objects.filter(cycle=cycle, part=part).prefetch_related(
                "comments__created_by", "status_history__created_by"
            )
        }
        for line in lines:
            if line["variance_quantity"] == 0:
                continue
            review_rows.append(
                {
                    "line": line,
                    "resolution": resolutions.get(line["sap_location_id"]),
                    "comment_submission_key": uuid.uuid4(),
                    "can_decide_line": not resolutions.get(line["sap_location_id"])
                    or resolutions[line["sap_location_id"]].status == VarianceResolutionStatus.NEEDS_REVIEW,
                }
            )
    elif part_number:
        messages.warning(request, "That P/N is not in this PI Cycle or is outside your scope.")
    return render(
        request,
        "portal/variance_by_part.html",
        {
            "cycle": cycle,
            "part_number": part_number,
            "part": part,
            "lines": lines,
            "records": records,
            "summary": variance_summary(lines),
            "locations": locations,
            "review_rows": review_rows,
            "is_closed": cycle.status == CycleStatus.CLOSED,
            "can_comment": user_has_action(request.user, "variance.comment"),
            "can_decide": user_has_action(request.user, "variance.post_decision"),
        },
    )


def _variance_line(cycle, allowed_ids, part_id, sap_location_id):
    for line in build_live_variance(cycle.pk, allowed_ids):
        if line["part_id"] == part_id and line["sap_location_id"] == sap_location_id:
            return line
    raise Http404("Variance line is outside your scope or no longer exists.")


def _safe_workflow_redirect(request, fallback_name="portal:variance-report"):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(fallback_name)


@login_required
@require_POST
def variance_submit_post(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    if not user_has_action(request.user, "variance.post_decision"):
        raise PermissionDenied("Your role cannot make a Post decision.")
    part_ids = {int(value) for value in request.POST.getlist("part_id") if value.isdigit()}
    if not part_ids:
        messages.error(request, "Select at least one P/N.")
        return redirect("portal:variance-report")
    allowed_ids = allowed_sap_location_ids(request.user, "variance.post_decision", plant_id=plant.pk)
    lines = [
        line for line in build_live_variance(cycle.pk, allowed_ids) if line["part_id"] in part_ids and line["variance_quantity"] != 0
    ]
    try:
        batch_name = request.POST.get("batch_name", "").strip()
        if not batch_name:
            raise ValidationError("Enter a Post Batch name.")
        # The Post decision and Draft batch are one business action.  If the
        # batch cannot be created (for example because its name is duplicated),
        # do not leave the selected resolutions stranded in To Post status.
        with transaction.atomic():
            resolutions = submit_lines_to_post(cycle, lines, request.user, request.POST.get("reason", ""))
            create_post_batch(
                cycle,
                batch_name,
                resolutions,
                request.user,
                request.POST.get("batch_note", ""),
            )
        messages.success(request, f"Draft Post Batch created with {len(resolutions)} line(s).")
    except (ValidationError, IntegrityError) as exc:
        messages.error(request, str(exc))
    return redirect("portal:variance-report")


@login_required
@require_POST
def variance_comment(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    if not user_has_action(request.user, "variance.comment"):
        raise PermissionDenied("Your role cannot add Variance comments.")
    part_id = int(request.POST["part_id"])
    sap_location_id = int(request.POST["sap_location_id"])
    allowed_ids = allowed_sap_location_ids(request.user, "variance.comment", plant_id=plant.pk)
    line = _variance_line(cycle, allowed_ids, part_id, sap_location_id)
    try:
        try:
            submission_key = uuid.UUID(request.POST.get("submission_key", ""))
        except (ValueError, TypeError, AttributeError):
            raise ValidationError("Comment submission key is invalid.")
        append_comment(
            line,
            request.POST.get("comment"),
            request.user,
            submission_key,
        )
        messages.success(request, "Comment added to the permanent thread.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return _safe_workflow_redirect(request, "portal:variance-by-part")


@login_required
@require_POST
def variance_decision(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    if not user_has_action(request.user, "variance.post_decision"):
        raise PermissionDenied("Your role cannot make Post / Not Post decisions.")
    part_id = int(request.POST["part_id"])
    sap_location_id = int(request.POST["sap_location_id"])
    allowed_ids = allowed_sap_location_ids(request.user, "variance.post_decision", plant_id=plant.pk)
    line = _variance_line(cycle, allowed_ids, part_id, sap_location_id)
    try:
        decision = request.POST.get("decision")
        if decision == "NOT_POST":
            mark_not_post(cycle, line, request.user, request.POST.get("reason", ""))
            messages.success(request, "This SAP Location was marked Not Post.")
        elif decision == "TO_POST":
            submit_lines_to_post(cycle, [line], request.user, request.POST.get("reason", ""))
            messages.success(request, "This SAP Location was moved to To Post.")
        else:
            raise ValidationError("Choose Post or Not Post.")
    except ValidationError as exc:
        messages.error(request, str(exc))
    return _safe_workflow_redirect(request, "portal:variance-by-part")


@login_required
def post_batches(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    can_confirm = user_has_action(request.user, "variance.confirm_post_batch")
    view_allowed_ids = allowed_sap_location_ids(request.user, "variance.view", plant_id=plant.pk)
    visible_lines = PostBatchLine.objects.select_related("resolution")
    batches = PostBatch.objects.filter(cycle=cycle)
    if view_allowed_ids is not None:
        visible_lines = visible_lines.filter(resolution__sap_location_id__in=view_allowed_ids)
        batches = batches.filter(lines__resolution__sap_location_id__in=view_allowed_ids).distinct()
    batches = list(batches.prefetch_related(Prefetch("lines", queryset=visible_lines, to_attr="visible_lines")))
    return render(
        request,
        "portal/post_batches.html",
        {
            "cycle": cycle,
            "open_batches": [item for item in batches if item.status == PostBatchStatus.DRAFT],
            "batch_history": [item for item in batches if item.status != PostBatchStatus.DRAFT],
            "can_confirm": can_confirm,
        },
    )


@login_required
def post_batch_detail(request, batch_id):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    view_allowed_ids = allowed_sap_location_ids(request.user, "variance.view", plant_id=plant.pk)
    visible_lines = PostBatchLine.objects.select_related("resolution")
    batch_query = PostBatch.objects.filter(cycle=cycle)
    if view_allowed_ids is not None:
        visible_lines = visible_lines.filter(resolution__sap_location_id__in=view_allowed_ids)
        batch_query = batch_query.filter(lines__resolution__sap_location_id__in=view_allowed_ids).distinct()
    batch = get_object_or_404(
        batch_query.prefetch_related(Prefetch("lines", queryset=visible_lines, to_attr="visible_lines")),
        pk=batch_id,
    )
    can_confirm = user_has_action(request.user, "variance.confirm_post_batch")
    if can_confirm:
        confirmation_scope = allowed_sap_location_ids(request.user, "variance.confirm_post_batch", plant_id=plant.pk)
        if confirmation_scope is not None:
            all_line_ids = set(batch.lines.values_list("resolution__sap_location_id", flat=True))
            can_confirm = all_line_ids.issubset(confirmation_scope)
    if request.method == "POST":
        action = request.POST.get("action")
        if not can_confirm:
            raise PermissionDenied("Only CM can confirm or cancel a Post Batch.")
        try:
            if action == "cancel":
                cancel_post_batch(batch.pk, request.user)
                messages.success(request, "Draft Post Batch cancelled.")
            else:
                confirm_post_batch(
                    batch.pk,
                    request.POST.get("sap_document_number"),
                    parse_date(request.POST.get("posting_date", "")),
                    request.user,
                    request.POST.getlist("excluded_line_id"),
                )
                messages.success(request, "SAP posting confirmed; included lines are now Posted.")
        except ValidationError as exc:
            messages.error(request, str(exc))
        return redirect("portal:post-batch-detail", batch_id=batch.pk)
    return render(
        request,
        "portal/post_batch_detail.html",
        {
            "cycle": cycle,
            "batch": batch,
            "can_confirm": can_confirm and cycle.status == CycleStatus.OPEN,
            "is_draft": batch.status == PostBatchStatus.DRAFT,
        },
    )


@login_required
def variance_by_location(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    data = _filtered_variance_data(request, plant, cycle)
    rows = _variance_location_rows(data["metric_lines"], data["filtered_locations"])
    context = {**data, "cycle": cycle, "rows": rows}
    return render(request, "portal/variance_by_location.html", context)


def _variance_workbook(cycle, lines):
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"
    detail_sheet = workbook.create_sheet("Variance Detail")
    header_fill = PatternFill("solid", fgColor="DCEAF7")
    header_font = Font(name="Arial Narrow", bold=True, color="0C3D70")
    body_font = Font(name="Arial Narrow", size=10)

    summary = variance_summary(lines)
    summary_sheet.append([f"{cycle.plant.code} {cycle.name} - Variance Summary", "Value"])
    summary_rows = [
        ("TK Book Value", summary["tk_book_value"]),
        ("TK Count Value", summary["tk_count_value"]),
        ("TK Net Variance", summary["tk_variance_value"]),
        ("TK Variance Accuracy", summary["tk_variance_accuracy"] / 100),
        ("TK Absolute Variance", summary["tk_absolute_variance"]),
        ("TK Absolute Variance Accuracy", summary["tk_absolute_variance_accuracy"] / 100),
        (
            "CS Average P/N Quantity Accuracy",
            (summary["cs_average_pn_quantity_accuracy"] / 100 if summary["cs_average_pn_quantity_accuracy"] is not None else None),
        ),
        ("CS Absolute Quantity Variance", summary["cs_absolute_quantity_variance"]),
    ]
    for item in summary_rows:
        summary_sheet.append(item)
    summary_sheet.column_dimensions["A"].width = 38
    summary_sheet.column_dimensions["B"].width = 22
    for cell in summary_sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
    for row in summary_sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = body_font
    for row_number in (5, 7, 8):
        summary_sheet.cell(row_number, 2).number_format = "0.00%"

    headers = [
        "P/N",
        "Description",
        "BU",
        "MAP$",
        "Inventory Type",
        "Ownership",
        "SAP Location",
        "Book Qty",
        "Count Qty",
        "Variance Qty",
        "Book Value",
        "Count Value",
        "Variance Value",
        "Abs Variance",
        "CS Qty Accuracy",
    ]
    detail_sheet.append(headers)
    for line in lines:
        detail_sheet.append(
            [
                line["part_number"],
                line["description"],
                line["business_unit"],
                line["price"],
                line["inventory_type"],
                line["department"],
                line["sap_location_code"],
                line["book_quantity"],
                line["count_quantity"],
                line["variance_quantity"],
                line["book_value"],
                line["count_value"],
                line["variance_value"],
                abs(line["variance_value"]),
                (line["quantity_accuracy"] / 100 if line["quantity_accuracy"] is not None else None),
            ]
        )
    detail_sheet.freeze_panes = "A2"
    detail_sheet.auto_filter.ref = detail_sheet.dimensions
    widths = [18, 46, 16, 14, 15, 18, 15, 14, 14, 14, 17, 17, 17, 17, 18]
    for index, width in enumerate(widths, 1):
        detail_sheet.column_dimensions[detail_sheet.cell(1, index).column_letter].width = width
    for cell in detail_sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
    for row in detail_sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = body_font
        for column in range(4, 15):
            row[column - 1].number_format = "#,##0.00;[Red]-#,##0.00;0.00"
        row[14].number_format = "0.00%"
    payload = BytesIO()
    workbook.save(payload)
    return payload.getvalue()


@login_required
def variance_export(request):
    plant, cycle = _variance_cycle(request)
    if cycle is None:
        return redirect("portal:cycles")
    data = _filtered_variance_data(request, plant, cycle)
    response = HttpResponse(
        _variance_workbook(cycle, data["lines"]),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{plant.code}_{cycle.name.replace(" ", "_")}_Variance.xlsx"'
    return response
