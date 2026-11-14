from django.db import models

from core.models import TimeStampedModel
from django.contrib.auth.models import User

from cycles.app_models.cycle_models import PICycle
from site_setting.models import PhysicalLocation, Plant, SAPLocation, SubLocation


class CycleTagRange(TimeStampedModel):
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="tag_ranges")
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="tag_ranges")
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, related_name="tag_ranges")
    physical_location = models.ForeignKey(PhysicalLocation, on_delete=models.PROTECT, related_name="tag_ranges")
    sub_location = models.ForeignKey(SubLocation, on_delete=models.PROTECT, related_name="tag_ranges")
    prefix = models.CharField(max_length=24, blank=True)
    start_number = models.BigIntegerField()
    end_number = models.BigIntegerField()
    tag_count = models.BigIntegerField(default=0)

    @property
    def used_count(self):
        return 0


class TempCycleTagMain(TimeStampedModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
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


class TempCycleTagDetail(TimeStampedModel):
    batch = models.ForeignKey(TempCycleTagMain, on_delete=models.PROTECT)
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT)
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, null=True, blank=True)
    physical_location = models.ForeignKey(PhysicalLocation, on_delete=models.PROTECT, null=True, blank=True)
    sub_location = models.ForeignKey(SubLocation, on_delete=models.PROTECT, null=True, blank=True)
    prefix = models.CharField(max_length=24, blank=True)
    start_number = models.BigIntegerField()
    end_number = models.BigIntegerField()
    tag_count = models.BigIntegerField(default=0)
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)
