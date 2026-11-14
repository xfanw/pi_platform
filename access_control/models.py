from django.db import models

from core.models import ActiveModel, TimeStampedModel
from django.db.models import Q
from site_setting.models import Plant, SAPLocation

from django.contrib.auth.models import User


class RoleGroup(TimeStampedModel):
    group_name = models.CharField(max_length=31, unique=True)
    holder = models.CharField(max_length=63, blank=True)
    scope = models.CharField(max_length=63, blank=True)
    description = models.CharField(max_length=255, blank=True)
    group_order = models.IntegerField(default=0)


class RoleApp(models.Model):
    app_name = models.CharField(max_length=31, unique=True)
    app_order = models.IntegerField(default=0)


class RoleAction(models.Model):
    role = models.CharField(max_length=50, default="")  # BUSINESS_ROLE
    access_page = models.ForeignKey(RoleApp, on_delete=models.PROTECT, to_field="app_name")
    can_edit = models.BooleanField(default=False)


# Create your models here.
class RoleAssignment(TimeStampedModel):
    """One business role in one approved data scope.

    A user may have any number of assignments. Blank Ownership and SAP Location
    mean the full Plant. A SAP Location is the narrowest supported scope.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    role = models.CharField(max_length=40)  # BUSINESS_ROLE
    plant = models.ForeignKey(
        Plant,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    department = models.CharField(max_length=63, blank=True)  # DEPARTMENTS
    sap_location = models.ForeignKey(
        SAPLocation,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="role_assignments",
    )
    count_methods = models.TextField(
        null=True,
        blank=True,
        help_text="Optional Count Method scope. Blank means every configured method.",
    )  # SAP_ENTRY_METHOD
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "plant", "department", "sap_location"],
                name="uq_role_assignment_scope",
                nulls_distinct=False,
            ),
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_from__isnull=True) | Q(valid_to__gte=models.F("valid_from")),
                name="ck_role_assignment_dates",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "plant", "is_active"],
                name="access_role_user_scope_idx",
            ),
            models.Index(
                fields=["role", "is_active"],
                name="access_role_role_active_idx",
            ),
        ]

    @property
    def plant_code(self):
        if self.plant:
            return self.plant.code
        else:
            return "All Plants"

    @property
    def role_ref(self):
        return RoleGroup.objects.filter(group_name=self.role).first()

    @property
    def scope_label(self):
        if self.role == "Global Admin":
            return "All Plants"
        labels = [self.plant_code]
        if self.department:
            labels.append(self.department)
        if self.sap_location_id:
            labels.append(self.sap_location.code)
        if len(labels) == 1:
            labels.append("All Ownership groups / SAP Locations")
        return " / ".join(labels)

    @property
    def app_list(self):
        return list(
            RoleAction.objects.filter(role=self.role).order_by("access_page__app_order").values_list("access_page_id", flat=True)
        )


class UserOnboardingBatch(TimeStampedModel):
    """Immutable upload preview followed by one atomic additive import."""

    plant = models.ForeignKey(
        Plant,
        on_delete=models.PROTECT,
        related_name="user_onboarding_batches",
    )
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16)
    row_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_row = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="confirmed_user_onboarding_batches",
    )


class CounterOnboardingRow(models.Model):
    batch = models.ForeignKey(
        UserOnboardingBatch,
        on_delete=models.CASCADE,
        related_name="rows",
    )
    row_number = models.PositiveIntegerField()
    employee_id = models.CharField(max_length=31, null=True)
    display_name = models.CharField(max_length=255, null=True)
    department = models.CharField(max_length=31)
    sap_location = models.ForeignKey(
        SAPLocation,
        on_delete=models.PROTECT,
        related_name="counter_onboard",
        null=True,
        blank=True,
    )
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)


class CounterRoster(ActiveModel):
    """Plant roster identity used for count attribution; it is not a login role."""

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="counter_roster")
    department = models.CharField(max_length=63, blank=True)
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, related_name="counter_roster", null=True, blank=True)
    employee_id = models.CharField(max_length=80)
    display_name = models.CharField(max_length=160)

    class Meta:
        ordering = ["plant_id", "display_name", "employee_id"]

    def __str__(self):
        return f"{self.display_name} ({self.employee_id})"
