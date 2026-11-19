from django.db.models import F, Sum
from django.db.models.functions import Abs


def get_live_var_context(curr_var_set):
    context = {
        "tk_book_value": 0,
        "tk_count_value": 0,
        "tk_net_val": 0,
        "tk_net_acc": 0,
        "tk_abs_val": 0,
        "tk_abs_acc": 0,
        "cs_avg_acc": 0,
        "cs_abs_qty": 0,
    }

    if curr_var_set is None:
        return context

    total_values = curr_var_set.aggregate(
        book_value=Sum(F("sap_quantity") * F("map_price")),
        net_variance=Sum("variance_value"),
    )
    tk_values = curr_var_set.filter(sap_location__inventory_type="FII_OWNED").aggregate(
        book_value=Sum(F("sap_quantity") * F("map_price")),
        count_value=Sum(F("count_quantity") * F("map_price")),
        net_variance=Sum("variance_value"),
        abs_variance=Sum(Abs("variance_value")),
    )
    cs_variances = curr_var_set.filter(sap_location__inventory_type="CONSIGNED")

    tk_book_value = tk_values["book_value"] or 0
    tk_count_value = tk_values["count_value"] or 0
    tk_net_variance = tk_values["net_variance"] or 0
    tk_abs_variance = tk_values["abs_variance"] or 0

    context["tk_book_value"] = tk_book_value
    context["tk_count_value"] = tk_count_value
    context["tk_net_val"] = tk_net_variance
    context["tk_net_acc"] = (1 - abs(tk_net_variance / tk_book_value)) * 100 if tk_book_value else 0 if tk_count_value else 100
    context["tk_abs_val"] = tk_abs_variance
    context["tk_abs_acc"] = (1 - tk_abs_variance / tk_book_value) * 100 if tk_book_value else 0 if tk_abs_variance else 100
    context["cs_abs_qty"] = cs_variances.aggregate(abs_qty=Sum(Abs("variance_quantity")))["abs_qty"] or 0

    accuracy_total = 0
    accuracy_count = 0
    for variance in cs_variances.only("sap_quantity", "count_quantity").iterator():
        accuracy_total += variance.qty_accuracy
        accuracy_count += 1
    context["cs_avg_acc"] = accuracy_total / accuracy_count if accuracy_count else 0

    return context


def get_part_sap_matrix(curr_var_set, tk_locations, cs_locations):
    from cycles.app_models.inventory_models import PartMaster

    lines = []
    part_sap_matrix = {}
    for var_ref in curr_var_set:
        key = (var_ref.part.part_number, var_ref.sap_location.code)
        part_sap_matrix[key] = var_ref
    parts = curr_var_set.values_list("part__part_number", flat=True).distinct()
    for part in parts:
        inventory_type = []

        tk_var_set = curr_var_set.filter(part__part_number=part, sap_location__inventory_type="FII_OWNED")
        if tk_var_set.exists():
            inventory_type.append("TK")
        tk_var_qty = tk_var_set.aggregate(var_qty=Sum("variance_quantity"))["var_qty"] or 0
        tk_var_val = tk_var_set.aggregate(var_val=Sum(F("variance_quantity") * F("map_price")))["var_val"] or 0

        cs_var_set = curr_var_set.filter(part__part_number=part, sap_location__inventory_type="CONSIGNED")
        if cs_var_set.exists():
            inventory_type.append("CS")
        cs_var_qty = cs_var_set.aggregate(var_qty=Sum("variance_quantity"))["var_qty"] or 0
        cs_abs_qty = cs_var_set.aggregate(abs_qty=Sum(Abs("variance_quantity")))["abs_qty"] or 0
        cs_book_qty = cs_var_set.aggregate(book_qty=Sum("sap_quantity"))["book_qty"] or 0

        resolution_class = "review"
        if cs_abs_qty == 0 and cs_var_qty == 0:
            resolution_status = "Settled"
            resolution_class = "settled"
        else:
            resolution_status = set(curr_var_set.filter(part__part_number=part).values_list("resolutions__status", flat=True))
            resolution_status.discard(None)
            if len(resolution_status) > 1:
                if "To Post" in resolution_status:
                    resolution_status = "Mixed / Review"
                elif "Not Post" in resolution_status:
                    resolution_status = "Partially Resolved"
                else:
                    resolution_status = "Partially Resolved"
            else:
                if "To Post" in resolution_status:
                    resolution_class = "to-post"
                elif "Not Post" in resolution_status:
                    resolution_class = "not-post"
                elif "Posted" in resolution_status:
                    resolution_status = "Fully Posted"
                    resolution_class = "posted"
                else:
                    resolution_status = "Review Needed"

        lines.append(
            {
                "part": PartMaster.objects.filter(part_number=part).first(),
                "inventory_type": "/".join(inventory_type) if inventory_type else "-- --",
                "resolution_status": resolution_status,
                "resolution_class": resolution_class,
                "tk_cells": [
                    (
                        part_sap_matrix.get((part, tk_loc["code"])).variance_quantity
                        if part_sap_matrix.get((part, tk_loc["code"]))
                        else "-- --"
                    )
                    for tk_loc in tk_locations
                ],
                "tk_var_qty": tk_var_qty,
                "tk_var_value": tk_var_val,
                "tk_abs_var": abs(tk_var_val),
                "cs_cells": [
                    (
                        part_sap_matrix.get((part, cs_loc["code"])).variance_quantity
                        if part_sap_matrix.get((part, cs_loc["code"]))
                        else "-- --"
                    )
                    for cs_loc in cs_locations
                ],
                "cs_var_qty": cs_var_qty,
                "cs_abs_qty": cs_abs_qty,
                "cs_accuracy": cs_var_qty / cs_book_qty * 100 if cs_book_qty else 0 if cs_var_qty else 100,
            }
        )
    return {"rows": lines}
