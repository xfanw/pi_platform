from core._imports_for_views import *
from cycles.app_functions.cycle import gen_cycle_name
from cycles.models import CyclePhysicalLocation, CycleSAPLocation, CycleSubLocation, PICycle
from site_setting.models import PhysicalLocation, SAPLocation, SubLocation

PERMISSION = "Setting.PI Cycles"


# Create your views here.
@login_required
def cycles(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view PI Cycles. {msg}"))
        return redirect("core:home")

    can_manage_cycle, msg = check_permission(curr_user, plant, PERMISSION, True)
    context["may_manage_cycles"] = can_manage_cycle

    active_cycle = context["cycle_ref"]
    if not active_cycle:
        context["cycle_holder"] = gen_cycle_name(plant.code)

        sap_locations = SAPLocation.objects.filter(plant=plant, is_active=True).order_by("code")
        context["sap_locations"] = sap_locations

        locations = PhysicalLocation.objects.filter(sap_location__in=sap_locations, is_active=True).order_by(
            "sap_location__code", "name"
        )
        context["locations"] = locations

        sub_locations = SubLocation.objects.filter(physical_location__in=locations, is_active=True).order_by(
            "physical_location__sap_location__code", "physical_location__name", "name"
        )
        context["sub_locations"] = sub_locations
    else:
        context["open_cycle"] = active_cycle
    context["cycle_history"] = PICycle.objects.filter(plant=plant).order_by("-id")
    context.update(
        {
            # "cycle_history": cycle_history,
            # "form": form,
            "portal_can_view_captures": True,
            # "preview": True,
            # "may_manage": True,
            "may_close": True,
            "close_final_capture": False,
            "close_blockers": ["a", "b"],
        }
    )
    # may_manage = user_has_scoped_action(request.user, "cycles.add_picycle", plant_id=plant.pk)
    # may_close = user_has_scoped_action(request.user, "cycles.close_picycle", plant_id=plant.pk)
    # open_cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()

    # if request.method == "POST":
    #     action = request.POST.get("action")
    #     if action == "close":
    #         if not may_close:
    #             raise PermissionDenied("Your role cannot close this PI Cycle.")
    #         if open_cycle is None or str(open_cycle.pk) != request.POST.get("cycle_id"):
    #             messages.error(request, "That open PI Cycle is no longer available. Refresh and try again.")
    #             return redirect("portal:cycles")
    #         try:
    #             closed = close_cycle(
    #                 cycle_id=open_cycle.pk,
    #                 closed_by=request.user,
    #                 blocker_checks=(lambda cycle: " ".join(cycle_close_readiness(cycle)) or None,),
    #             )
    #             messages.success(
    #                 request,
    #                 f"{closed.name} closed. {closed.follow_up_created_count} unresolved P/N × SAP Location item(s) were carried to Follow-up.",
    #             )
    #             return redirect("portal:cycles")
    #         except ValidationError as exc:
    #             messages.error(request, " ".join(exc.messages))
    #         form = CycleCreateForm(plant=plant)
    #     else:
    #         if not may_manage:
    #             raise PermissionDenied("Your role cannot create a PI Cycle for this Plant.")
    #         form = CycleCreateForm(request.POST, plant=plant)
    #     if action != "close" and form.is_valid():
    #         if action == "preview":
    #             preview = form.cleaned_data
    #         elif action == "create":
    #             try:
    #                 cycle = create_open_cycle(
    #                     plant_id=plant.pk,
    #                     name=form.cleaned_data["name"],
    #                     opened_by=request.user,
    #                     sap_location_ids=form.cleaned_data["sap_location_ids"],
    #                     physical_location_ids=form.cleaned_data["physical_location_ids"],
    #                     sub_location_ids=form.cleaned_data["sub_location_ids"],
    #                 )
    #                 messages.success(request, f"{cycle.name} created and opened.")
    #                 return redirect("portal:cycles")
    #             except ValidationError as exc:
    #                 messages.error(request, " ".join(exc.messages))
    #     elif action != "close":
    #         messages.error(request, "Please complete the required PI name and SAP Location scope.")
    # else:
    #     form = CycleCreateForm(plant=plant)

    # close_final_capture = None
    # close_blockers = []
    # if open_cycle:
    #     close_final_capture = (
    #         PICapture.objects.filter(
    #             cycle=open_cycle,
    #             capture_type__in=[CaptureType.FIVE_DAY_FINAL, CaptureType.CLOSE_FINAL],
    #         )
    #         .order_by("-captured_at")
    #         .first()
    #     )
    #     close_blockers = cycle_close_readiness(open_cycle)

    # cycle_history = list(
    #     PICycle.objects.filter(plant=plant)
    #     .select_related("opened_by", "closed_by")
    #     .prefetch_related(
    #         Prefetch(
    #             "captures",
    #             queryset=PICapture.objects.filter(
    #                 capture_type__in=[
    #                     CaptureType.FIVE_DAY_FINAL,
    #                     CaptureType.CLOSE_FINAL,
    #                 ]
    #             ).order_by("-captured_at"),
    #             to_attr="final_captures",
    #         )
    #     )
    #     .annotate(
    #         follow_up_count=Count("follow_up_items", distinct=True),
    #         follow_up_open_count=Count(
    #             "follow_up_items",
    #             filter=~Q(follow_up_items__status__in=TERMINAL_FOLLOW_UP_STATUSES),
    #             distinct=True,
    #         ),
    #     )
    # )
    # for item in cycle_history:
    #     item.final_capture = next(
    #         (capture for capture in item.final_captures if capture.capture_type == CaptureType.FIVE_DAY_FINAL),
    #         item.final_captures[0] if item.final_captures else None,
    #     )
    return render(request, "cycles/cycles.html", context)


def create_cycle(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view PI Cycles. {msg}"))
        return redirect("core:home")

    curr_time = datetime.now().astimezone()
    post_data = request.POST

    sap_location_ids = post_data.getlist("sap_location_ids", [])
    location_ids = post_data.getlist("location_ids", [])
    sub_location_ids = post_data.getlist("sub_location_ids", [])

    if not sap_location_ids or not location_ids:
        messages.error(request, "SAP Location and Physical Location are required. ")
        return redirect("cycles:cycles")

    cycle_name = post_data.get("cycle_name", "").strip()
    if PICycle.objects.filter(plant=plant, status="OPEN").exists():
        messages.error(request, "This plant already has an open PI Cycle.")
        return redirect("cycles:cycles")

    sap_location_set = SAPLocation.objects.filter(pk__in=sap_location_ids, plant=plant, is_active=True)
    if sap_location_set.count() != len(sap_location_ids):
        messages.error(request, "One or more SAP Locations are outside this plant or inactive.")
        return redirect("cycles:cycles")

    location_set = PhysicalLocation.objects.filter(
        pk__in=location_ids, sap_location_id__in=sap_location_ids, plant=plant, is_active=True
    )
    if location_set.count() != len(location_ids):
        messages.error(request, "One or more Physical Locations are outside the SAP scope.")
        return redirect("cycles:cycles")

    sub_location_set = SubLocation.objects.filter(
        pk__in=sub_location_ids,
        physical_location_id__in=location_ids,
        plant=plant,
        is_active=True,
    )

    if sub_location_set.count() != len(sub_location_ids):
        messages.error(request, "One or more Sub-locations are outside the Physical scope.")
        return redirect("cycles:cycles")

    try:
        cycle_ref = PICycle.objects.create(
            plant=plant,
            name=cycle_name,
            status="OPEN",
            opened_at=curr_time,
            opened_by=curr_user,
            created_at=curr_time,
            created_by=curr_user,
            updated_at=curr_time,
            updated_by=curr_user,
        )

        CycleSAPLocation.objects.bulk_create(
            [
                CycleSAPLocation(
                    plant=plant,
                    cycle=cycle_ref,
                    sap_location=item,
                    created_by=curr_user,
                    updated_by=curr_user,
                )
                for item in sap_location_set
            ]
        )
        CyclePhysicalLocation.objects.bulk_create(
            [
                CyclePhysicalLocation(
                    plant=plant,
                    cycle=cycle_ref,
                    physical_location=item,
                    created_by=curr_user,
                    updated_by=curr_user,
                )
                for item in location_set
            ]
        )
        CycleSubLocation.objects.bulk_create(
            [
                CycleSubLocation(
                    plant=plant,
                    cycle=cycle_ref,
                    sub_location=item,
                    created_by=curr_user,
                    updated_by=curr_user,
                )
                for item in sub_location_set
            ]
        )
    except Exception as e:
        messages.error(request, mark_safe(f"Error Creating New Cycle {cycle_name}. {clean_errors(e)}"))
        return redirect("cycles:cycles")

    messages.success(request, f"Cycle {cycle_name} created and opened.")
    return redirect("cycles:cycles")
