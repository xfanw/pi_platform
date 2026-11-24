from django.db import models
from django.db.models import Q
from core.constants import PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS, QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS
from core.models import TimeStampedModel
from count.models import CountRecord
from cycles.app_models.cycle_models import PICycle
from cycles.app_models.inventory_models import PartMaster
from site_setting.models import SAPLocation
from django.contrib.auth.models import User

# Create your models here.


class AuditPlan(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.CASCADE, related_name="audit_plans")
    department = models.CharField(max_length=160)  # SAP Department
    name = models.CharField(max_length=160)
    auditors = models.PositiveIntegerField()
    pages_per_auditor = models.PositiveIntegerField()
    rows_per_page = models.PositiveIntegerField()
    target_count = models.PositiveIntegerField()
    value_pct = models.DecimalField(max_digits=5, decimal_places=2, default=85)
    map_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    variance_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5)
    status = models.CharField(max_length=24)  # Draft, In Process, Finalized, Submitted
    finalized_at = models.DateTimeField(null=True, blank=True)
    results_submitted_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cycle", "name"], name="uq_audit_plan_cycle_name"),
            models.CheckConstraint(
                condition=Q(auditors__gte=1, pages_per_auditor__gte=1),
                name="ck_audit_plan_positive_capacity",
            ),
        ]
        indexes = [models.Index(fields=["cycle", "status"], name="audit_plan_cycle_status_idx")]


class AuditCandidate(TimeStampedModel):
    plan = models.ForeignKey(AuditPlan, on_delete=models.CASCADE, related_name="candidates")
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.CASCADE, related_name="audit_candidates")
    part = models.ForeignKey(PartMaster, on_delete=models.CASCADE, related_name="audit_candidates")
    part_number_snapshot = models.CharField(max_length=80)
    description_snapshot = models.CharField(max_length=500, blank=True)
    book_value = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
    map_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
    variance_value = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
    abs_variance = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
    count_records = models.PositiveIntegerField()
    location_count = models.PositiveIntegerField(default=0)
    sub_location_count = models.PositiveIntegerField(default=0)
    tag_count = models.PositiveIntegerField(default=0)
    coverage_pct = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    in_top80 = models.BooleanField(default=False)
    selected_records = models.PositiveIntegerField(default=0)
    selection_reason = models.CharField(max_length=24, blank=True)  # Top 80% Value, High Value, High Abs Variance, Manual Select
    manual_override = models.SmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "sap_location", "part"],
                name="uq_audit_candidate_group",
            ),
            models.CheckConstraint(
                condition=Q(selected_records__lte=models.F("count_records")),
                name="ck_audit_candidate_selected_limit",
            ),
        ]
        indexes = [models.Index(fields=["plan", "selected_records"], name="audit_candidate_selected_idx")]


class AuditRecord(TimeStampedModel):
    plan = models.ForeignKey(AuditPlan, on_delete=models.CASCADE, related_name="records")
    candidate = models.ForeignKey(AuditCandidate, on_delete=models.CASCADE, related_name="records", null=True)
    source_count_record = models.ForeignKey(CountRecord, on_delete=models.CASCADE, related_name="audit_records")
    sap_location_code = models.CharField(max_length=16)
    physical_location_snapshot = models.CharField(max_length=160, blank=True)
    sub_location_snapshot = models.CharField(max_length=160, blank=True)
    tag_number_snapshot = models.CharField(max_length=80, blank=True)
    part_number_snapshot = models.CharField(max_length=80)
    count_quantity_snapshot = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)

    selected = models.BooleanField(default=False)

    page_number = models.IntegerField(default=0)
    auditor_number = models.IntegerField(default=0)
    result_status = models.CharField(max_length=31, default="Pending")  # Pending, Correct, Error, Unable / Not Counted
    audit_quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES, null=True, blank=True)
    error_type = models.CharField(max_length=24, null=True, blank=True)  # Wrong Quantity, Wrong Part Number, Other
    corrected_part = models.CharField(max_length=80)
    result_comment = models.CharField(max_length=500, blank=True)
    auditor_name = models.CharField(max_length=160, blank=True)
    completed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="completed_audit_records")
    completed_at = models.DateTimeField(null=True, blank=True)
    # count_correction = models.OneToOneField(
    #     CountCorrection, null=True, blank=True, on_delete=models.CASCADE, related_name="audit_record"
    # )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "source_count_record"],
                name="uq_audit_plan_source_record",
            )
        ]
        indexes = [
            models.Index(fields=["plan", "page_number"], name="audit_record_page_idx"),
            models.Index(fields=["plan", "result_status"], name="audit_record_status_idx"),
        ]
