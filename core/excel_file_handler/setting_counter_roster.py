from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from django.db import transaction
from django.db.models import Count, Q

from core.app_functions import clean_errors, swap_dict_key_value
from core.constants import MAX_FILE_BYTES, COUNTER_HEADERS
from core.excel_file_handler._excel_helper_function import gen_dv_dict, text_val


def counter_roster_excel_bytes(plant):
    from site_setting.models import SAPLocation

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Counter"
    sheet.append(COUNTER_HEADERS)
    sheet.append(
        [
            "10001",
            "Alex Counter",
            "All",
            "All",
        ]
    )

    fill = PatternFill("solid", fgColor="DDEEFF")
    for cell in sheet[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
        cell.alignment = Alignment(horizontal="center")
    widths = [20, 30, 20, 30]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:D{sheet.max_row}"

    guide = workbook.create_sheet("Instructions")
    guide.append(["Rule", "Description"])
    rules = [
        ("One row", "One person per row. Imports are additive and never deactivate omitted people."),
        ("Multiple Rows", "If a person has multiple ownership or SAP Locations, use multiple rows."),
        ("Ownership", "Empty means All. Use an active Ownership code or name from Plant Setup."),
        ("SAP Locations", "Empty means All. One row for each SAP Location."),
    ]
    for item in rules:
        guide.append(item)
    for cell in guide[1]:
        cell.fill = fill
        cell.font = Font(bold=True, color="103B6D")
    guide.column_dimensions["A"].width = 22
    guide.column_dimensions["B"].width = 95
    for row in guide.iter_rows(min_row=2):
        row[0].alignment = Alignment(vertical="center")
        row[1].alignment = Alignment(wrap_text=True, vertical="top")

    sap_locations = dict(SAPLocation.objects.filter(plant=plant, is_active=True).values_list("code", "department"))
    sap_loc_dict = swap_dict_key_value(sap_locations)

    dv_category, dv_sub_category = gen_dv_dict(workbook, sap_loc_dict, "C2")
    sheet.add_data_validation(dv_category)
    sheet.add_data_validation(dv_sub_category)

    for row in range(2, 101):
        sheet[f"C{row}"] = ""
        sheet[f"D{row}"] = ""

        dv_category.add(sheet[f"C{row}"])
        dv_sub_category.add(sheet[f"D{row}"])
    workbook.active = 0

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


@transaction.atomic
def counter_batch_upload(curr_file, sheet_name, *, plant, actor):
    from access_control.models import CounterOnboardingRow, UserOnboardingBatch
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

    user_list = []

    if not sheet_name in workbook.sheetnames:
        workbook.close()
        return "error", f"Sheet name {sheet_name} does NOT exist, please download the latest template. "

    sheet = workbook[sheet_name]

    batch = UserOnboardingBatch.objects.create(
        plant=plant,
        source_filename=curr_file.name[:255],
        created_by=actor,
        updated_by=actor,
    )
    rows = sheet.iter_rows(values_only=True)
    headers = tuple(text_val(value) for value in next(rows))
    if not headers == COUNTER_HEADERS:
        workbook.close()
        return "error", f"Headers do NOT match, please download the latest template. "

    # Load the plant's SAP locations once; setdefault keeps the first match like .first()
    by_department, by_code, by_both = {}, {}, {}
    for loc in SAPLocation.objects.filter(plant=plant).order_by("pk"):
        by_department.setdefault(loc.department, loc)
        by_code.setdefault(loc.code, loc)
        by_both.setdefault((loc.department, loc.code), loc)

    validated_location = []
    row_index = 1
    for row in rows:
        row_index += 1
        if row[0] or row[1]:
            curr_error = []
            curr_valid = True
            curr_emp_id = text_val(row[0]).strip().capitalize()
            curr_name = text_val(row[1]).strip().capitalize()
            curr_depart = text_val(row[2]).strip() if row[2] else ""
            curr_sap_loc = text_val(row[3]).strip() if row[3] else ""
            if not curr_emp_id:
                curr_valid = False
                curr_error.append("User ID cannot be empty. ")
            if not curr_name:
                curr_valid = False
                curr_error.append("User Name cannot be empty. ")
            if not curr_depart and not curr_sap_loc:
                pass
            elif curr_depart and not curr_sap_loc:
                sap_ref = by_department.get(curr_depart)
                if not sap_ref:
                    curr_valid = False
                    curr_error.append(f"Ownership ({curr_depart}) does not exist in plant {plant.code}")

            elif not curr_depart and curr_sap_loc:
                sap_ref = by_code.get(curr_sap_loc)
                if not sap_ref:
                    curr_valid = False
                    curr_error.append(f"SAP Location ({curr_sap_loc}) does not exist in plant {plant.code}")
                else:
                    curr_depart = sap_ref.department
            elif curr_depart and curr_sap_loc:
                sap_ref = by_both.get((curr_depart, curr_sap_loc))
                if not sap_ref:
                    curr_valid = False
                    curr_error.append(f"SAP Location ({curr_sap_loc}/{curr_depart}) does not exist in plant {plant.code}")
                else:
                    validated_location.append((curr_depart, curr_sap_loc))

            user_list.append(
                CounterOnboardingRow(
                    batch=batch,
                    row_number=row_index,
                    employee_id=curr_emp_id,
                    display_name=curr_name,
                    department=curr_depart,
                    sap_location=sap_ref if curr_sap_loc else None,
                    validation_errors=curr_error,
                    is_valid=curr_valid,
                )
            )
    try:
        CounterOnboardingRow.objects.bulk_create(user_list)
    except Exception as e:
        workbook.close()
        return "error", f"Error batch onboarding, f{clean_errors(e)}"

    workbook.close()
    return "success", batch


def counter_batch_validate(batch):
    from access_control.models import CounterOnboardingRow

    status = CounterOnboardingRow.objects.filter(batch=batch).aggregate(
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
