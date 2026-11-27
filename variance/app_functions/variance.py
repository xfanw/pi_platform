from count.models import CountRecord
from django.db.models import Sum
from decimal import Decimal
from cycles.models import BookInventoryLine
from variance.models import CycleVariance


def create_variance(sap_book_ref, count_ref):
    if not sap_book_ref and not count_ref:
        return
    cycle = sap_book_ref.cycle if sap_book_ref else count_ref.cycle if count_ref else None
    plant = cycle.plant if cycle else None

    sap_location = None
    sap_code = None
    sap_department = None
    sap_inventory_type = None

    if sap_book_ref:
        sap_location = sap_book_ref.sap_location
        sap_code = sap_location.code if sap_location else None
        sap_department = sap_location.department if sap_location else None
        sap_inventory_type = sap_location.inventory_type if sap_location else None
    elif count_ref:
        sap_book_ref = BookInventoryLine.objects.filter(cycle=count_ref.cycle, part=count_ref.part).first()
        sap_location = count_ref.sap_location
        sap_code = sap_location.code if sap_location else None
        sap_department = sap_location.department if sap_location else None
        sap_inventory_type = sap_location.inventory_type if sap_location else None

    sap_qty = sap_book_ref.quantity if sap_book_ref else 0
    count_qty = Decimal(count_ref.quantity) if count_ref else 0
    part = sap_book_ref.part if sap_book_ref else count_ref.part if count_ref else None

    CycleVariance.objects.create(
        plant=plant,
        cycle=cycle,
        part=part,
        sap_location=sap_location,
        sap_code=sap_code,
        sap_department=sap_department,
        sap_inventory_type=sap_inventory_type or "",
        sap_quantity=sap_qty,
        count_quantity=count_qty,
        variance_quantity=count_qty - sap_qty,
        variance_value=(count_qty - sap_qty) * (part.price if part else 0),
        map_price=part.price if part else 0,
    )


def update_variance_sap(sap_ref):
    sap_location = sap_ref.sap_location
    sap_code = sap_location.code if sap_location else None
    sap_department = sap_location.department if sap_location else None

    var_ref = CycleVariance.objects.filter(
        plant=sap_ref.cycle.plant,
        cycle=sap_ref.cycle,
        part=sap_ref.part,
        sap_code=sap_code,
    ).first()

    if var_ref:
        count_sum = (
            CountRecord.objects.filter(cycle=sap_ref.cycle, part=sap_ref.part, sap_location=sap_ref.sap_location).aggregate(
                total_quantity=Sum("quantity")
            )["total_quantity"]
            or 0
        )
        sap_qty = sap_ref.quantity if sap_ref else 0
        var_qty = count_sum - sap_qty
        var_ref.sap_quantity = sap_qty
        var_ref.variance_quantity = var_qty
        var_ref.sap_location = sap_location
        var_ref.sap_inventory_type = sap_location.inventory_type if sap_location else None
        if sap_location and sap_location.inventory_type == "CONSIGNED":
            var_ref.variance_value = 0
        else:
            var_ref.variance_value = var_qty * var_ref.map_price
        if var_qty == 0:
            var_ref.status = "Settled"
        else:
            var_ref.status = "Needs Review"
        var_ref.save()
    else:
        create_variance(sap_ref, None)


def update_variance_count(count_ref):
    sap_location = count_ref.sap_location
    sap_code = sap_location.code if sap_location else None

    var_ref = CycleVariance.objects.filter(
        plant=count_ref.cycle.plant,
        cycle=count_ref.cycle,
        part=count_ref.part,
        sap_code=sap_code,
    ).first()

    if var_ref:
        count_sum = (
            CountRecord.objects.filter(cycle=count_ref.cycle, part=count_ref.part, sap_location=count_ref.sap_location).aggregate(
                total_quantity=Sum("quantity")
            )["total_quantity"]
            or 0
        )
        var_ref.count_quantity = count_sum
        var_qty = count_sum - (var_ref.sap_quantity or 0)
        var_ref.variance_quantity = var_qty
        if sap_location and sap_location.inventory_type == "CONSIGNED":
            var_ref.variance_value = 0
        else:
            var_ref.variance_value = var_qty * var_ref.map_price

        if var_qty == 0:
            var_ref.status = "Settled"
        else:
            var_ref.status = "Needs Review"
        var_ref.save()
    else:
        create_variance(None, count_ref)


def delete_variance_count(count_ref):
    sap_location = count_ref.sap_location
    sap_code = sap_location.code if sap_location else None

    var_ref = CycleVariance.objects.filter(
        plant=count_ref.cycle.plant,
        cycle=count_ref.cycle,
        part=count_ref.part,
        sap_code=sap_code,
    ).first()

    if var_ref:
        var_ref.count_quantity -= count_ref.quantity
        var_ref.variance_quantity -= count_ref.quantity
        if sap_location and sap_location.inventory_type == "CONSIGNED":
            var_ref.variance_value = 0
        else:
            var_ref.variance_value = var_ref.variance_quantity * var_ref.map_price
        if var_ref.variance_quantity == 0:
            var_ref.status = "Settled"
        else:
            var_ref.status = "Needs Review"
        var_ref.save()
