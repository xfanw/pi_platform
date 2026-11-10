from django.db import models


class UserActionDateMemo(models.Model):
    action = models.CharField(max_length=50, null=True)
    user = models.CharField(max_length=255, null=True)
    date = models.DateTimeField(auto_now_add=True)
    memo = models.TextField(null=True)

    class Meta:
        abstract = True
