from access_control.models import RoleAction, RoleApp, RoleGroup
from core.db_connection import MESRawDB
from core.models import User


def init_admin_user():
    admin_ref = User.objects.filter(username="SYSTEM").first()
    if not admin_ref:
        User.objects.create_user(
            username="SYSTEM",
            email="admin@foxconn.com",
            password="Foxconn1!",
            is_active=False,
        )


def init_role():
    RoleAction.objects.all().delete()
    RoleGroup.objects.all().delete()
    RoleApp.objects.all().delete()
    MESRawDB().reset_index(["access_control_roleaction_id_seq", "access_control_rolegroup_id_seq", "access_control_roleapp_id_seq"])
    init_role_group()
    init_role_app()
    init_role_actions()


def init_role_actions():
    ROLE_ACTIONS = {
        "Global Admin": {
            "Setting.Plant Setup": True,
            "Setting.PI Cycles": True,
            "Setting.Location": True,
            "Setting.Tag Range": True,
            "Setting.Counter": True,
            "Setting.Data Entry": True,
            "Book Inventary.PN List": True,
            "Book Inventary.SAP Inventary": True,
            "Book Inventary.Exclude PN List": True,
            "Count.Manual Key-In": True,
            "Count.Tag Key-In": True,
            "Count.Count Result Upload": True,
            "Count.WMS Feed": True,
            "Count.Virtual Tag Scan": True,
            "Count.Count Results": True,
            "Count.Pending Station": True,
            "Audit.Audit Pending": True,
            "Audit.Audit Correction": True,
            "Audit.Audit Accuracy": True,
            "Variance.Live Variance Report": True,
            "Variance.Variance by PN": True,
            "Variance.Variance by Location": True,
            "Variance.Post Batches": True,
            "5-Day Update.Capture History": True,
            "5-Day Update.5-Day Update": True,
            "5-Day Update.Follow-up Register": True,
            "Admin.Dropdown Management": True,
            "Admin.Notification Routing": True,
            "Admin.System Readiness": True,
            "Admin.User Management": True,
            # "Admin.Bulk People Onboarding": True,
            "Admin.Role & Permissions": True,
            "Admin.Access History": True,
            "Admin.Database Administration": True,
        },
        "Plant Admin": {
            "Setting.Plant Setup": True,
            "Setting.PI Cycles": True,
            "Setting.Location": True,
            "Setting.Tag Range": True,
            "Setting.Counter": True,
            "Setting.Data Entry": True,
            "Book Inventary.PN List": True,
            "Book Inventary.SAP Inventary": True,
            "Book Inventary.Exclude PN List": True,
            "Count.Manual Key-In": True,
            "Count.Tag Key-In": True,
            "Count.Count Result Upload": True,
            "Count.WMS Feed": True,
            "Count.Virtual Tag Scan": True,
            "Count.Count Results": True,
            "Count.Pending Station": True,
            "Audit.Audit Pending": True,
            "Audit.Audit Correction": True,
            "Audit.Audit Accuracy": True,
            "Variance.Live Variance Report": True,
            "Variance.Variance by PN": True,
            "Variance.Variance by Location": True,
            "Variance.Post Batches": True,
            "5-Day Update.Capture History": True,
            "5-Day Update.5-Day Update": True,
            "5-Day Update.Follow-up Register": True,
            "Admin.Dropdown Management": True,
            # "Admin.Notification Routing":True,
            # "Admin.System Readiness":True,
            "Admin.User Management": True,
            # "Admin.Bulk People Onboarding": True,
            "Admin.Role & Permissions": True,
            # "Admin.Access History":True,
            # "Admin.Database Administration":True,
        },
        "Data Entry": {
            "Setting.PI Cycles": False,
            "Count.Manual Key-In": True,
            "Count.Tag Key-In": True,
            "Count.Count Result Upload": True,
            "Count.WMS Feed": True,
            "Count.Virtual Tag Scan": True,
            "Count.Count Results": True,
            "Count.Pending Station": True,
        },
        "Varience Viewer": {
            "Count.Manual Key-In": True,
            "Count.Tag Key-In": True,
            "Count.Count Result Upload": True,
            "Count.WMS Feed": True,
            "Count.Virtual Tag Scan": True,
            "Count.Count Results": True,
            "Count.Pending Station": True,
            "Audit.Audit Pending": True,
            "Audit.Audit Correction": True,
            "Audit.Audit Accuracy": True,
            "Variance.Live Variance Report": True,
            "Variance.Variance by PN": True,
            "Variance.Variance by Location": True,
            "Variance.Post Batches": True,
            "5-Day Update.Capture History": True,
            "5-Day Update.5-Day Update": True,
            "5-Day Update.Follow-up Register": True,
        },
        "Varience Approver": {
            "Count.Manual Key-In": True,
            "Count.Tag Key-In": True,
            "Count.Count Result Upload": True,
            "Count.WMS Feed": True,
            "Count.Virtual Tag Scan": True,
            "Count.Count Results": True,
            "Count.Pending Station": True,
            "Audit.Audit Pending": True,
            "Audit.Audit Correction": True,
            "Audit.Audit Accuracy": True,
            "Variance.Live Variance Report": True,
            "Variance.Variance by PN": True,
            "Variance.Variance by Location": True,
            "Variance.Post Batches": True,
            "5-Day Update.Capture History": True,
            "5-Day Update.5-Day Update": True,
            "5-Day Update.Follow-up Register": True,
        },
        "CM": {
            "Setting.Plant Setup": True,
            "Setting.PI Cycles": True,
            "Setting.Location": True,
            "Setting.Tag Range": True,
            "Setting.Counter": True,
            "Setting.Data Entry": True,
            "Book Inventary.PN List": True,
            "Book Inventary.SAP Inventary": True,
            "Book Inventary.Exclude PN List": True,
            "Count.Manual Key-In": True,
            "Count.Tag Key-In": True,
            "Count.Count Result Upload": True,
            "Count.WMS Feed": True,
            "Count.Virtual Tag Scan": True,
            "Count.Count Results": True,
            "Count.Pending Station": True,
            "Audit.Audit Pending": True,
            "Audit.Audit Correction": True,
            "Audit.Audit Accuracy": True,
            "Variance.Live Variance Report": True,
            "Variance.Variance by PN": True,
            "Variance.Variance by Location": True,
            "Variance.Post Batches": True,
            "5-Day Update.Capture History": True,
            "5-Day Update.5-Day Update": True,
            "5-Day Update.Follow-up Register": True,
        },
    }
    role_action_list = []
    for role, permissions in ROLE_ACTIONS.items():
        for permission, can_edit in permissions.items():
            role_action_list.append(RoleAction(role=role, access_page_id=permission, can_edit=can_edit))
    RoleAction.objects.bulk_create(role_action_list)


def init_role_group():
    RoleGroup.objects.all().delete()
    MESRawDB().reset_index(["access_control_rolegroup_id_seq"])
    ROLE_METADATA = {
        "Global Admin": {
            "holder": "Corporate platform support",
            "scope": "All Plants",
            "description": "Platform administration across every Plant.",
            "group_order": 1,
        },
        "Plant Admin": {
            "holder": "Inventory Control / local Finance admin",
            "scope": "Assigned Plant",
            "description": "Manages the assigned Plant setup, Ownerships, SAP Locations, PI cycle, users and reporting defaults.",
            "group_order": 2,
        },
        "Data Entry": {
            "holder": "Data-entry operator",
            "scope": "Assigned Plant, Ownership or SAP Location",
            "description": "Enters counts through assigned channels and sees assigned results.",
            "group_order": 3,
        },
        "Varience Viewer": {
            "holder": "Lead / supervisor / inventory analyst",
            "scope": "Assigned Plant or Ownership",
            "description": "Views dashboards and reports, reviews variance, comments, and submits update requests.",
            "group_order": 4,
        },
        "Varience Approver": {
            "holder": "Location owner / manager",
            "scope": "Assigned Plant or Ownership",
            "description": "Makes Post / Not Post decisions and submits update requests.",
            "group_order": 5,
        },
        "CM": {
            "holder": "CM / Inventory Control / Finance",
            "scope": "Assigned Plant or Ownership",
            "description": "Plans and approves audits, applies corrections, validates updates, and confirms SAP Post Batches.",
            "group_order": 6,
        },
    }
    admin = User.objects.filter(username="SYSTEM").first()
    role_group_list = []
    for role, action in ROLE_METADATA.items():
        role_group_list.append(
            RoleGroup(
                group_name=role,
                holder=action.get("holder", ""),
                scope=action.get("scope", ""),
                description=action.get("description", ""),
                group_order=action.get("group_order", 0),
                created_by=admin,
                updated_by=admin,
            )
        )
    RoleGroup.objects.bulk_create(role_group_list)


def init_role_app():
    RoleApp.objects.all().delete()
    app_list = [
        "Setting.Plant Setup",
        "Setting.Location",
        "Setting.PI Cycles",
        "Setting.Tag Range",
        "Setting.Counter",
        "Setting.Data Entry",
        "Book Inventary.PN List",
        "Book Inventary.SAP Inventary",
        "Book Inventary.Exclude PN List",
        "Count.Manual Key-In",
        "Count.Tag Key-In",
        "Count.Count Result Upload",
        "Count.WMS Feed",
        "Count.Virtual Tag Scan",
        "Count.Count Results",
        "Count.Pending Station",
        "Audit.Audit Pending",
        "Audit.Audit Correction",
        "Audit.Audit Accuracy",
        "Variance.Live Variance Report",
        "Variance.Variance by PN",
        "Variance.Variance by Location",
        "Variance.Post Batches",
        "5-Day Update.Capture History",
        "5-Day Update.5-Day Update",
        "5-Day Update.Follow-up Register",
        "Admin.Dropdown Management",
        "Admin.Notification Routing",
        "Admin.System Readiness",
        "Admin.User Management",
        # "Admin.Bulk People Onboarding",
        "Admin.Role & Permissions",
        "Admin.Access History",
        "Admin.Database Administration",
    ]
    order_dict = {
        "Setting": 100,
        "Book Inventary": 200,
        "Count": 300,
        "Audit": 400,
        "Variance": 500,
        "5-Day Update": 600,
        "Admin": 700,
    }
    role_app_list = []
    order = 0
    for app in app_list:
        order += 1
        role_app_list.append(
            RoleApp(
                app_name=app,
                app_order=order + order_dict.get(app.split(".")[0], 0),
            )
        )
    RoleApp.objects.bulk_create(role_app_list)
