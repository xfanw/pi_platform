################################################################################
#     user_list
#     create_user
#     user_detail
#     edit_user
#     reset_password
#     assign_user_role
#     remove_user_role
################################################################################

from core._imports_for_views import *

# from django.db.models import Q
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt

from access_control.app_functions import (
    is_global_manager,
    is_plant_manager,
    manageable_plants,
    can_manage_target,
)
from access_control.forms import PasswordResetForm, UserCreateForm, UserProfileForm
from access_control.models import RoleAssignment
from site_setting.models import Plant, SAPLocation
from site_setting.system_setting.sys_settings import SysSet

PERMISSION = "Admin.User Management"


# Create your views here.
@login_required
def user_list(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view users. {msg}"))
        return redirect("core:home")

    context["create_form"] = UserCreateForm()
    if is_global_manager(curr_user):
        users = User.objects.exclude(username="SYSTEM").order_by("-id")
    elif is_plant_manager(curr_user, plant):
        users = User.objects.filter(role_assignments__plant=plant).exclude(username="SYSTEM").order_by("-id").distinct()
    else:
        messages.error(request, "You do NOT have permission to view users.")
        return redirect("core:home")

    post_data = request.GET
    search = post_data.get("search", "").strip()
    if search:
        context["search"] = search
        users = users.filter(
            Q(username__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(role_assignments__role__icontains=search)
        ).distinct()

    assignments = RoleAssignment.objects.filter(user__in=users).select_related("plant", "sap_location")
    assignment_map = {}
    for assignment in assignments:
        assignment_map.setdefault(assignment.user_id, []).append(assignment)

    rows = []
    for item in users:
        rows.append({"user": item, "assignments": assignment_map.get(item.pk, [])})
    context["rows"] = rows
    return render(request, "access_control/user_list.html", context)


@login_required
@csrf_exempt
def create_user(request):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        return json_error(f"You do NOT have permission to create new users. {msg}")

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            return json_success(f"User {user.username} created successfully.")
        else:
            return json_error(f"Error creating user: <br> {'<br>'.join(form_errors(form))}")
    # TODO: Keep Log
    return json_error("Invalid request method. Only POST requests are allowed.")


@login_required
def user_detail(request, user_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to view user detail. {msg}"))
        return redirect("access_control:user_list")

    target = User.objects.filter(pk=user_id).first()
    if not target:
        messages.error(request, "User not found.")
        return redirect("access_control:user_list")

    context["target"] = target
    status, msg = can_manage_target(curr_user, target)
    if not status:
        messages.error(request, msg)
        return redirect("access_control:user_list")

    plant_list = manageable_plants(curr_user)
    context["plant_list"] = plant_list

    role_list = SysSet().get_val("BUSINESS_ROLE")
    context["role_list"] = role_list

    if not is_global_manager(curr_user):
        context["role_list"].remove("Global Admin")

    context["sap_locations"] = list(SAPLocation.objects.filter(plant__in=plant_list).values("plant__code", "department", "code"))
    if is_global_manager(target):
        assignment_rows = RoleAssignment.objects.filter(user=target).filter(Q(plant__in=plant_list) | Q(plant=None)).order_by("-id")
    else:
        assignment_rows = RoleAssignment.objects.filter(user=target, plant__in=plant_list).order_by("-id")

    context["assignment_rows"] = assignment_rows
    return render(request, "access_control/user_detail.html", context)


@login_required
def edit_user(request, user_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to edit user detail. {msg}"))
        return redirect("access_control:user_list")

    target = User.objects.filter(pk=user_id).first()
    if not target:
        messages.error(request, "User not found.")
        return redirect("access_control:user_list")

    status, msg = can_manage_target(curr_user, target)
    if not status:
        messages.error(request, msg)
        return redirect("access_control:user_detail", user_id=user_id)

    post_data = request.POST
    is_active = post_data.get("status") == "active"
    if target == request.user and not is_active:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("access_control:user_detail", user_id=user_id)

    form = UserProfileForm(request.POST, instance=target)
    if form.is_valid():
        form.save()
        # TODO: Keep Log
        # _write_log(
        #     request,
        #     "PROFILE_UPDATED",
        #     target=target,
        #     plant=current_plant,
        #     detail="Display name or email updated.",
        # )
        messages.success(request, "Profile saved.")
    else:
        messages.error(request, mark_safe(f"Error editing user: <br> {'<br>'.join(form_errors(form))}"))

    return redirect("access_control:user_detail", user_id=user_id)


@login_required
def reset_password(request, user_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        return json_error("No Plant is available in your approved scope.")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        return json_error(f"You do NOT have permission to reset passwords. {msg}")

    target = User.objects.filter(pk=user_id).first()
    if not target:
        return json_error("User not found.")

    status, msg = can_manage_target(curr_user, target)
    if not status:
        return json_error(msg)

    form = PasswordResetForm(request.POST)

    if form.is_valid():
        target.set_password(form.cleaned_data["password"])
        target.save(update_fields=["password"])
        # TODO: Keep Log
        # _write_log(
        #     request,
        #     "PASSWORD_RESET",
        #     target=target,
        #     plant=current_plant,
        #     detail="Temporary password set by an administrator.",
        # )
        return json_success(f"Temporary password for {target.username} is updated.")
    else:
        return json_error(f"Error update user password: <br> {'<br>'.join(form_errors(form))}")


@login_required
def assign_user_role(request, user_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        messages.error(request, "No Plant is available in your approved scope.")
        return redirect("core:home")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        messages.error(request, mark_safe(f"You do NOT have permission to assign user roles. {msg}"))
        return redirect("access_control:user_list")

    target = User.objects.filter(pk=user_id).first()
    if not target:
        messages.error(request, "User not found.")
        return redirect("access_control:user_list")

    status, msg = can_manage_target(curr_user, target)
    if not status:
        messages.error(request, msg)
        return redirect("access_control:user_detail", user_id=user_id)
    curr_time = datetime.now().astimezone()
    post_data = request.POST
    role = post_data.get("role", "")
    plant_code = post_data.get("plant", "")
    plant_ref = Plant.objects.filter(code=plant_code).first()
    department = post_data.get("department", "")
    sap_code = post_data.get("sap_location", "")
    sap_ref = SAPLocation.objects.filter(plant=plant_ref, code=sap_code).first()
    valid_from_str = post_data.get("valid_from", "")
    valid_to_str = post_data.get("valid_from", "")
    valid_from = datetime.strptime(valid_from_str, "%Y-%m-%dT%H:%M").astimezone() if valid_from_str else curr_time
    valid_to = datetime.strptime(valid_to_str, "%Y-%m-%dT%H:%M").astimezone() if valid_to_str else None

    role_ref = RoleAssignment.objects.filter(
        user=target, role=role, plant=plant_ref, department=department, sap_location=sap_ref, is_active=True
    ).first()
    if role_ref:
        messages.error(request, f"Same role setting for user {target.username} already exists. ")
        return redirect("access_control:user_detail", user_id=user_id)

    RoleAssignment.objects.create(
        user=target, role=role, plant=plant_ref, department=department, sap_location=sap_ref, valid_from=valid_from, valid_to=valid_to
    )
    # TODO: Add Log
    return redirect("access_control:user_detail", user_id=user_id)


@login_required
def remove_user_role(request, role_id):
    curr_user = request.user
    context = get_basic_info(request)
    plant = context["plant_ref"]
    if not plant:
        return json_error("No Plant is available in your approved scope.")

    can_act, msg = check_permission(curr_user, plant, PERMISSION, True)
    if not can_act:
        return json_error(f"You do NOT have permission to assign user roles. {msg}")

    role_ref = RoleAssignment.objects.filter(id=role_id).first()
    if not role_ref:
        return json_error("Role assignment not found.")
    role_name = role_ref.role
    target = role_ref.user
    role_ref.delete()

    # TODO: Add Log
    return json_success(f"Role {role_name} is removed from user {target.username}")
