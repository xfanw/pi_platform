from io import BytesIO
from decimal import Decimal, InvalidOperation

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.db import transaction
from django.db.models import Count, Q

from core.app_functions import clean_errors
from core.constants import MAX_FILE_BYTES, COUNT_BATCH_HEADERS
from core.excel_file_handler._excel_helper_function import text_val


def count_excel_bytes(plant):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Count Upload"
    sheet.append(COUNT_BATCH_HEADERS)

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    widths = [20, 30, 30, 30, 20, 10, 30]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:G{sheet.max_row}"

    workbook.active = 0

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def count_batch_upload(curr_file, sheet_name, plant, note, cycle, actor):
    from count.models import CountLoadBatch, CycleTagDetail, TempCountLoadDetail
    from cycles.models import CyclePhysicalLocation, CycleSAPLocation, CycleSubLocation, CycleTagRange, PartMaster
    from site_setting.models import SAPLocation

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

    try:
        if sheet_name not in workbook.sheetnames:
            return "error", f"Sheet name {sheet_name} does NOT exist, please download the latest template. "

        rows = workbook[sheet_name].iter_rows(values_only=True)
        headers = tuple(text_val(value) for value in next(rows, ()))
        if headers != COUNT_BATCH_HEADERS:
            return "error", "Headers do NOT match, please download the latest template. "

        parts = {part.part_number: part for part in PartMaster.objects.filter(cycle=cycle)}
        sap_locations = {location.code: location for location in SAPLocation.objects.filter(plant=plant, is_active=True)}
        cycle_sap_locations = {
            location.sap_location_id: location
            for location in CycleSAPLocation.objects.filter(plant=plant, cycle=cycle, is_active=True)
        }
        physical_locations = {
            (location.physical_location.sap_location_id, location.physical_location.name): location.physical_location
            for location in CyclePhysicalLocation.objects.filter(plant=plant, cycle=cycle, is_active=True).select_related(
                "physical_location"
            )
        }
        sub_locations = {
            (location.sub_location.physical_location_id, location.sub_location.name): location.sub_location
            for location in CycleSubLocation.objects.filter(plant=plant, cycle=cycle, is_active=True).select_related("sub_location")
        }
        tag_ranges = {}
        for sap_location_id, physical_location_id, sub_location_id, start_number, end_number in CycleTagRange.objects.filter(
            plant=plant, cycle=cycle
        ).values_list("sap_location_id", "physical_location_id", "sub_location_id", "start_number", "end_number"):
            key = (sap_location_id, physical_location_id, sub_location_id)
            tag_ranges.setdefault(key, []).append((start_number, end_number))
        counted_tags = set(CycleTagDetail.objects.filter(tag_range__cycle=cycle, is_counted=True).values_list("tag_number", flat=True))

        details = []
        for line_number, row in enumerate(rows, start=2):
            row = tuple(row[: len(COUNT_BATCH_HEADERS)]) + (None,) * max(0, len(COUNT_BATCH_HEADERS) - len(row))
            if not any(value not in (None, "") for value in row):
                continue

            part_number, sap_code, location_name, sub_location_name, tag_number, quantity_value, counter_name = (
                text_val(value) for value in row
            )
            part_number = part_number.strip()
            sap_code = sap_code.strip()
            location_name = location_name.strip()
            sub_location_name = sub_location_name.strip()
            tag_number = tag_number.strip()
            counter_name = counter_name.strip() or actor.first_name

            part = parts.get(part_number)

            sap_location = sap_locations.get(sap_code)
            if not sap_location:
                return "error", f"Line {line_number}: SAP Location {sap_code or '(blank)'} is not in this plant."

            errors = []
            is_valid = True
            if not part_number or not sap_code or not location_name or not text_val(quantity_value):
                is_valid = False
                errors.append("PN, SAP Location, Location and Qty are required. ")

            if sap_location.id not in cycle_sap_locations:
                is_valid = False
                errors.append(f"SAP Location {sap_code} does not exist in this cycle. ")

            physical_location = physical_locations.get((sap_location.id, location_name))
            if not physical_location:
                is_valid = False
                errors.append(f"Location {location_name} does not exist in {sap_code}. ")

            sub_location = None
            if sub_location_name:
                if physical_location:
                    sub_location = sub_locations.get((physical_location.id, sub_location_name))
                if not sub_location:
                    is_valid = False
                    errors.append(f"Sub Location {sub_location_name} does not exist in {sap_code} > {location_name}. ")

            if tag_number:
                try:
                    tag_number_value = int(tag_number)
                except ValueError:
                    is_valid = False
                    errors.append("Tag Number must be a valid whole number. ")
                else:
                    location_key = (
                        sap_location.id,
                        physical_location.id if physical_location else None,
                        sub_location.id if sub_location else None,
                    )
                    ranges = tag_ranges.get(location_key, ())
                    if not any(start <= tag_number_value <= end for start, end in ranges):
                        is_valid = False
                        errors.append(
                            f"Tag Number {tag_number} is not defined in a tag range for the selected SAP Location, "
                            "Location and Sub Location. "
                        )
                    elif tag_number_value in counted_tags:
                        is_valid = False
                        errors.append(f"Tag Number {tag_number} has already been counted in this cycle. ")

            quantity = Decimal(0)
            if text_val(quantity_value):
                try:
                    quantity = Decimal(text_val(quantity_value))
                    if not quantity.is_finite() or quantity < 0:
                        quantity = Decimal(0)
                        is_valid = False
                        errors.append("Qty must be a number of 0 or more. ")
                except InvalidOperation:
                    is_valid = False
                    errors.append("Qty must be a number of 0 or more. ")
            details.append(
                TempCountLoadDetail(
                    cycle=cycle,
                    part=part,
                    raw_part_number="" if part else part_number,
                    sap_location=sap_location,
                    physical_location=physical_location,
                    sub_location=sub_location,
                    tag_number=tag_number,
                    quantity=quantity,
                    counter_name=counter_name,
                    validation_errors=errors,
                    is_valid=is_valid,
                    created_by=actor,
                    updated_by=actor,
                )
            )

        if not details:
            return "error", "File is empty."

        batch = CountLoadBatch.objects.create(
            cycle=cycle,
            source="Count Upload",
            source_filename=curr_file.name[:255],
            note=note,
            status="Preview",
            created_by=actor,
            updated_by=actor,
        )
        for detail in details:
            detail.batch = batch
        TempCountLoadDetail.objects.bulk_create(details)
    except Exception as e:
        return "error", f"Error batch onboarding, {clean_errors(e)}"
    finally:
        workbook.close()

    return "success", batch


def count_batch_validate(batch):
    from collections import Counter

    from count.models import TempCountLoadDetail

    details = list(TempCountLoadDetail.objects.filter(batch=batch))
    tag_counts = Counter(detail.tag_number for detail in details if detail.tag_number)
    changed = []
    duplicate_tag_error = "This tag number is duplicated in this file batch. "

    for detail in details:
        if detail.tag_number and tag_counts[detail.tag_number] > 1 and duplicate_tag_error not in detail.validation_errors:
            detail.is_valid = False
            detail.validation_errors.append(duplicate_tag_error)
            changed.append(detail)

    if changed:
        TempCountLoadDetail.objects.bulk_update(changed, ["is_valid", "validation_errors"])

    status = TempCountLoadDetail.objects.filter(batch=batch).aggregate(
        row_count=Count("id"),
        ready_count=Count("id", filter=Q(is_valid=True)),
        error_count=Count("id", filter=Q(is_valid=False)),
        part_count=Count("id", filter=Q(part__isnull=False)),
        ex_part_count=Count("id", filter=Q(part__isnull=True)),
    )

    error_count = status.get("error_count", 0)
    batch.row_count = status.get("row_count", 0)
    batch.ready_count = status.get("ready_count", 0)
    batch.part_count = status.get("part_count", 0)
    batch.ex_part_count = status.get("ex_part_count", 0)
    batch.error_count = error_count
    batch.status = "Error" if error_count > 0 else "Preview"
    batch.save()

    return ""
