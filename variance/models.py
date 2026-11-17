from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from core.constants import PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS, QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS
from cycles.app_models.cycle_models import PICycle
from cycles.app_models.inventory_models import PartMaster
from site_setting.models import Plant, SAPLocation


class CycleVariance(models.Model):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="cycle_variances")
    cycle = models.ForeignKey(PICycle, on_delete=models.CASCADE, related_name="cycle_variances")
    part = models.ForeignKey(PartMaster, on_delete=models.CASCADE, related_name="cycle_variances")
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.CASCADE, related_name="cycle_variances")
    sap_quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)
    count_quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)
    variance_quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)
    map_price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
    variance_value = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)

    class Meta:
        indexes = [
            models.Index(fields=["cycle", "plant"], name="cycle_variance_cycle_plant_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["cycle", "sap_location", "part"], name="uq_variance_cycle_sap_location_part_grain")
        ]


# class VarianceResolutionStatus(models.TextChoices):
#     NEEDS_REVIEW = "NEEDS_REVIEW", "Needs Review"
#     TO_POST = "TO_POST", "To Post"
#     NOT_POST = "NOT_POST", "Not Post"
#     POSTED = "POSTED", "Posted"
#     CLOSED_RESOLVED = "CLOSED_RESOLVED", "Closed - Resolved"


class VarianceResolution(TimeStampedModel):
    variance = models.ForeignKey(CycleVariance, on_delete=models.CASCADE, related_name="resolutions")
    status = models.CharField(max_length=24, default="Needs Review")
    reason = models.CharField(max_length=240, blank=True)
    sap_document_number = models.CharField(max_length=80, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="variance_resolutions_decided"
    )
    row_version = models.PositiveBigIntegerField(default=1)


class VarianceComment(models.Model):
    variance = models.ForeignKey(CycleVariance, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="variance_comments")


# class VarianceResolutionLog(models.Model):
#     log_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     resolution = models.ForeignKey(VarianceResolution, on_delete=models.CASCADE, related_name="status_history")
#     from_status = models.CharField(max_length=24, blank=True)
#     to_status = models.CharField(max_length=24, choices=VarianceResolutionStatus.choices)
#     note = models.CharField(max_length=500, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     created_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="variance_resolution_logs",
#     )

#     class Meta:
#         ordering = ["created_at"]


# class PostBatchStatus(models.TextChoices):
#     DRAFT = "DRAFT", "Draft"
#     POSTED = "POSTED", "Posted"
#     CANCELLED = "CANCELLED", "Cancelled"


# class PostBatch(TimeStampedModel):
#     batch_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     cycle = models.ForeignKey(PICycle, on_delete=models.CASCADE, related_name="post_batches")
#     name = models.CharField(max_length=160)
#     status = models.CharField(max_length=12, choices=PostBatchStatus.choices, default=PostBatchStatus.DRAFT)
#     note = models.CharField(max_length=500, blank=True)
#     sap_document_number = models.CharField(max_length=80, blank=True)
#     posting_date = models.DateField(null=True, blank=True)
#     confirmed_at = models.DateTimeField(null=True, blank=True)
#     confirmed_by = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         null=True,
#         blank=True,
#         on_delete=models.CASCADE,
#         related_name="post_batches_confirmed",
#     )
#     row_version = models.PositiveBigIntegerField(default=1)

#     class Meta:
#         constraints = [models.UniqueConstraint(fields=["cycle", "name"], name="uq_post_batch_cycle_name")]
#         ordering = ["-created_at"]


# class PostBatchLine(models.Model):
#     line_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     batch = models.ForeignKey(PostBatch, on_delete=models.CASCADE, related_name="lines")
#     resolution = models.ForeignKey(VarianceResolution, on_delete=models.CASCADE, related_name="post_batch_lines")
#     part_number_snapshot = models.CharField(max_length=80)
#     sap_location_code_snapshot = models.CharField(max_length=16)
#     inventory_type_snapshot = models.CharField(max_length=2)
#     moving_average_price_snapshot = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
#     variance_quantity_snapshot = models.DecimalField(max_digits=22, decimal_places=4)
#     variance_value_snapshot = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
#     movement_type = models.CharField(max_length=3)
#     is_included = models.BooleanField(default=True)
#     exclusion_note = models.CharField(max_length=240, blank=True)

#     class Meta:
#         constraints = [models.UniqueConstraint(fields=["batch", "resolution"], name="uq_post_batch_line")]
#         ordering = ["sap_location_code_snapshot", "part_number_snapshot"]
