from django.db import models

from core.constants import PRICE_DECIMAL_PLACES, PRICE_MAX_DIGITS, QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS
from core.models import TimeStampedModel
from cycles.app_models.cycle_models import PICycle
from site_setting.models import SAPLocation
from django.contrib.auth.models import User


class PartMaster(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="parts")
    part_number = models.CharField(max_length=80)
    description = models.CharField(max_length=500, blank=True)
    business_unit = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cycle", "part_number"], name="uq_part_cycle_number")]
        indexes = [
            models.Index(
                fields=["cycle", "business_unit"],
                name="inventory_p_cycle_i_5ef560_idx",
            )
        ]
        ordering = ["part_number"]

    def __str__(self):
        return f"{self.cycle} / {self.part_number}"


class TempPartMain(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16)
    row_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_row = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)


class TempPartDetail(TimeStampedModel):
    batch = models.ForeignKey(TempPartMain, on_delete=models.PROTECT)
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    part_number = models.CharField(max_length=80)
    description = models.CharField(max_length=500, blank=True)
    business_unit = models.CharField(max_length=80, blank=True)
    price = models.DecimalField(max_digits=PRICE_MAX_DIGITS, decimal_places=PRICE_DECIMAL_PLACES, default=0)
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)


class BookInventoryLine(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="book_lines")
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, related_name="book_lines")
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT, related_name="book_lines")
    quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cycle", "sap_location", "part"],
                name="uq_book_cycle_sap_part",
            )
        ]
        indexes = [
            models.Index(
                fields=["cycle", "sap_location"],
                name="inventory_b_cycle_i_10ff54_idx",
            ),
            models.Index(
                fields=["cycle", "part"],
                name="inventory_b_cycle_i_98793a_idx",
            ),
        ]


class TempSAPPartMain(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16)
    row_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_row = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)


class TempSAPPartDetail(TimeStampedModel):
    batch = models.ForeignKey(TempSAPPartMain, on_delete=models.PROTECT)
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT, null=True, blank=True)
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES)
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)


class ExcludedPart(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="excluded_parts")
    sap_location = models.ForeignKey(SAPLocation, null=True, blank=True, on_delete=models.PROTECT, related_name="excluded_parts")
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT, related_name="exclusions")
    reason = models.CharField(max_length=240)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cycle", "sap_location", "part"],
                name="uq_excluded_part_scope",
                nulls_distinct=False,
            )
        ]


class TempExPartMain(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16)
    row_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_row = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)


class TempExPartDetail(TimeStampedModel):
    batch = models.ForeignKey(TempExPartMain, on_delete=models.PROTECT)
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    sap_location = models.ForeignKey(SAPLocation, null=True, blank=True, on_delete=models.PROTECT)
    part = models.ForeignKey(PartMaster, on_delete=models.PROTECT, null=True, blank=True)
    reason = models.CharField(max_length=240)
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)
