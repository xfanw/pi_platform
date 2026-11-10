from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.db import transaction
from django.db.models import Count, Q

from core.app_functions import clean_errors
from core.constants import MAX_FILE_BYTES, PART_HEADERS
from core.excel_file_handler._excel_helper_function import text_val


def part_excel_bytes(plant):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "PN List"
    sheet.append(PART_HEADERS)

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    widths = [20, 50, 20, 30]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:D{sheet.max_row}"

    workbook.active = 0

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def part_batch_upload(curr_file, sheet_name, plant, cycle, actor):
    from cycles.models import TempPartMain, TempPartDetail, PartMaster

    if not curr_file:
        return "error", "Choose a completed .xlsx file."
    if not curr_file.name.lower().endswith(".xlsx"):
        return "error", "The onboarding file must be an .xlsx workbook."
    if getattr(curr_file, "size", 0) > MAX_FILE_BYTES:
        return "error", "The onboarding workbook cannot exceed 5 MB."
    try:
        workbook = load_workbook(curr_file, read_only=True, data_only=True)
    except Exception as e:
        return "error", f"The uploaded workbook could not be read. {clean_errors(e)}"

    part_list = []

    if not sheet_name in workbook.sheetnames:
        workbook.close()
        return "error", f"Sheet name {sheet_name} does NOT exist, please download the latest template. "

    sheet = workbook[sheet_name]
    try:
        batch = TempPartMain.objects.create(
            cycle=cycle,
            source_filename=curr_file.name[:255],
            created_by=actor,
            updated_by=actor,
        )
        rows = sheet.iter_rows(values_only=True)
        headers = tuple(text_val(value) for value in next(rows))
        if not headers == PART_HEADERS:
            workbook.close()
            return "error", f"Headers do NOT match, please download the latest template. "

        for row in rows:
            if row[0] or row[1] or row[2] or row[3]:
                curr_error = []
                curr_valid = True
                curr_part_number = text_val(row[0]).strip() if row[0] else ""
                curr_desc = text_val(row[1]).strip() if row[1] else ""
                curr_price = row[2] if row[2] else 0
                curr_bu = text_val(row[3]).strip() if row[3] else ""
                if not curr_part_number or not curr_price or not curr_bu:
                    curr_valid = False
                    curr_error.append("PN, MAP$, BU are required. This line has empty fields. ")

                try:
                    curr_price = float(curr_price)
                except ValueError:
                    curr_price = 0
                    curr_valid = False
                    curr_error.append("MAP$ must be a valid number. ")

                part_list.append(
                    TempPartDetail(
                        cycle=cycle,
                        part_number=curr_part_number,
                        description=curr_desc,
                        business_unit=curr_bu,
                        price=curr_price,
                        validation_errors=curr_error,
                        is_valid=curr_valid,
                        batch=batch,
                        created_by=actor,
                        updated_by=actor,
                    )
                )

        TempPartDetail.objects.bulk_create(part_list)
    except Exception as e:
        workbook.close()
        return "error", f"Error batch onboarding, {clean_errors(e)}"

    workbook.close()
    return "success", batch


def part_batch_validate(batch):
    from cycles.models import TempPartDetail

    part_set = TempPartDetail.objects.filter(batch=batch)
    for part in part_set:
        new_error = False

        duplicated_parts = part_set.exclude(pk=part.pk).filter(part_number=part.part_number)

        if duplicated_parts.exists():
            new_error = True
            part.is_valid = False
            part.validation_errors.append("This part number is duplicated in this file batch. ")
        if new_error:
            part.save()

    status = TempPartDetail.objects.filter(batch=batch).aggregate(
        row_count=Count("id"),
        ready_count=Count("id", filter=Q(is_valid=True)),
        error_count=Count("id", filter=Q(is_valid=False)),
    )

    error_count = status.get("error_count", 0)
    batch.row_count = status.get("row_count", 0)
    batch.ready_count = status.get("ready_count", 0)
    batch.error_count = error_count
    batch.status = "Error" if error_count > 0 else "Preview"
    batch.save()

    return ""
