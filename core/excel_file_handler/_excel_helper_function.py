from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName


def text_val(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def gen_dv_list(curr_list, *, allow_all=True, allow_blank=True):
    curr_str = ",".join(curr_list)
    formula_str = f'"All,{curr_str}"' if allow_all else f'"{curr_str}"'
    dv = DataValidation(type="list", formula1=formula_str, allow_blank=allow_blank)
    dv.error = "Your entry is not in the list"
    dv.errorTitle = "Invalid Entry"
    dv.showErrorMessage = True

    return dv


def gen_dv_dict(workbook, curr_dict, col):
    ws_source = workbook.create_sheet(title="Dropdown Sources")
    defined_names = workbook.defined_names

    # Single pass: write each column and register its named range
    for col_idx, (category, items) in enumerate(curr_dict.items(), start=1):
        col_letter = get_column_letter(col_idx)
        ws_source.cell(row=1, column=col_idx, value=category)
        for row_idx, item in enumerate(items, start=2):
            ws_source.cell(row=row_idx, column=col_idx, value=item)

        sub_dn = DefinedName(name=category)
        sub_dn.value = f"'Dropdown Sources'!${col_letter}$2:${col_letter}${len(items) + 1}"
        defined_names[category] = sub_dn

    max_col_letter = get_column_letter(len(curr_dict))
    categories_dn = DefinedName(name="CategoriesList")
    categories_dn.value = f"'Dropdown Sources'!$A$1:${max_col_letter}$1"
    defined_names["CategoriesList"] = categories_dn

    dv_category = DataValidation(type="list", formula1="=CategoriesList", allow_blank=True)
    dv_sub_category = DataValidation(type="list", formula1=f"=INDIRECT({col})", allow_blank=True)
    ws_source.state = "hidden"
    return dv_category, dv_sub_category
