from django.db.models import F, Q, Count, Sum, DecimalField
from django.db.models.functions import Abs

from audit.models import AuditCandidate, AuditRecord
from django.db import transaction

from count.models import CycleTagDetail
from cycles.app_models.cycle_models import CycleSAPLocation
from cycles.app_models.inventory_models import PartMaster
from variance.models import CycleVariance


def link_candidates_to_audit_records(plan_ref, candidate_set, selection_reason):
    """
    Link created AuditCandidates to their related AuditRecords.

    After candidates are created via bulk_create, this function:
    1. Maps candidates by (sap_location_code, part_number)
    2. Updates all matching AuditRecords with the candidate foreign key
    3. Uses bulk_update for efficiency

    Args:
        plan_ref: The AuditPlan object
        candidate_set: List of dicts with 'sap_location_code' and 'part_number_snapshot' keys
        selection_reason: String value to filter candidates (selection_reason field)
    """
    if not candidate_set:
        return

    # Query created candidates with their ID and identifiers
    candidate_map = {}
    created_candidates = AuditCandidate.objects.filter(plan=plan_ref, selection_reason=selection_reason).values_list(
        "id", "sap_location__code", "part_number_snapshot"
    )

    for candidate_id, sap_code, part_number in created_candidates:
        candidate_map[(sap_code, part_number)] = candidate_id

    # Build audit records to update
    audit_records_to_update = []
    for item in candidate_set:
        sap_code = item["sap_location_code"]
        part_number = item["part_number_snapshot"]
        candidate_id = candidate_map.get((sap_code, part_number))

        if candidate_id:
            # Get all matching audit records and prepare for update
            audit_records = AuditRecord.objects.filter(
                plan=plan_ref, sap_location_code=sap_code, part_number_snapshot=part_number, selected=True
            )
            for record in audit_records:
                record.candidate_id = candidate_id
                audit_records_to_update.append(record)

    # Bulk update all audit records
    if audit_records_to_update:
        AuditRecord.objects.bulk_update(audit_records_to_update, ["candidate_id"], batch_size=1000)


def generate_audit_records(audit_plan, count_records):
    """
    Efficiently generate AuditRecord entries from count_records with minimal DB queries.
    Takes snapshots of key fields from CountRecord at the time of audit generation.

    Optimization strategy:
    - Delete existing records in single query
    - Prefetch related objects to avoid N+1 queries
    - Batch variance lookups instead of per-record queries
    - Batch tag lookups instead of per-record queries
    - Use bulk_create with batch_size for memory efficiency
    - Minimize field transformations and lookups
    """
    # Single query to delete existing records
    AuditRecord.objects.filter(plan=audit_plan).delete()

    # Prefetch related objects to avoid N+1 queries
    count_records = count_records.select_related("sap_location", "physical_location", "sub_location", "part")

    # First pass: collect IDs for batch lookups
    count_records_list = list(count_records)

    if not count_records_list:
        return []

    sap_location_ids = set()
    part_ids = set()
    tag_numbers = set()

    for count_record in count_records_list:
        sap_location_ids.add(count_record.sap_location_id)
        part_ids.add(count_record.part_id)
        if count_record.tag_number:
            tag_numbers.add(count_record.tag_number)

    # Batch prefetch all variance records (single query)
    variances_map = {}
    if sap_location_ids and part_ids:
        variances = CycleVariance.objects.filter(cycle=audit_plan.cycle, sap_location_id__in=sap_location_ids, part_id__in=part_ids)
        for variance in variances:
            variances_map[(variance.sap_location_id, variance.part_id)] = variance

    # Batch prefetch all tag details (single query instead of N queries!)
    tags_map = {}
    if tag_numbers:
        tags = CycleTagDetail.objects.filter(tag_number__in=tag_numbers)
        for tag in tags:
            tags_map[tag.tag_number] = tag

    # Build audit records list in memory (no DB calls)
    audit_records_to_create = []

    for count_record in count_records_list:
        # Get cached variance record
        variance_key = (count_record.sap_location_id, count_record.part_id)
        variance = variances_map.get(variance_key)

        # Get cached tag record
        tag = tags_map.get(count_record.tag_number) if count_record.tag_number else None

        # Build snapshot strings efficiently (avoid if/else for each field)
        physical_location_name = count_record.physical_location.name if count_record.physical_location else ""
        sub_location_name = count_record.sub_location.name if count_record.sub_location else ""

        audit_records_to_create.append(
            AuditRecord(
                plan=audit_plan,
                source_count_record=count_record,
                candidate=None,
                sap_location=count_record.sap_location,
                physical_location=count_record.physical_location,
                sub_location=count_record.sub_location,
                variance=variance,
                tag_number=tag,
                sap_location_code=count_record.sap_location.code,
                physical_location_snapshot=physical_location_name,
                sub_location_snapshot=sub_location_name,
                tag_number_snapshot=count_record.tag_number,
                part_number_snapshot=count_record.part.part_number,
                count_quantity_snapshot=count_record.quantity,
                price_snapshot=count_record.part.price,
                selected=False,
                page_number=0,
            )
        )

    # Bulk create with batching to manage memory for large datasets
    if audit_records_to_create:
        record_set = AuditRecord.objects.bulk_create(audit_records_to_create, batch_size=1000)
    else:
        record_set = []

    return record_set


@transaction.atomic
def regenerate_candidates(plan_ref):
    target_count = plan_ref.target_count
    top_80_target = int(target_count * plan_ref.value_pct / 100)
    # TODO:
    # Top 80% is calculated separately for each SAP Location and part_number. ignore count_quantity = 0
    # Lines are sorted by positive Book Value * book inventory, highest first.
    # if top 80% count >= target_count, stop selecting 85% from the top 80% candidates for that SAP Location and part_number.
    # else select all top 80% candidates
    # after top_80 record selection, continue selecting from the remaining candidates based on High Value and High Abs Variance until target_count is reached.
    top_80_count_real, small_audit = generate_top_80_candidates(plan_ref, target_count, top_80_target)

    if small_audit:
        # Variance and MAP > 100
        top_variance_target = min(target_count - top_80_count_real, int(target_count * plan_ref.variance_pct / 100))
        real_top_variance_count = generate_top_variance_candidates(plan_ref, top_variance_target)
        # MAP
        top_map_target = min(target_count - top_80_count_real - real_top_variance_count, int(target_count * plan_ref.map_pct / 100))
        real_top_map_count = generate_top_map_candidates(plan_ref, top_map_target)

        plan_ref.real_top_80_count = top_80_count_real
        plan_ref.real_variance_count = real_top_variance_count
        plan_ref.real_map_count = real_top_map_count
        plan_ref.real_total_count = top_80_count_real + real_top_variance_count + real_top_map_count
        plan_ref.save()
    else:
        # 10% MAP
        top_map_target = min(target_count - top_80_count_real, int(target_count * plan_ref.map_pct / 100))
        real_top_map_count = generate_top_map_candidates(plan_ref, top_map_target)
        # 5% of abs variance
        top_variance_target = min(
            target_count - top_80_count_real - real_top_map_count, int(target_count * plan_ref.variance_pct / 100)
        )
        real_top_variance_count = generate_top_variance_candidates(plan_ref, top_variance_target)

        plan_ref.real_top_80_count = top_80_count_real
        plan_ref.real_variance_count = real_top_variance_count
        plan_ref.real_map_count = real_top_map_count
        plan_ref.real_total_count = top_80_count_real + real_top_variance_count + real_top_map_count
        plan_ref.save()


def generate_top_80_candidates(plan_ref, target_count, top_80_target):
    """
    Efficiently generate top 80% candidates with minimal DB queries.

    Optimization strategy:
    - Use aggregation with variance FK to get book values in a single query
    - Leverage variance data already available via FK (no separate variance lookup!)
    - Batch create candidates instead of individual creates
    - Use bulk_update for marking selected records
    - Prefetch related objects to avoid N+1 queries
    """

    # Single aggregation query to get book value by SAP location and part
    # Include variance data via FK to avoid separate queries
    book_inventory_set = list(
        AuditRecord.objects.filter(plan=plan_ref, selected=False)
        .select_related("variance__part")  # Prefetch variance and its part
        .values("sap_location_code", "part_number_snapshot", "price_snapshot", "variance_id")
        .annotate(
            book_value_sum=Sum(F("count_quantity_snapshot") * F("price_snapshot")),
            count_val=Count("id"),
            physical_location_count=Count("physical_location_snapshot", distinct=True),
            sub_location_count=Count("sub_location_snapshot", distinct=True),
            tag_count=Count("tag_number_snapshot", distinct=True),
            # Get variance data via aggregation
            variance_value_sum=Sum("variance__variance_value"),
            abs_variance_sum=Sum(Abs(F("variance__variance_value")), output_field=DecimalField()),
            sap_quantity_sum=Sum("variance__sap_quantity"),
            map_price_first=F("variance__map_price"),
        )
        .order_by("-book_value_sum")
    )

    if not book_inventory_set:
        return 0, False

    top_80_count_real = sum(item["count_val"] for item in book_inventory_set)
    book_set = []
    small_audit = False

    if top_80_count_real >= target_count:
        temp_sum = 0

        for item in book_inventory_set:
            if temp_sum >= top_80_target:
                break
            book_set.append(item)
            temp_sum += item["count_val"]

        top_80_count_real = temp_sum
    else:
        book_set = book_inventory_set
        small_audit = True

    # Batch update selected records
    if book_set:
        # Build Q filter for all book_set items
        q_filter = Q()
        for item in book_set:
            q_filter |= Q(sap_location_code=item["sap_location_code"], part_number_snapshot=item["part_number_snapshot"])

        # Single bulk update
        AuditRecord.objects.filter(q_filter).update(selected=True)

    # Prefetch related objects for all book_set items in batch
    sap_codes = {item["sap_location_code"] for item in book_set}
    part_numbers = {item["part_number_snapshot"] for item in book_set}
    variance_ids = {item["variance_id"] for item in book_set if item["variance_id"]}

    # Single queries to get all related objects
    sap_locations_map = {}
    if sap_codes:
        sap_locations = CycleSAPLocation.objects.filter(cycle=plan_ref.cycle, sap_location__code__in=sap_codes).select_related(
            "sap_location"
        )
        for sap in sap_locations:
            sap_locations_map[sap.sap_location.code] = sap.sap_location

    parts_map = {}
    if part_numbers:
        parts = PartMaster.objects.filter(cycle=plan_ref.cycle, part_number__in=part_numbers)
        for part in parts:
            parts_map[part.part_number] = part

    # Get variances by ID (no need to filter by cycle/sap_code/part anymore!)
    variances_map = {}
    if variance_ids:
        variances = CycleVariance.objects.filter(id__in=variance_ids)
        for var in variances:
            variances_map[var.id] = var

    # Build candidates list for bulk create
    candidates_to_create = []

    for item in book_set:
        sap_code = item["sap_location_code"]
        part_number = item["part_number_snapshot"]
        variance_id = item["variance_id"]

        sap_location = sap_locations_map.get(sap_code)
        part = parts_map.get(part_number)
        variance = variances_map.get(variance_id)

        # Use variance data from aggregation, fallback to retrieved variance object
        book_value = variance.sap_quantity * variance.map_price if variance else item["book_value_sum"]
        variance_value = variance.variance_value if variance else (item["variance_value_sum"] or 0)
        abs_variance = abs(variance.variance_value) if variance else abs(item["abs_variance_sum"] or 0)
        map_price = part.price if part else item["price_snapshot"]

        candidates_to_create.append(
            AuditCandidate(
                plan=plan_ref,
                sap_location=sap_location,
                part=part,
                part_number_snapshot=part_number,
                description_snapshot=part.description if part else "",
                book_value=book_value,
                map_price=map_price,
                variance_value=variance_value,
                abs_variance=abs_variance,
                count_records=item["count_val"],
                location_count=item["physical_location_count"],
                sub_location_count=item["sub_location_count"],
                tag_count=item["tag_count"],
                coverage_pct=0,
                selected_records=item["count_val"],
                selection_reason="Top 80% Value",
                manual_override=0,
            )
        )

    # Single bulk create for all candidates
    if candidates_to_create:
        AuditCandidate.objects.bulk_create(candidates_to_create, batch_size=1000)
        link_candidates_to_audit_records(plan_ref, book_set, selection_reason="Top 80% Value")

    return top_80_count_real, small_audit


def generate_top_variance_candidates(plan_ref, top_variance_target):
    """
    Efficiently generate top variance candidates with minimal DB queries.

    Selects candidates with the highest absolute variance values.
    Similar structure to generate_top_80_candidates but sorted by variance instead of book value.

    Optimization strategy:
    - Use aggregation with variance FK to get variance values in a single query
    - Leverage variance data already available via FK (no separate variance lookup!)
    - Batch create candidates instead of individual creates
    - Use bulk_update for marking selected records
    """

    # Single aggregation query to get variance values by SAP location and part
    # Include variance data via FK to avoid separate queries
    variance_inventory_set = list(
        AuditRecord.objects.filter(plan=plan_ref, selected=False)
        .select_related("variance__part")  # Prefetch variance and its part
        .values("sap_location_code", "part_number_snapshot", "price_snapshot", "variance_id")
        .annotate(
            abs_variance_sum=Sum(Abs("variance__variance_value")),
            variance_value_sum=Sum("variance__variance_value"),
            count_val=Count("id"),
            physical_location_count=Count("physical_location_snapshot", distinct=True),
            sub_location_count=Count("sub_location_snapshot", distinct=True),
            tag_count=Count("tag_number_snapshot", distinct=True),
            book_value_sum=Sum(F("count_quantity_snapshot") * F("price_snapshot")),
        )
        .order_by("-abs_variance_sum")  # Sort by absolute variance descending
    )

    if not variance_inventory_set:
        return 0

    variance_count_real = sum(item["count_val"] for item in variance_inventory_set)
    variance_set = []

    # Select candidates until reaching top_variance_target
    temp_sum = 0
    for item in variance_inventory_set:
        if temp_sum >= top_variance_target:
            break
        variance_set.append(item)
        temp_sum += item["count_val"]
    variance_count_real = temp_sum
    # Batch update selected records
    if variance_set:
        # Build Q filter for all variance_set items
        q_filter = Q()
        for item in variance_set:
            q_filter |= Q(sap_location_code=item["sap_location_code"], part_number_snapshot=item["part_number_snapshot"])

        # Single bulk update
        AuditRecord.objects.filter(q_filter).update(selected=True)

    # Prefetch related objects for all variance_set items in batch
    sap_codes = {item["sap_location_code"] for item in variance_set}
    part_numbers = {item["part_number_snapshot"] for item in variance_set}
    variance_ids = {item["variance_id"] for item in variance_set if item["variance_id"]}

    # Single queries to get all related objects
    sap_locations_map = {}
    if sap_codes:
        sap_locations = CycleSAPLocation.objects.filter(cycle=plan_ref.cycle, sap_location__code__in=sap_codes).select_related(
            "sap_location"
        )
        for sap in sap_locations:
            sap_locations_map[sap.sap_location.code] = sap.sap_location

    parts_map = {}
    if part_numbers:
        parts = PartMaster.objects.filter(cycle=plan_ref.cycle, part_number__in=part_numbers)
        for part in parts:
            parts_map[part.part_number] = part

    # Get variances by ID (direct lookup via FK)
    variances_map = {}
    if variance_ids:
        variances = CycleVariance.objects.filter(id__in=variance_ids)
        for var in variances:
            variances_map[var.id] = var

    # Build candidates list for bulk create
    candidates_to_create = []

    for item in variance_set:
        sap_code = item["sap_location_code"]
        part_number = item["part_number_snapshot"]
        variance_id = item["variance_id"]

        sap_location = sap_locations_map.get(sap_code)
        part = parts_map.get(part_number)
        variance = variances_map.get(variance_id)

        # Use variance data
        book_value = variance.sap_quantity * variance.map_price if variance else item["book_value_sum"]
        variance_value = variance.variance_value if variance else (item["variance_value_sum"] or 0)
        abs_variance = abs(variance.variance_value) if variance else abs(item["abs_variance_sum"] or 0)
        map_price = part.price if part else item["price_snapshot"]

        candidates_to_create.append(
            AuditCandidate(
                plan=plan_ref,
                sap_location=sap_location,
                part=part,
                part_number_snapshot=part_number,
                description_snapshot=part.description if part else "",
                book_value=book_value,
                map_price=map_price,
                variance_value=variance_value,
                abs_variance=abs_variance,
                count_records=item["count_val"],
                location_count=item["physical_location_count"],
                sub_location_count=item["sub_location_count"],
                tag_count=item["tag_count"],
                coverage_pct=0,
                selected_records=item["count_val"],
                selection_reason="High Abs Variance",
                manual_override=0,
            )
        )

    # Single bulk create for all candidates
    if candidates_to_create:
        AuditCandidate.objects.bulk_create(candidates_to_create, batch_size=1000)
        link_candidates_to_audit_records(plan_ref, variance_set, selection_reason="High Abs Variance")

    return variance_count_real


def generate_top_map_candidates(plan_ref, top_map_target):
    """
    Efficiently generate top MAP (Map Price) candidates with minimal DB queries.

    Selects candidates with the highest MAP price values.
    Similar structure to generate_top_variance_candidates but sorted by map_price instead of variance.

    Optimization strategy:
    - Use aggregation with variance FK to get MAP prices in a single query
    - Leverage variance data already available via FK (no separate variance lookup!)
    - Batch create candidates instead of individual creates
    - Use bulk_update for marking selected records
    """

    # Single aggregation query to get MAP prices by SAP location and part
    # Include variance data via FK to avoid separate queries
    map_inventory_set = list(
        AuditRecord.objects.filter(plan=plan_ref, selected=False)
        .select_related("variance__part")  # Prefetch variance and its part
        .values("sap_location_code", "part_number_snapshot", "price_snapshot", "variance_id")
        .annotate(
            count_val=Count("id"),
            physical_location_count=Count("physical_location_snapshot", distinct=True),
            sub_location_count=Count("sub_location_snapshot", distinct=True),
            tag_count=Count("tag_number_snapshot", distinct=True),
            abs_variance_sum=Sum(Abs("variance__variance_value")),
            variance_value_sum=Sum("variance__variance_value"),
            book_value_sum=Sum(F("count_quantity_snapshot") * F("price_snapshot")),
            map_price_value=F("price_snapshot"),  # Use price_snapshot as MAP price
        )
        .order_by("-price_snapshot")  # Sort by MAP price descending
    )

    if not map_inventory_set:
        return 0

    map_count_real = sum(item["count_val"] for item in map_inventory_set)
    map_set = []

    # Select candidates until reaching top_map_target
    temp_sum = 0
    for item in map_inventory_set:
        if temp_sum >= top_map_target:
            break
        map_set.append(item)
        temp_sum += item["count_val"]
    map_count_real = temp_sum
    # Batch update selected records
    if map_set:
        # Build Q filter for all map_set items
        q_filter = Q()
        for item in map_set:
            q_filter |= Q(sap_location_code=item["sap_location_code"], part_number_snapshot=item["part_number_snapshot"])

        # Single bulk update
        AuditRecord.objects.filter(q_filter).update(selected=True)

    # Prefetch related objects for all map_set items in batch
    sap_codes = {item["sap_location_code"] for item in map_set}
    part_numbers = {item["part_number_snapshot"] for item in map_set}
    variance_ids = {item["variance_id"] for item in map_set if item["variance_id"]}

    # Single queries to get all related objects
    sap_locations_map = {}
    if sap_codes:
        sap_locations = CycleSAPLocation.objects.filter(cycle=plan_ref.cycle, sap_location__code__in=sap_codes).select_related(
            "sap_location"
        )
        for sap in sap_locations:
            sap_locations_map[sap.sap_location.code] = sap.sap_location

    parts_map = {}
    if part_numbers:
        parts = PartMaster.objects.filter(cycle=plan_ref.cycle, part_number__in=part_numbers)
        for part in parts:
            parts_map[part.part_number] = part

    # Get variances by ID (direct lookup via FK)
    variances_map = {}
    if variance_ids:
        variances = CycleVariance.objects.filter(id__in=variance_ids)
        for var in variances:
            variances_map[var.id] = var

    # Build candidates list for bulk create
    candidates_to_create = []

    for item in map_set:
        sap_code = item["sap_location_code"]
        part_number = item["part_number_snapshot"]
        variance_id = item["variance_id"]

        sap_location = sap_locations_map.get(sap_code)
        part = parts_map.get(part_number)
        variance = variances_map.get(variance_id)

        # Use variance data
        book_value = variance.sap_quantity * variance.map_price if variance else item["book_value_sum"]
        variance_value = variance.variance_value if variance else (item["variance_value_sum"] or 0)
        abs_variance = abs(variance.variance_value) if variance else abs(item["abs_variance_sum"] or 0)
        map_price = part.price if part else item["price_snapshot"]

        candidates_to_create.append(
            AuditCandidate(
                plan=plan_ref,
                sap_location=sap_location,
                part=part,
                part_number_snapshot=part_number,
                description_snapshot=part.description if part else "",
                book_value=book_value,
                map_price=map_price,
                variance_value=variance_value,
                abs_variance=abs_variance,
                count_records=item["count_val"],
                location_count=item["physical_location_count"],
                sub_location_count=item["sub_location_count"],
                tag_count=item["tag_count"],
                coverage_pct=0,
                selected_records=item["count_val"],
                selection_reason="High MAP Price",
                manual_override=0,
            )
        )

    # Single bulk create for all candidates
    if candidates_to_create:
        AuditCandidate.objects.bulk_create(candidates_to_create, batch_size=1000)
        link_candidates_to_audit_records(plan_ref, map_set, selection_reason="High MAP Price")

    return map_count_real
