from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Sum
from django.shortcuts import redirect, render

from core.context_processors import get_basic_info
from core.init_functions.db_init import *
from site_setting.models import Plant
from django.contrib.auth import logout


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
