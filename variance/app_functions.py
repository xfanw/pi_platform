from count.models import CountRecord
from django.db.models import Sum
from variance.models import CycleVariance


def create_variance(sap_book_ref, count_ref):
    sap_qty = sap_book_ref.quantity if sap_book_ref else 0
    count_qty = count_ref.quantity if count_ref else 0
    part = sap_book_ref.part if sap_book_ref else count_ref.part if count_ref else None
    CycleVariance.objects.create(
        plant=sap_book_ref.plant if sap_book_ref else count_ref.cycle.plant if count_ref else None,
        cycle=sap_book_ref.cycle if sap_book_ref else count_ref.cycle if count_ref else None,
        part=part,
        sap_location=sap_book_ref.sap_location if sap_book_ref else count_ref.sap_location if count_ref else None,
        sap_quantity=sap_qty,
        count_quantity=count_qty,
        variance_quantity=count_qty - sap_qty,
        variance_value=count_qty * (part.price if part else 0),
        map_price=part.price if part else 0,
    )


def update_variance_count(count_ref):
    var_ref = CycleVariance.objects.filter(
        plant=count_ref.cycle.plant,
        cycle=count_ref.cycle,
        part=count_ref.part,
        sap_location=count_ref.sap_location,
    ).first()

    if var_ref:
        count_sum = (
            CountRecord.objects.filter(cycle=count_ref.cycle, part=count_ref.part, sap_location=count_ref.sap_location).aggregate(
                total_quantity=Sum("quantity")
            )["total_quantity"]
            or 0
        )
        var_ref.count_quantity = count_sum
        var_ref.variance_quantity = count_sum - (var_ref.sap_quantity or 0)
        var_ref.variance_value = (count_sum - (var_ref.sap_quantity or 0)) * var_ref.map_price
        var_ref.save()
    else:
        create_variance(None, count_ref)


def delete_variance_count(count_ref):
    var_ref = CycleVariance.objects.filter(
        plant=count_ref.cycle.plant,
        cycle=count_ref.cycle,
        part=count_ref.part,
        sap_location=count_ref.sap_location,
    ).first()

    if var_ref:
        count_sum = (
            CountRecord.objects.filter(cycle=count_ref.cycle, part=count_ref.part, sap_location=count_ref.sap_location)
            .exclude(id=count_ref.id)
            .aggregate(total_quantity=Sum("quantity"))["total_quantity"]
            or 0
        )
        var_ref.count_quantity = count_sum
        var_ref.variance_quantity = count_sum - (var_ref.sap_quantity or 0)
        var_ref.variance_value = (count_sum - (var_ref.sap_quantity or 0)) * var_ref.map_price
        var_ref.save()
    else:
        create_variance(None, count_ref)
