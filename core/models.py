from django.db import models
from django.contrib.auth.models import User


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class ActiveModel(TimeStampedModel):
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Module(ActiveModel):
    module_name = models.CharField(max_length=100)
    module_sequence = models.IntegerField(default=1)
    display = models.BooleanField(default=True)


class Application(ActiveModel):
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    app_name = models.CharField(max_length=100, unique=True)
    app_sequence = models.IntegerField(default=1)
    app_url = models.CharField(null=True, blank=True, max_length=200)
    display = models.BooleanField(default=True)
    disable_auth = models.BooleanField(default=False)
    display_name = models.CharField(max_length=127, default="")
