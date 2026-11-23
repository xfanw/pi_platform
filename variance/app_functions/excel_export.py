from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


def variance_export_excel_bytes(excel_context, curr_var_set, tk_locations, cs_locations):
    """Generate Excel file for variance export with two sheets: Summary and Details"""

    workbook = Workbook()

    # Remove default sheet
    if "Sheet" in workbook.sheetnames:
        workbook.remove(workbook["Sheet"])

    # Create Summary Sheet
    _create_summary_sheet(workbook, excel_context)

    # Create Details Sheet
    _create_details_sheet(workbook, curr_var_set, tk_locations, cs_locations)

    # Write to bytes
    excel_bytes = BytesIO()
    workbook.save(excel_bytes)
    excel_bytes.seek(0)

    return excel_bytes.getvalue()


def _create_summary_sheet(workbook, excel_context):
    """Create summary sheet with high-level variance statistics"""

    ws = workbook.create_sheet("Summary", 0)

    # Define styles
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    section_fill = PatternFill(start_color="B4C7E7", end_color="B4C7E7", fill_type="solid")
    section_font = Font(bold=True, size=11)
    border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))

    row = 1

    # Title
    ws.merge_cells(f"A{row}:B{row}")
    title_cell = ws[f"A{row}"]
    title_cell.value = f"Variance Summary: {excel_context.get('cycle_name', '')}"
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    row += 2

    # FII_OWNED (Traded Kept) Section
    ws.merge_cells(f"A{row}:B{row}")
    ws[f"A{row}"] = "FII_OWNED (TK) Inventory"
    ws[f"A{row}"].font = section_font
    ws[f"A{row}"].fill = section_fill
    row += 1

    _add_summary_row(ws, row, "Book Value", excel_context.get("tk_book_value", 0), border)
    row += 1
    _add_summary_row(ws, row, "Count Value", excel_context.get("tk_count_value", 0), border)
    row += 1
    _add_summary_row(ws, row, "Net Variance", excel_context.get("tk_net_val", 0), border)
    row += 1
    _add_summary_row(ws, row, "Variance Accuracy", f"{round(excel_context.get('tk_net_acc', 0), 2)}%", border)
    row += 1
    _add_summary_row(ws, row, "Absolute Variance", excel_context.get("tk_abs_val", 0), border)
    row += 1
    _add_summary_row(ws, row, "Absolute Variance Accuracy", f"{round(excel_context.get('tk_abs_acc', 0), 2)}%", border)
    row += 2

    # CONSIGNED Section
    ws.merge_cells(f"A{row}:B{row}")
    ws[f"A{row}"] = "CONSIGNED Inventory"
    ws[f"A{row}"].font = section_font
    ws[f"A{row}"].fill = section_fill
    row += 1

    _add_summary_row(ws, row, "Average P/N Quantity Accuracy", f"{round(excel_context.get('cs_avg_acc', 0), 2)}%", border)
    row += 1
    _add_summary_row(ws, row, "Absolute Quantity Variance", excel_context.get("cs_abs_qty", 0), border)

    # Set column widths
    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 25


def _add_summary_row(ws, row, label, value, border):
    """Add a row to summary sheet"""
    ws[f"A{row}"] = label
    ws[f"A{row}"].border = border
    ws[f"B{row}"] = value
    ws[f"B{row}"].border = border
    ws[f"B{row}"].alignment = Alignment(horizontal="right")


def _create_details_sheet(workbook, curr_var_set, tk_locations, cs_locations):
    """Create details sheet with variance matrix similar to live report"""

    from variance.app_functions.report import get_part_sap_matrix

    ws = workbook.create_sheet("Details", 1)

    # Define styles
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    section_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    section_font = Font(bold=True)
    border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    right_align = Alignment(horizontal="right", vertical="center")

    row = 1

    # Get matrix data
    matrix_data = get_part_sap_matrix(curr_var_set, tk_locations, cs_locations)
    rows_data = matrix_data.get("rows", [])

    if not rows_data:
        ws[f"A{row}"] = "No variance data available"
        return

    # Title row
    ws.merge_cells(f"A{row}:H{row}")
    title_cell = ws[f"A{row}"]
    title_cell.value = "Variance Details Matrix"
    title_cell.font = Font(bold=True, size=12)
    title_cell.alignment = center_align
    row += 2

    # Determine column layout
    # Fixed columns: Part Number, Inventory Type, Resolution Status
    # Then TK locations columns, TK totals, CS locations columns, CS totals

    # Build header
    headers = ["Part Number", "Inventory Type", "Resolution Status"]

    # Add TK location headers
    for tk_loc in tk_locations:
        headers.append(f"TK {tk_loc['code']}")

    headers.extend(["TK Qty", "TK Value", "TK Abs Var"])

    # Add CS location headers
    for cs_loc in cs_locations:
        headers.append(f"CS {cs_loc['code']}")

    headers.extend(["CS Qty", "CS Abs Qty", "CS Accuracy %"])

    # Write headers
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = border
        cell.alignment = center_align if col == 1 else center_align

    row += 1

    # Write data rows
    for line in rows_data:
        part = line.get("part")
        part_number = part.part_number if part else "Unknown"

        col = 1
        ws.cell(row=row, column=col, value=part_number).border = border
        col += 1

        ws.cell(row=row, column=col, value=line.get("inventory_type", "")).border = border
        col += 1

        resolution = ws.cell(row=row, column=col, value=line.get("resolution_status", ""))
        resolution.border = border
        resolution.alignment = center_align
        col += 1

        # TK cells
        for tk_cell_val in line.get("tk_cells", []):
            cell = ws.cell(row=row, column=col, value=tk_cell_val if tk_cell_val != "-- --" else None)
            cell.border = border
            cell.alignment = right_align if isinstance(tk_cell_val, (int, float)) else center_align
            col += 1

        # TK totals
        for tk_total in [line.get("tk_var_qty"), line.get("tk_var_value"), line.get("tk_abs_var")]:
            cell = ws.cell(row=row, column=col, value=tk_total)
            cell.border = border
            cell.alignment = right_align
            col += 1

        # CS cells
        for cs_cell_val in line.get("cs_cells", []):
            cell = ws.cell(row=row, column=col, value=cs_cell_val if cs_cell_val != "-- --" else None)
            cell.border = border
            cell.alignment = right_align if isinstance(cs_cell_val, (int, float)) else center_align
            col += 1

        # CS totals
        cs_accuracy = line.get("cs_accuracy", 0)
        for cs_total in [line.get("cs_var_qty"), line.get("cs_abs_qty"), round(cs_accuracy, 2) if cs_accuracy else 0]:
            cell = ws.cell(row=row, column=col, value=cs_total)
            cell.border = border
            cell.alignment = right_align
            col += 1

        row += 1

    # Auto-fit columns
    for col_idx, header in enumerate(headers, 1):
        ws.column_dimensions[
            chr(64 + col_idx) if col_idx <= 26 else chr(64 + (col_idx - 1) // 26) + chr(65 + (col_idx - 1) % 26)
        ].width = 15
