from collections import Counter
from io import BytesIO

from django.db.models.functions import Concat
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.db import transaction
from django.db.models import F, Value

from core.app_functions import clean_errors, swap_dict_key_value
from core.constants import MAX_FILE_BYTES, LOC_HEADERS, SUB_LOC_HEADERS
from core.excel_file_handler._excel_helper_function import gen_dv_dict, gen_dv_list, text_val

from site_setting.models import SAPLocation, PhysicalLocation, SAPLocation


def location_excel_bytes(plant):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Locations"
    sheet.append(LOC_HEADERS)

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    widths = [30, 30]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:B{sheet.max_row}"

    sap_locations = list(
        SAPLocation.objects.filter(plant=plant, is_active=True)
        .annotate(sap_code=Concat(F("code"), Value("_"), F("department")))
        .values_list("sap_code", flat=True)
    )

    dv_category = gen_dv_list(sap_locations, allow_all=False)
    sheet.add_data_validation(dv_category)

    for row in range(2, 500):
        sheet[f"A{row}"] = ""
        dv_category.add(sheet[f"A{row}"])
    workbook.active = 0

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def location_batch_upload(curr_file, sheet_name, *, plant, actor):
    from site_setting.models import TempLocationDetail, TempLocationMain

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

    loc_list = []

    if not sheet_name in workbook.sheetnames:
        workbook.close()
        return "error", f"Sheet name {sheet_name} does NOT exist, please download the latest template. "

    sheet = workbook[sheet_name]

    batch = TempLocationMain.objects.create(
        plant=plant,
        source_filename=curr_file.name[:255],
        created_by=actor,
        updated_by=actor,
    )
    rows = sheet.iter_rows(values_only=True)
    headers = tuple(text_val(value) for value in next(rows))
    if not headers == LOC_HEADERS:
        workbook.close()
        return "error", f"Headers do NOT match, please download the latest template. "

    sap_map = {}
    for sap in SAPLocation.objects.filter(plant=plant).order_by("pk"):
        sap_map.setdefault(sap.code, sap)

    for row in rows:
        if row[0] or row[1]:
            curr_error = []
            curr_valid = True
            curr_sap_id = text_val(row[0].split("_")[0]).strip().upper()
            curr_name = text_val(row[1]).strip()
            if not curr_sap_id:
                curr_valid = False
                curr_error.append("SAP ID cannot be empty. ")
            if not curr_name:
                curr_valid = False
                curr_error.append("Location Name cannot be empty. ")

            curr_sap_ref = sap_map.get(curr_sap_id)
            if not curr_sap_ref:
                curr_valid = False
                curr_error.append(f"SAP ({curr_sap_id}) does not exist in plant {plant.code}")

            loc_list.append(
                TempLocationDetail(
                    batch=batch,
                    plant=plant,
                    sap_location=curr_sap_ref if curr_sap_ref else None,
                    name=curr_name,
                    validation_errors=curr_error,
                    is_valid=curr_valid,
                )
            )
    try:
        TempLocationDetail.objects.bulk_create(loc_list)
    except Exception as e:
        workbook.close()
        return "error", f"Error batch onboarding, f{clean_errors(e)}"

    workbook.close()
    return "success", batch


def _flag_duplicate_names(detail_model, batch):
    """Mark rows whose name repeats within the batch, using one read and one bulk write."""
    rows = list(detail_model.objects.filter(batch=batch))
    name_counts = Counter(row.name for row in rows)
    changed = []
    for row in rows:
        if name_counts[row.name] > 1:
            row.is_valid = False
            row.validation_errors.append("This location name is duplicated in this file. ")
            changed.append(row)
    if changed:
        detail_model.objects.bulk_update(changed, ["is_valid", "validation_errors"])

    error_count = sum(1 for row in rows if not row.is_valid)
    batch.row_count = len(rows)
    batch.ready_count = len(rows) - error_count
    batch.error_count = error_count
    batch.status = "Error" if error_count > 0 else "Preview"
    batch.save()


def location_batch_validate(batch):
    from site_setting.models import TempLocationDetail

    _flag_duplicate_names(TempLocationDetail, batch)
    return ""


def sub_location_excel_bytes(plant):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sub Locations"
    sheet.append(SUB_LOC_HEADERS)

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    widths = [30, 30, 30]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:C{sheet.max_row}"

    sap_locations = dict(
        PhysicalLocation.objects.filter(plant=plant, is_active=True)
        .annotate(sap_code=Concat(F("sap_location__code"), Value("_"), F("sap_location__department")))
        .values_list("name", "sap_code")
    )
    sap_loc_dict = swap_dict_key_value(sap_locations)

    dv_category, dv_sub_category = gen_dv_dict(workbook, sap_loc_dict, "A2")
    sheet.add_data_validation(dv_category)
    sheet.add_data_validation(dv_sub_category)

    for row in range(2, 101):
        sheet[f"A{row}"] = ""
        sheet[f"B{row}"] = ""

        dv_category.add(sheet[f"A{row}"])
        dv_sub_category.add(sheet[f"B{row}"])

    workbook.active = 0

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def sub_location_batch_upload(curr_file, sheet_name, *, plant, actor):
    from site_setting.models import TempSubLocationDetail, TempSubLocationMain

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

    loc_list = []

    if not sheet_name in workbook.sheetnames:
        workbook.close()
        return "error", f"Sheet name {sheet_name} does NOT exist, please download the latest template. "

    sheet = workbook[sheet_name]

    batch = TempSubLocationMain.objects.create(
        plant=plant,
        source_filename=curr_file.name[:255],
        created_by=actor,
        updated_by=actor,
    )
    rows = sheet.iter_rows(values_only=True)
    headers = tuple(text_val(value) for value in next(rows))
    if not headers == SUB_LOC_HEADERS:
        workbook.close()
        return "error", f"Headers do NOT match, please download the latest template. "

    sap_map = {}
    for sap in SAPLocation.objects.filter(plant=plant).order_by("pk"):
        sap_map.setdefault(sap.code, sap)
    physical_map = {}
    for physical in PhysicalLocation.objects.filter(plant=plant).order_by("pk"):
        physical_map.setdefault((physical.sap_location_id, physical.name), physical)

    for row in rows:
        if row[0] or row[1] or row[2]:
            curr_error = []
            curr_valid = True
            curr_sap_id = text_val(row[0].split("_")[0]).strip().upper()
            curr_physical_name = text_val(row[1]).strip()
            curr_name = text_val(row[2]).strip()
            if not curr_sap_id:
                curr_valid = False
                curr_error.append("SAP ID cannot be empty. ")
            if not curr_physical_name:
                curr_valid = False
                curr_error.append("Location Name cannot be empty. ")
            if not curr_name:
                curr_valid = False
                curr_error.append("Sub Location Name cannot be empty. ")

            curr_sap_ref = sap_map.get(curr_sap_id)
            if not curr_sap_ref:
                curr_valid = False
                curr_error.append(f"SAP ({curr_sap_id}) does not exist in plant {plant.code}")

            curr_physical_ref = physical_map.get((curr_sap_ref.pk, curr_physical_name)) if curr_sap_ref else None
            if not curr_physical_ref:
                curr_valid = False
                curr_error.append(f"Location ({curr_physical_name}) does not exist in plant {plant.code}")

            loc_list.append(
                TempSubLocationDetail(
                    batch=batch,
                    plant=plant,
                    physical_location=curr_physical_ref if curr_physical_ref else None,
                    name=curr_name,
                    validation_errors=curr_error,
                    is_valid=curr_valid,
                )
            )
    try:
        TempSubLocationDetail.objects.bulk_create(loc_list)
    except Exception as e:
        workbook.close()
        return "error", f"Error batch onboarding, f{clean_errors(e)}"

    workbook.close()
    return "success", batch


def sub_location_batch_validate(batch):
    from site_setting.models import TempSubLocationDetail

    _flag_duplicate_names(TempSubLocationDetail, batch)
    return ""
