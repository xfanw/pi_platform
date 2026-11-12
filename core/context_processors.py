# from apps.access_control.models import BusinessRole
# from django.db.models import Q

# from apps.access_control.policy import (
#     active_assignments,
#     allowed_sap_location_ids,
#     assignments_for_action,
#     user_has_action,
#     user_has_scoped_action,
# )
# from apps.counting.models import (
#     CorrectionStatus,
#     CountCorrection,
#     CountIntakeException,
#     ExceptionStatus,
# )
# from apps.cycles.models import CycleStatus, PICycle
# from apps.follow_up.models import FollowUpItem, TERMINAL_FOLLOW_UP_STATUSES
# from apps.plants.models import Plant


from access_control.app_functions import active_plant_roles, available_plants, is_global_manager, is_plant_manager, my_sap_loc
from access_control.models import RoleAction
from count.models import CountIntakeException
from cycles.models import PICycle

# def portal_context(request):
#     context = {}
#     curr_user = request.user
#     if not curr_user.is_authenticated:
#         return context

#     # 1. Get Plant Info
#     plants = available_plants(curr_user)
#     selected_id = request.session.get("selected_plant_id")

#     plant = plants.filter(pk=selected_id).first()
#     if plant is None:
#         plant = plants.first()
#         if plant:
#             request.session["selected_plant_id"] = plant.pk

#     context["portal_plants"] = plants
#     context["portal_plant_code"] = plant.code if plant else None

#     # 2. Get Role Info
#     global_admin = is_global_manager(curr_user)
#     if global_admin:
#         role_names = ["Global Admin"]
#         curr_role = "Global Admin"
#     else:
#         role_names = list(active_plant_roles(curr_user, plant).values_list("role", flat=True))
#         selected_role = request.session.get("selected_role_id")
#         curr_role = selected_role if selected_role else role_names[0] if role_names else ""
#     context["portal_role_names"] = role_names
#     context["portal_curr_role"] = curr_role

#     page_access_list = set(RoleAction.objects.filter(role=curr_role).values_list("access_page", flat=True))
#     context["page_access_list"] = page_access_list
#     context["page_access_group"] = set(page.split(".", 1)[0] for page in page_access_list)

#     cycle = None
#     if plant:
#         cycle = PICycle.objects.filter(plant=plant, status="OPEN").first()
#         last_closed = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-closed_at").first()
#         context["portal_cycle_name"] = cycle.name if cycle else None
#         context["portal_last_closed"] = last_closed.name if last_closed else None
#     # pprint(context)
#     return context

# cycle = None
# last_closed = None
# if plant:
#     cycle = PICycle.objects.filter(plant=plant, status=CycleStatus.OPEN).first()
#     last_closed = PICycle.objects.filter(plant=plant, status=CycleStatus.CLOSED).first()

# if request.user.is_superuser:
#     role_values = [BusinessRole.Global Admin]
# else:
#     role_values = list(active_assignments(request.user).values_list("role", flat=True).distinct())
# role_labels = dict(BusinessRole.choices)
# role_names = [role_labels.get(role, role) for role in role_values]

# def has_plant_action(action):
#     if not plant:
#         return False
#     if request.user.is_superuser:
#         return True
#     return assignments_for_action(request.user, action).filter(Q(role=BusinessRole.Global Admin) | Q(plant=plant)).exists()

# can_view_pending = has_plant_action("counting.view_countintakeexception")
# pending_count = 0
# if cycle and can_view_pending:
#     allowed_ids = allowed_sap_location_ids(
#         request.user,
#         "counting.view_countintakeexception",
#         plant_id=plant.pk,
#     )
#     pending_query = CountIntakeException.objects.filter(
#         cycle=cycle,
#         status=ExceptionStatus.PENDING,
#     )
#     if allowed_ids is not None:
#         pending_query = pending_query.filter(sap_location_id__in=allowed_ids)
#     pending_count = pending_query.count()

# can_view_audit = has_plant_action("audit.view_auditplan")
# can_view_audit_corrections = has_plant_action("counting.view_countcorrection")
# can_view_audit_accuracy = has_plant_action("audit.view_auditaccuracy")
# can_view_variance = has_plant_action("variance.view")
# can_view_post_batches = can_view_variance
# can_view_captures = has_plant_action("capture.view")
# can_create_captures = has_plant_action("capture.create")
# can_view_five_day = has_plant_action("five_day.view")
# can_view_follow_up = has_plant_action("follow_up.view")
# can_manage_users = user_has_action(request.user, "access_control.manage_roleassignment")
# can_manage_dropdowns = has_plant_action("plants.manage_businessoption")
# can_manage_notification_routes = has_plant_action("notifications.manage_notificationroute")
# prior_follow_up_count = 0
# if plant and can_view_follow_up:
#     follow_up_query = FollowUpItem.objects.filter(plant=plant).exclude(status__in=TERMINAL_FOLLOW_UP_STATUSES)
#     if cycle:
#         follow_up_query = follow_up_query.exclude(source_cycle=cycle)
#     allowed_ids = allowed_sap_location_ids(request.user, "follow_up.view", plant_id=plant.pk)
#     if allowed_ids is not None:
#         follow_up_query = follow_up_query.filter(sap_location_id__in=allowed_ids)
#     prior_follow_up_count = follow_up_query.count()
# audit_correction_count = 0
# if cycle and can_view_audit_corrections:
#     correction_query = CountCorrection.objects.filter(
#         count_record__cycle=cycle,
#         audit_record__isnull=False,
#         status=CorrectionStatus.SUBMITTED,
#     )
#     allowed_ids = allowed_sap_location_ids(
#         request.user,
#         "counting.view_countcorrection",
#         plant_id=plant.pk,
#     )
#     if allowed_ids is not None:
#         correction_query = correction_query.filter(count_record__sap_location_id__in=allowed_ids)
#     audit_correction_count = correction_query.count()

# task_count = 0
# if plant:
#     from apps.notifications.tasks import task_count_for_user

#     task_count = task_count_for_user(user=request.user, plant=plant, cycle=cycle)

# return {
#     "portal_plants": plants,
#     "portal_plant": plant,
#     "portal_cycle": cycle,
#     "portal_last_closed": last_closed,
#     "portal_role_names": role_names,
#     "portal_is_admin": request.user.is_superuser
#     or BusinessRole.Global Admin in role_values
#     or BusinessRole.Plant Admin in role_values,
#     "portal_can_manage_plant_master": has_plant_action("plants.manage_plantsetup"),
#     "portal_can_view_parts": bool(plant and user_has_scoped_action(request.user, "inventory.view_partmaster", plant_id=plant.pk)),
#     "portal_can_view_book": bool(
#         plant
#         and user_has_scoped_action(
#             request.user,
#             "inventory.view_bookinventoryline",
#             plant_id=plant.pk,
#         )
#     ),
#     "portal_can_view_exclusions": bool(
#         plant and user_has_scoped_action(request.user, "inventory.view_excludedpart", plant_id=plant.pk)
#     ),
#     "portal_can_add_count": has_plant_action("counting.add_countrecord"),
#     "portal_can_view_counts": has_plant_action("counting.view_countrecord"),
#     "portal_can_view_pending": can_view_pending,
#     "portal_pending_count": pending_count,
#     "portal_can_view_audit": can_view_audit,
#     "portal_can_view_audit_corrections": can_view_audit_corrections,
#     "portal_can_view_audit_accuracy": can_view_audit_accuracy,
#     "portal_audit_correction_count": audit_correction_count,
#     "portal_can_view_variance": can_view_variance,
#     "portal_can_view_post_batches": can_view_post_batches,
#     "portal_can_view_captures": can_view_captures,
#     "portal_can_create_captures": can_create_captures,
#     "portal_can_view_five_day": can_view_five_day,
#     "portal_can_view_follow_up": can_view_follow_up,
#     "portal_can_manage_users": can_manage_users,
#     "portal_can_manage_dropdowns": can_manage_dropdowns,
#     "portal_can_manage_notification_routes": can_manage_notification_routes,
#     "portal_can_view_readiness": bool(
#         request.user.is_superuser or BusinessRole.Global Admin in role_values or BusinessRole.Plant Admin in role_values
#     ),
#     "portal_can_manage_roster": has_plant_action("plants.manage_counterroster"),
#     "portal_prior_follow_up_count": prior_follow_up_count,
#     "portal_task_count": task_count,
# }


def get_basic_info(request):
    context = {}
    curr_user = request.user
    if not curr_user.is_authenticated:
        return context

    # 1. Get Plant Info
    plants = available_plants(curr_user)
    selected_id = request.session.get("selected_plant_id")

    plant = plants.filter(pk=selected_id).first()
    if plant is None:
        plant = plants.first()
        if plant:
            request.session["selected_plant_id"] = plant.pk

    context["portal_plants"] = plants
    context["plant_ref"] = plant
    context["portal_plant_code"] = plant.code if plant else None

    # 2. Get Role Info
    global_admin = is_global_manager(curr_user)
    context["is_global_admin"] = global_admin
    plant_admin = is_plant_manager(curr_user, plant)
    if global_admin:
        role_names = ["Global Admin"]
        curr_role = "Global Admin"
    else:
        role_names = list(active_plant_roles(curr_user, plant).values_list("role", flat=True))
        selected_role = request.session.get("selected_role_id")
        curr_role = selected_role if selected_role else role_names[0] if role_names else ""
    context["portal_role_names"] = role_names
    context["portal_curr_role"] = curr_role

    page_access_list = set(RoleAction.objects.filter(role=curr_role).values_list("access_page", flat=True))
    context["page_access_list"] = page_access_list
    context["page_access_group"] = set(page.split(".", 1)[0] for page in page_access_list)

    cycle = None
    if plant:
        cycle = PICycle.objects.filter(plant=plant, status="OPEN").first()
        last_closed = PICycle.objects.filter(plant=plant, status="CLOSED").order_by("-closed_at").first()
        context["portal_cycle_name"] = cycle.name if cycle else None
        context["portal_last_closed"] = last_closed.name if last_closed else None

    context["cycle_ref"] = cycle
    portal_pending_count = 0
    if cycle:
        count_ex_set = CountIntakeException.objects.filter(cycle=cycle)
        if count_ex_set:
            if not global_admin and not plant_admin:
                my_sap_list = my_sap_loc(curr_user, plant)
                count_ex_set = count_ex_set.filter(sap_location__code__in=my_sap_list)
            portal_pending_count = count_ex_set.filter(status="Pending").count()
    context["portal_pending_count"] = portal_pending_count

    # pprint(context)
    return context
