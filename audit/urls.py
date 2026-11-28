from django.urls import path

from audit.app_views.plan_detail import (
    audit_candidate_detail,
    audit_candidate_update,
    audit_plan_detail,
    audit_plan_regenerate,
    audit_plan_finalize,
)
from audit.app_views.planning import audit_result, audit_planning, audit_planning_create

app_name = "audit"

urlpatterns = [
    path("audit_planning", audit_planning, name="audit_planning"),
    path("audit_planning_create", audit_planning_create, name="audit_planning_create"),
    path("audit_result/<int:plan_id>", audit_result, name="audit_result"),
]

urlpatterns += [
    path("audit_plan_detail/<int:plan_id>", audit_plan_detail, name="audit_plan_detail"),
    path("audit_plan_regenerate/<int:plan_id>", audit_plan_regenerate, name="audit_plan_regenerate"),
    path("audit_candidate_detail/<int:candidate_id>", audit_candidate_detail, name="audit_candidate_detail"),
    path("audit_candidate_update/<int:candidate_id>", audit_candidate_update, name="audit_candidate_update"),
    path("audit_plan_finalize/<int:plan_id>", audit_plan_finalize, name="audit_plan_finalize"),
]
