from django.urls import path

from audit.app_views.planning import audit_input, audit_plan_detail, audit_planning, audit_planning_create, audit_input

app_name = "audit"

urlpatterns = [
    path("audit_planning", audit_planning, name="audit_planning"),
    path("audit_planning_create", audit_planning_create, name="audit_planning_create"),
    path("audit_plan_detail/<int:plan_id>", audit_plan_detail, name="audit_plan_detail"),
    path("audit_input/<int:plan_id>", audit_input, name="audit_input"),
]
