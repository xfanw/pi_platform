from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.db import transaction

from core.app_functions import clean_errors
from core.constants import MAX_FILE_BYTES, TAG_HEADERS
from core.excel_file_handler._excel_helper_function import text_val

from cycles.models import CyclePhysicalLocation, CycleSAPLocation, CycleSubLocation


def tag_range_excel_bytes(plant, cycle):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tag Ranges"
    sheet.append(TAG_HEADERS)

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    widths = [20, 30, 30, 30, 30]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:E{sheet.max_row}"

    sub_locations = CycleSubLocation.objects.filter(plant=plant, is_active=True, cycle=cycle).values_list(
        "sub_location__name", "sub_location__physical_location__name", "sub_location__physical_location__sap_location__code"
    )

    workbook.active = 0

    for sub_loc, phys_loc, sap_loc in sub_locations:
        sheet.append([sap_loc, phys_loc, sub_loc, "", ""])

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def tag_batch_upload(curr_file, sheet_name, plant, cycle, actor):
    from cycles.models import TempCycleTagMain, TempCycleTagDetail

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

    tag_list = []

    if not sheet_name in workbook.sheetnames:
        workbook.close()
        return "error", f"Sheet name {sheet_name} does NOT exist, please download the latest template. "

    sheet = workbook[sheet_name]
    try:
        batch = TempCycleTagMain.objects.create(
            plant=plant,
            cycle=cycle,
            source_filename=curr_file.name[:255],
            created_by=actor,
            updated_by=actor,
        )
        rows = sheet.iter_rows(values_only=True)
        headers = tuple(text_val(value) for value in next(rows))
        if not headers == TAG_HEADERS:
            workbook.close()
            return "error", f"Headers do NOT match, please download the latest template. "

        # Load active cycle locations once instead of querying per row
        sap_map = {}
        for item in CycleSAPLocation.objects.filter(plant=plant, cycle=cycle, is_active=True).select_related("sap_location"):
            sap_map.setdefault(item.sap_location.code, item)
        loc_map = {}
        for item in CyclePhysicalLocation.objects.filter(plant=plant, cycle=cycle, is_active=True).select_related("physical_location"):
            loc_map.setdefault((item.physical_location.sap_location_id, item.physical_location.name), item)
        sub_loc_map = {}
        for item in CycleSubLocation.objects.filter(plant=plant, cycle=cycle, is_active=True).select_related("sub_location"):
            sub_loc_map.setdefault((item.sub_location.physical_location_id, item.sub_location.name), item)

        row_index = 1
        for row in rows:
            row_index += 1
            if row[0] or row[1] or row[2] or row[3] or row[4]:
                curr_error = []
                curr_valid = True
                curr_sap_code = text_val(row[0]).strip() if row[0] else ""
                curr_loc = text_val(row[1]).strip() if row[1] else ""
                curr_sub_loc = text_val(row[2]).strip() if row[2] else ""
                curr_start = text_val(row[3]).strip() if row[3] else ""
                curr_end = text_val(row[4]).strip() if row[4] else ""
                if not curr_sap_code or not curr_loc or not curr_sub_loc or not curr_start or not curr_end:
                    curr_valid = False
                    curr_error.append("All Fields are required. This line has empty fields. ")
                curr_sap_ref = sap_map.get(curr_sap_code)
                curr_loc_ref = loc_map.get((curr_sap_ref.sap_location_id, curr_loc)) if curr_sap_ref else None
                curr_sub_loc_ref = sub_loc_map.get((curr_loc_ref.physical_location_id, curr_sub_loc)) if curr_loc_ref else None
                if not curr_sap_ref:
                    curr_valid = False
                    curr_error.append(f"SAP Location {curr_sap_code} does not exist in this cycle. ")
                if not curr_loc_ref:
                    curr_valid = False
                    curr_error.append(f"Location {curr_loc} does not exist in this cycle. ")
                if not curr_sub_loc_ref:
                    curr_valid = False
                    curr_error.append(f"Sub Location {curr_sub_loc} does not exist in this cycle. ")
                if not curr_start.isdigit() or not curr_end.isdigit():
                    curr_valid = False
                    curr_start = 0
                    curr_end = 0
                    curr_error.append(f"Start and End must be valid numbers. ")
                if int(curr_start) > int(curr_end):
                    curr_valid = False
                    curr_error.append(f"Start number cannot be greater than End number. ")

                tag_list.append(
                    TempCycleTagDetail(
                        cycle=cycle,
                        plant=plant,
                        sap_location=curr_sap_ref.sap_location if curr_sap_ref else None,
                        physical_location=curr_loc_ref.physical_location if curr_loc_ref else None,
                        sub_location=curr_sub_loc_ref.sub_location if curr_sub_loc_ref else None,
                        start_number=curr_start if curr_start else 0,
                        end_number=curr_end if curr_end else 0,
                        validation_errors=curr_error,
                        is_valid=curr_valid,
                        batch=batch,
                        created_by=actor,
                        updated_by=actor,
                    )
                )

        TempCycleTagDetail.objects.bulk_create(tag_list)
    except Exception as e:
        workbook.close()
        return "error", f"Error batch onboarding, {clean_errors(e)}"

    workbook.close()
    return "success", batch


def tag_batch_validate(batch):
    from bisect import bisect_right

    from cycles.models import TempCycleTagDetail, CycleTagRange

    all_tags = list(TempCycleTagDetail.objects.filter(batch=batch))
    checked = sorted((t for t in all_tags if t.start_number != 0 and t.end_number != 0), key=lambda t: t.start_number)

    # Merge existing ranges once so each tag needs only a binary search
    merged = []
    for s, e in CycleTagRange.objects.order_by("start_number").values_list("start_number", "end_number"):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    merged_starts = [s for s, _ in merged]

    changed = []
    prefix_max_end = None
    for index, tag in enumerate(checked):
        start, end = tag.start_number, tag.end_number
        new_error = False

        pos = bisect_right(merged_starts, end) - 1
        if pos >= 0 and merged[pos][1] >= start:
            new_error = True
            tag.is_valid = False
            tag.validation_errors.append("This range overlaps with existing ranges. ")

        overlaps_previous = prefix_max_end is not None and prefix_max_end >= start
        overlaps_next = index + 1 < len(checked) and checked[index + 1].start_number <= end
        if overlaps_previous or overlaps_next:
            new_error = True
            tag.is_valid = False
            tag.validation_errors.append("This range overlaps with other ranges in the batch. ")

        prefix_max_end = end if prefix_max_end is None else max(prefix_max_end, end)
        if new_error:
            changed.append(tag)

    if changed:
        TempCycleTagDetail.objects.bulk_update(changed, ["is_valid", "validation_errors"])

    error_count = sum(1 for t in all_tags if not t.is_valid)
    batch.row_count = len(all_tags)
    batch.ready_count = len(all_tags) - error_count
    batch.error_count = error_count
    batch.status = "Error" if error_count > 0 else "Preview"
    batch.save()

    return ""
