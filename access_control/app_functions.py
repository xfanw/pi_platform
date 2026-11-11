from datetime import datetime

from django.db.models import Q
from access_control.models import RoleAction, RoleAssignment
from site_setting.models import Plant, SAPLocation


def active_roles(user, curr_time=None):
    curr_time = curr_time or datetime.now().astimezone()
    return RoleAssignment.objects.filter(user=user, is_active=True).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=curr_time),
        Q(valid_to__isnull=True) | Q(valid_to__gte=curr_time),
    )


def active_plant_roles(user, plant, curr_time=None):
    curr_time = curr_time or datetime.now().astimezone()
    return RoleAssignment.objects.filter(user=user, is_active=True, plant=plant).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=curr_time),
        Q(valid_to__isnull=True) | Q(valid_to__gte=curr_time),
    )


def is_global_manager(user):
    return user.is_superuser or active_roles(user).filter(role="Global Admin").exists()


def is_plant_manager(user, plant, *, role_name="Plant Admin"):
    if role_name != "Plant Admin":
        return False
    return active_roles(user).filter(role=role_name, plant=plant).exists()


def my_sap_loc(user, plant, curr_time=None):
    active_role_set = active_plant_roles(user, plant, curr_time=curr_time)
    if not active_role_set:
        return set()
    if active_role_set.filter(sap_location__isnull=True).exists():
        return set(SAPLocation.objects.filter(plant=plant, is_active=True).values_list("code", flat=True))

    return set(active_role_set.filter(sap_location__isnull=False).values_list("sap_location__code", flat=True))


def check_permission(curr_user, plant, app_name, editable=False):
    """Check if user has permission to continue their action

    Args:
        curr_user: django user object / request.user
        plant: current plant in session
        app_name: frontend links like Setting.Plant Setup

    Returns:
        has_permission: Boolean
        msg: String explaining why the user does not have permission
    """

    if curr_user.is_anonymous:
        return False, ""

    if not curr_user.is_active:
        return False, ""

    if curr_user.is_superuser:
        return True, ""

    if is_global_manager(curr_user):
        return True, ""

    if not editable:
        roles_list = list(RoleAction.objects.filter(access_page=app_name).values_list("role", flat=True))
    else:
        roles_list = list(RoleAction.objects.filter(access_page=app_name, can_edit=editable).values_list("role", flat=True))

    if active_roles(curr_user).filter(role__in=roles_list, plant=plant).exists():
        return True, ""

    msg = f"To Access <b>{app_name}</b>: You need to be assigned to <br> <b>{', or '.join(roles_list)}</b>"

    return False, f"<br>{msg}"


def available_plants(user):
    if not user.is_authenticated:
        return Plant.objects.none()

    if user.is_superuser:
        return Plant.objects.filter(is_active=True)

    roles_set = active_roles(user)
    if roles_set.filter(role="Global Admin").exists():
        return Plant.objects.filter(is_active=True)

    return Plant.objects.filter(
        id__in=roles_set.exclude(plant_id=None).values("plant_id"),
        is_active=True,
    ).distinct()


def manageable_plants(user):
    if is_global_manager(user):
        return Plant.objects.filter(is_active=True)

    active_plant_admins = active_roles(user).filter(role="Plant Admin")
    return Plant.objects.filter(
        id__in=active_plant_admins.values("plant_id"),
        is_active=True,
    ).distinct()


def can_manage_target(curr_user, target_user):
    if is_global_manager(curr_user):
        return True, ""

    if is_global_manager(target_user):
        return False, "Only a Global Admin can manage this account."

    manageable_plant_set = set(manageable_plants(curr_user).values_list("code", flat=True))
    target_plant_set = set(active_roles(target_user).values_list("plant__code", flat=True))
    if manageable_plant_set.isdisjoint(target_plant_set):
        return False, "This user is outside your administration scope."

    return True, ""
