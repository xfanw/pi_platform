from django.db import models

from core.models import ActiveModel, TimeStampedModel
from django.contrib.auth.models import User


# Create your models here.
class Plant(ActiveModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=160)
    site = models.CharField(max_length=80, default="FII USA")
    customer = models.CharField(max_length=160, blank=True)
    timezone = models.CharField(max_length=64, default="America/Chicago")
    variance_summary_default = models.CharField(max_length=24, default="SAP_LOCATION")  # PLANT_VAR_SUM_DEFAULT

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class SAPLocation(ActiveModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="sap_locations")
    department = models.CharField(max_length=63, blank=True)
    code = models.CharField(max_length=16)
    address = models.CharField(max_length=255, blank=True)
    inventory_type = models.CharField(max_length=15)  # SAP_INVENTORY_TYPE
    default_entry_method = models.CharField(max_length=16)  # SAP_ENTRY_METHOD
    allowed_entry_methods = models.CharField(max_length=255, blank=True)  # SAP_ENTRY_METHOD

    @property
    def configured_entry_methods(self):
        return eval(self.allowed_entry_methods)

    @property
    def total_location_count(self):
        return self.physical_locations.count()

    @property
    def active_location_count(self):
        return self.physical_locations.filter(is_active=True).count()

    @property
    def total_sub_location_count(self):
        return sum(location.total_sub_location_count for location in self.physical_locations.all())

    @property
    def active_sub_location_count(self):
        return sum(location.active_sub_location_count for location in self.physical_locations.all())

    # def supports_entry_method(self, method):
    #     return method in self.configured_entry_methods()

    # def count_methods_display(self):
    #     labels = dict(EntryMethod.choices)
    #     return ", ".join(labels.get(method, method) for method in self.configured_entry_methods())

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plant", "code"],
                name="uq_sap_location_plant_code",
            )
        ]
        ordering = ["plant_id", "code"]

    def __str__(self):
        return f"{self.plant.code} / {self.code}"


class PhysicalLocation(ActiveModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="physical_locations")
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, related_name="physical_locations")
    name = models.CharField(max_length=160)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sap_location", "name"], name="uq_physical_location_scope")]
        ordering = ["sap_location_id", "name"]

    def __str__(self):
        return f"{self.sap_location.code} / {self.name}"

    @property
    def total_sub_location_count(self):
        return self.sub_locations.count()

    @property
    def active_sub_location_count(self):
        return self.sub_locations.filter(is_active=True).count()


class SubLocation(ActiveModel):
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="sub_locations")
    physical_location = models.ForeignKey(PhysicalLocation, on_delete=models.PROTECT, related_name="sub_locations")
    name = models.CharField(max_length=160)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["physical_location", "name"], name="uq_sub_location_scope")]
        ordering = ["physical_location_id", "name"]

    def __str__(self):
        return f"{self.physical_location} / {self.name}"


class BusinessOption(ActiveModel):
    """Plant-owned workflow vocabulary whose recorded history stays immutable."""

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT, related_name="business_options")
    category = models.CharField(max_length=40)  # BUSINESS_OPTION_CATEGORY
    value = models.CharField(max_length=120)
    sort_order = models.PositiveIntegerField(default=0)
    is_protected = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plant", "category", "value"],
                name="uq_business_option_plant_category_value",
            )
        ]
        ordering = ["plant_id", "category", "sort_order", "value"]

    def __str__(self):
        return f"{self.plant.code} / {self.get_category_display()} / {self.value}"


class SystemSetting(models.Model):
    var_name = models.CharField(max_length=127)
    var_status = models.BooleanField(default=False)
    var_text = models.TextField()
    updater = models.CharField(max_length=127)
    update_date = models.DateTimeField(auto_now=True)


class TempLocationMain(TimeStampedModel):
    """Immutable upload preview followed by one atomic additive import."""

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16)
    row_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_row = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)


class TempLocationDetail(models.Model):
    batch = models.ForeignKey(TempLocationMain, on_delete=models.CASCADE)
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    sap_location = models.ForeignKey(SAPLocation, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=160)
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)


class TempSubLocationMain(TimeStampedModel):
    """Immutable upload preview followed by one atomic additive import."""

    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    source_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=16)
    row_count = models.PositiveIntegerField(default=0)
    ready_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    skipped_row = models.PositiveIntegerField(default=0)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT)


class TempSubLocationDetail(models.Model):
    batch = models.ForeignKey(TempSubLocationMain, on_delete=models.CASCADE)
    plant = models.ForeignKey(Plant, on_delete=models.PROTECT)
    physical_location = models.ForeignKey(PhysicalLocation, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=160)
    validation_errors = models.JSONField(default=list, blank=True)
    is_valid = models.BooleanField(default=False)
