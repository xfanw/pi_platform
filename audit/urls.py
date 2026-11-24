from django.urls import path

from audit.app_views.planning import audit_planning

app_name = "audit"

urlpatterns = [
    path("audit_planning", audit_planning, name="audit_planning"),
]
