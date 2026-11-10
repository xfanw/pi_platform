# Worldwide IANA Time Zones mapped to their standard UTC offsets
from core.constants_long import *

# Price and Quantity field settings
QUANTITY_MAX_DIGITS = 22
QUANTITY_DECIMAL_PLACES = 4
PRICE_MAX_DIGITS = 22
PRICE_DECIMAL_PLACES = 6

# excel file size limit
MAX_FILE_BYTES = 5 * 1024 * 1024

# excel headers
COUNTER_HEADERS = ("Employee ID", "Display Name", "Ownership", "SAP Locations")
LOC_HEADERS = ("SAP Location", "Location")
SUB_LOC_HEADERS = ("SAP Location", "Location", "Sub Location")

TAG_HEADERS = ("SAP Location", "Location", "Sub Location", "Start", "End")
PART_HEADERS = ("PN", "Description", "MAPS$", "BU")
SAP_PART_HEADERS = ("PN", "SAP Location", "Qty")
EX_PART_HEADERS = ("PN", "SAP Location or ALL", "Reason")
