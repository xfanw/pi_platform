from django.db import models
from django.db.models import Q


from core.constants import QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS
from core.models import TimeStampedModel
from cycles.models import PartMaster, PICycle, CycleTagRange
from site_setting.models import PhysicalLocation, SAPLocation, SubLocation
from django.contrib.auth.models import User

# class CorrectionStatus(models.TextChoices):
#     SUBMITTED = "SUBMITTED", "Submitted"
#     APPROVED = "APPROVED", "Approved"
#     APPLIED = "APPLIED", "Applied"
#     REJECTED = "REJECTED", "Rejected"


class CountLoadBatch(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="count_batches")
    source = models.CharField(max_length=16)
    source_filename = models.CharField(max_length=255, blank=True)
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16)
    row_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    part_count = models.PositiveIntegerField(default=0)
    ex_part_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(
                fields=["cycle", "created_at"],
                name="counting_co_cycle_i_19fc36_idx",
            )
        ]


class TempCountLoadDetail(TimeStampedModel):
    batch = models.ForeignKey(CountLoadBatch, null=True, blank=True, on_delete=models.CASCADE)
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT)
    raw_part_number = models.CharField(max_length=80)
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT)
    physical_location = models.ForeignKey(PhysicalLocation, null=True, blank=True, on_delete=models.PROTECT)
    sub_location = models.ForeignKey(SubLocation, null=True, blank=True, on_delete=models.PROTECT)
    tag_number = models.CharField(max_length=80, blank=True)
    quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)
    counter_name = models.CharField(max_length=160, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)


class CountRecord(models.Model):
    # idempotency_key = models.CharField(max_length=128, unique=True)  # ?
    # request_fingerprint = models.CharField(max_length=64)  # ?
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT, related_name="count_records")
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="count_records")
    batch = models.ForeignKey(CountLoadBatch, null=True, blank=True, on_delete=models.SET_NULL)
    source = models.CharField(max_length=16)
    source_record_key = models.CharField(max_length=160, blank=True)
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, related_name="count_records")
    physical_location = models.ForeignKey(PhysicalLocation, null=True, blank=True, on_delete=models.PROTECT)
    sub_location = models.ForeignKey(SubLocation, null=True, blank=True, on_delete=models.PROTECT)
    tag_number = models.CharField(max_length=80, blank=True)
    quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)
    counter_name = models.CharField(max_length=160, blank=True)
    # counter_employee_id = models.CharField(max_length=80, blank=True)
    entered_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="entered_count_records")
    entered_at = models.DateTimeField(null=True)
    accepted_at = models.DateTimeField(null=True)
    accepted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="accepted_count_records")
    editable = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cycle", "source", "source_record_key"],
                condition=~Q(source_record_key=""),
                name="uq_count_source_record_key",
            )
        ]
        indexes = [
            models.Index(
                fields=["cycle", "sap_location", "part"],
                name="counting_co_cycle_i_fabe25_idx",
            ),
            models.Index(
                fields=["cycle", "tag_number"],
                name="counting_co_cycle_i_b353ca_idx",
            ),
        ]


class CountIntakeException(TimeStampedModel):
    # exception_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # idempotency_key = models.CharField(max_length=128, unique=True)
    # request_fingerprint = models.CharField(max_length=64)
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="count_exceptions")
    batch = models.ForeignKey(CountLoadBatch, null=True, blank=True, on_delete=models.PROTECT, related_name="exceptions")
    source = models.CharField(max_length=16)  # COUNT_SOURCE
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, related_name="count_exceptions")
    physical_location = models.ForeignKey(
        PhysicalLocation, null=True, blank=True, on_delete=models.PROTECT, related_name="count_exceptions"
    )
    sub_location = models.ForeignKey(SubLocation, null=True, blank=True, on_delete=models.PROTECT, related_name="count_exceptions")
    tag_number = models.CharField(max_length=80, blank=True)
    raw_part_number = models.CharField(max_length=80)
    quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)
    counter_name = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=24, blank=True, null=True)
    disposition_part = models.ForeignKey(
        PartMaster, null=True, blank=True, on_delete=models.PROTECT, related_name="mapped_count_exceptions"
    )
    disposition_reason = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_count_exceptions")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(
                fields=["cycle", "status"],
                name="counting_co_cycle_i_26737a_idx",
            ),
            models.Index(
                fields=["cycle", "raw_part_number"],
                name="counting_co_cycle_i_1cf034_idx",
            ),
        ]


class CycleTagDetail(TimeStampedModel):
    tag_range = models.ForeignKey(CycleTagRange, on_delete=models.CASCADE, related_name="tag_details")
    tag_number = models.BigIntegerField(unique=True)
    count_record = models.ForeignKey(CountRecord, on_delete=models.PROTECT, related_name="tag_details", null=True, blank=True)
    exception_record = models.ForeignKey(
        CountIntakeException, null=True, blank=True, on_delete=models.SET_NULL, related_name="tag_details"
    )
    is_counted = models.BooleanField(default=False)

    @property
    def part_number(self):
        if self.count_record:
            return self.count_record.part.part_number
        elif self.exception_record:
            return self.exception_record.raw_part_number
        return None

    @property
    def quantity(self):
        if self.count_record:
            return self.count_record.quantity
        elif self.exception_record:
            return self.exception_record.quantity
        return None

    @property
    def counter_name(self):
        if self.count_record:
            return self.count_record.counter_name
        elif self.exception_record:
            return self.exception_record.counter_name
        return None

    @property
    def pending_review(self):
        if not self.count_record and self.exception_record:
            return True
        return False


class CountCorrection(TimeStampedModel):
    # correction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    count_record = models.ForeignKey(CountRecord, on_delete=models.PROTECT, related_name="corrections")
    corrected_part = models.ForeignKey(PartMaster, null=True, blank=True, on_delete=models.PROTECT, related_name="count_corrections")
    corrected_quantity = models.DecimalField(
        max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES, null=True, blank=True
    )
    reason_code = models.CharField(max_length=80)
    comment = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16)  # COUNT_EXCEPTION_STATUS
    submitted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="submitted_count_corrections")
    submitted_at = models.DateTimeField()
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="reviewed_count_corrections")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.CharField(max_length=500, blank=True)
    applied_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="applied_count_corrections")
    effective_at = models.DateTimeField(null=True, blank=True)
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(
                fields=["count_record", "effective_at"],
                name="counting_co_count_r_556488_idx",
            ),
            models.Index(
                fields=["status", "submitted_at"],
                name="count_corr_status_time_idx",
            ),
        ]
