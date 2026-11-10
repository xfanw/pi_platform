from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.db.models import Q
from django.db.models.aggregates import Count
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.db import transaction

from core.app_functions import clean_errors
from core.constants import MAX_FILE_BYTES, SAP_PART_HEADERS
from core.excel_file_handler._excel_helper_function import text_val

MAX_REPORTED_ERRORS = 10


def sap_part_excel_bytes(plant):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "SAP Inventory"
    sheet.append(SAP_PART_HEADERS)

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    for index, width in enumerate([20, 20, 15], start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:C{sheet.max_row}"

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def sap_part_batch_upload(curr_file, sheet_name, plant, cycle, actor):
    from cycles.models import PartMaster, TempSAPPartDetail, TempSAPPartMain
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
        headers = tuple(text_val(value) for value in next(rows, ()))[: len(SAP_PART_HEADERS)]
        if headers != SAP_PART_HEADERS:
            return "error", "Headers do NOT match, please download the latest template."

        parts = {part.part_number: part for part in PartMaster.objects.filter(cycle=cycle)}
        locations = {loc.code: loc for loc in SAPLocation.objects.filter(plant=plant)}

        curr_valid = True
        seen = set()
        records = []
        for line_no, row in enumerate(rows, start=2):
            row = tuple(row) + (None,) * (3 - len(row))
            if not any(value not in (None, "") for value in row[:3]):
                continue
            part_number = text_val(row[0])
            location_code = text_val(row[1])
            line_errors = []

            part = parts.get(part_number)
            location = locations.get(location_code)
            if not part_number or not location_code or text_val(row[2]) == "":
                curr_valid = False
                line_errors.append("PN, SAP Location and Qty are required")
            else:
                if not part:
                    curr_valid = False
                    line_errors.append(f"PN {part_number} is not in the current PN List")
                if not location:
                    curr_valid = False
                    line_errors.append(f"SAP Location {location_code} is not in this plant")

            quantity = Decimal(0)
            if text_val(row[2]) != "":
                try:
                    quantity = Decimal(text_val(row[2]))
                    if not quantity.is_finite() or quantity < 0:
                        quantity = Decimal(0)
                        curr_valid = False
                        line_errors.append("Qty must be a number of 0 or more")
                except InvalidOperation:
                    curr_valid = False
                    line_errors.append("Qty must be a number of 0 or more")

            key = (part_number, location_code)
            if part and location:
                if key in seen:
                    curr_valid = False
                    line_errors.append("Duplicated PN and SAP Location in this file")
                seen.add(key)
            records.append((part, location, quantity, line_errors, curr_valid))

        batch = TempSAPPartMain.objects.create(
            cycle=cycle,
            source_filename=curr_file.name[:255],
            status="Preview",
            row_count=len(records),
            ready_count=len(records),
            error_count=0,
            created_by=actor,
            updated_by=actor,
        )
        TempSAPPartDetail.objects.bulk_create(
            [
                TempSAPPartDetail(
                    batch=batch,
                    cycle=cycle,
                    part=part,
                    sap_location=location,
                    quantity=quantity,
                    validation_errors=validation_errors,
                    is_valid=is_valid,
                    created_by=actor,
                    updated_by=actor,
                )
                for part, location, quantity, validation_errors, is_valid in records
            ]
        )
    except Exception as e:
        return "error", f"Error batch onboarding, {clean_errors(e)}"
    finally:
        workbook.close()

    return "success", batch


def sap_part_batch_validate(batch):

    from cycles.models import TempSAPPartDetail

    status = TempSAPPartDetail.objects.filter(batch=batch).aggregate(
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
