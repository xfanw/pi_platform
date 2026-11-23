from core.constants import QUANTITY_DECIMAL_PLACES, QUANTITY_MAX_DIGITS
from log.log_models.abstract_model import *


class CountLog(UserActionDateMemo):
    cycle_name = models.CharField(max_length=24, blank=True)
    plant_code = models.CharField(max_length=24, blank=True)
    part_number = models.CharField(max_length=24, blank=True)
    counter = models.CharField(max_length=255, blank=True)
    quantity = models.DecimalField(max_digits=QUANTITY_MAX_DIGITS, decimal_places=QUANTITY_DECIMAL_PLACES, null=True, blank=True)
