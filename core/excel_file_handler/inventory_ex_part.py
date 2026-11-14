from io import BytesIO

from django.db.models import Q
from django.db.models.aggregates import Count
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.db import transaction

from core.app_functions import clean_errors
from core.constants import EX_PART_HEADERS, MAX_FILE_BYTES
from core.excel_file_handler._excel_helper_function import text_val

MAX_REPORTED_ERRORS = 10
REASON_MAX_LENGTH = 240
ALL_LOCATIONS = "ALL"


def ex_part_excel_bytes(plant):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Exclude PN"
    sheet.append(EX_PART_HEADERS)

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    for index, width in enumerate([20, 25, 50], start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:C{sheet.max_row}"

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def ex_part_batch_upload(curr_file, sheet_name, plant, cycle, actor):
    from cycles.models import PartMaster, TempExPartDetail, TempExPartMain
    from site_setting.models import SAPLocation

    if not curr_file:
        return "error", "Choose a completed .xlsx file."
    if not curr_file.name.lower().endswith(".xlsx"):
        return "error", "The file must be an .xlsx workbook."
    if getattr(curr_file, "size", 0) > MAX_FILE_BYTES:
        return "error", "The workbook cannot exceed 5 MB."
    try:
        workbook = load_workbook(curr_file, read_only=True, data_only=True)
    except Exception as e:
        return "error", f"The uploaded workbook could not be read. {clean_errors(e)}"

    if sheet_name not in workbook.sheetnames:
        workbook.close()
        return "error", f"Sheet name {sheet_name} does NOT exist, please download the latest template."

    try:
        rows = workbook[sheet_name].iter_rows(values_only=True)
        headers = tuple(text_val(value) for value in next(rows, ()))[: len(EX_PART_HEADERS)]
        if headers != EX_PART_HEADERS:
            return "error", "Headers do NOT match, please download the latest template."

        parts = {part.part_number: part for part in PartMaster.objects.filter(cycle=cycle)}
        locations = {loc.code: loc for loc in SAPLocation.objects.filter(plant=plant)}

        seen = set()
        records = []
        for line_no, row in enumerate(rows, start=2):
            curr_valid = True
            row = tuple(row) + (None,) * (3 - len(row))
            part_number, location_code, reason = (text_val(value) for value in row[:3])
            if not (part_number or location_code or reason):
                continue

            line_errors = []
            part = parts.get(part_number)
            is_all = location_code.upper() == ALL_LOCATIONS
            location = None if is_all else locations.get(location_code)

            if not part_number or not location_code or not reason:
                curr_valid = False
                line_errors.append("PN, SAP Location, and Reason are required")
            else:
                if not part:
                    curr_valid = False
                    line_errors.append(f"PN {part_number} is not in the current PN List")
                if not is_all and not location:
                    curr_valid = False
                    line_errors.append(f"SAP Location {location_code} is not in this plant")
                if len(reason) > REASON_MAX_LENGTH:
                    curr_valid = False
                    line_errors.append(f"Reason cannot exceed {REASON_MAX_LENGTH} characters")

            if not line_errors:
                key = (part.pk, location.pk if location else None)
                if key in seen:
                    curr_valid = False
                    line_errors.append("Duplicated PN and SAP Location in this file")
                seen.add(key)

            records.append((part, location, reason, curr_valid, line_errors))

        batch = TempExPartMain.objects.create(
            cycle=cycle,
            source_filename=curr_file.name[:255],
            status="Preview",
            row_count=len(records),
            ready_count=len(records),
            error_count=0,
            created_by=actor,
            updated_by=actor,
        )
        TempExPartDetail.objects.bulk_create(
            [
                TempExPartDetail(
                    batch=batch,
                    cycle=cycle,
                    part=part,
                    sap_location=location,
                    reason=reason,
                    is_valid=curr_valid,
                    validation_errors=line_errors,
                    created_by=actor,
                    updated_by=actor,
                )
                for part, location, reason, curr_valid, line_errors in records
            ]
        )
    except Exception as e:
        return "error", f"Error batch onboarding, {clean_errors(e)}"
    finally:
        workbook.close()

    return "success", batch


def ex_part_batch_validate(batch):

    from cycles.models import TempExPartDetail

    status = TempExPartDetail.objects.filter(batch=batch).aggregate(
        row_count=Count("id"),
        ready_count=Count("id", filter=Q(is_valid=True)),
        error_count=Count("id", filter=Q(is_valid=False)),
    )

    error_count = status["error_count"]
    batch.row_count = status["row_count"]
    batch.ready_count = status["ready_count"]
    batch.error_count = error_count
    batch.status = "Error" if error_count > 0 else "Preview"
    batch.save()

    return ""
