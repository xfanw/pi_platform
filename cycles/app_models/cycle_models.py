from django.db import models

from core.models import ActiveModel, TimeStampedModel
from django.contrib.auth.models import User

from site_setting.models import PhysicalLocation, Plant, SAPLocation, SubLocation


# Create your models here.
class PICycle(TimeStampedModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="pi_cycles")
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=12)
    opened_at = models.DateTimeField(null=True, blank=True)
    opened_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pi_cycles_opened",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pi_cycles_closed",
    )
    row_version = models.PositiveBigIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["plant", "name"], name="uq_cycle_plant_name"),
        ]

    def __str__(self):
        return f"{self.plant.code} / {self.name}"


class CycleSAPLocation(ActiveModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="sap_location_scope")
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="sap_location_scope")
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, related_name="cycle_scope")

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.cycle.plant.code} / {self.cycle.name} / " f"{self.sap_location.code} ({status})"


class CyclePhysicalLocation(ActiveModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="physical_location_scope")
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="physical_location_scope")
    physical_location = models.ForeignKey(PhysicalLocation, on_delete=models.PROTECT, related_name="cycle_scope")


class CycleSubLocation(ActiveModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="sub_location_scope")
    cycle = models.ForeignKey(PICycle, on_delete=models.PROTECT, related_name="sub_location_scope")
    sub_location = models.ForeignKey(SubLocation, on_delete=models.PROTECT, related_name="cycle_scope")
