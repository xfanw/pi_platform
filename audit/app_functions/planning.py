from django.db.models import Q

from audit.models import AuditCandidate, AuditRecord
from django.db import transaction

from count.models import CycleTagDetail
from variance.models import CycleVariance


def generate_audit_records(audit_plan, count_records, curr_user):
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
                created_by=curr_user,
                page_number=0,
            )
        )

    # Bulk create with batching to manage memory for large datasets
    if audit_records_to_create:
        record_set = AuditRecord.objects.bulk_create(audit_records_to_create, batch_size=1000)
    else:
        record_set = []

    return record_set


def init_candidates(audit_plan, curr_user):
    """
    Initialize audit candidates from audit records.

    Leverages the existing variance foreign key on AuditRecord to:
    - Fetch all audit records with their variance in one query
    - Group in-memory by variance (no additional queries)
    - Create one candidate per unique variance
    - Link audit records to candidates in bulk
    """
    # Fetch all audit records with their related variance in a single query
    audit_records = list(audit_plan.records.select_related("variance", "variance__part", "variance__sap_location").all())

    # Group audit records by variance, counting them in-memory
    variance_groups = {}
    for record in audit_records:
        if record.variance:
            if record.variance.id not in variance_groups:
                variance_groups[record.variance.id] = {"variance": record.variance, "records": []}
            variance_groups[record.variance.id]["records"].append(record)

    # Create candidates from variance groups
    candidates_to_create = []
    for var_data in variance_groups.values():
        var_ref = var_data["variance"]
        part_ref = var_ref.part
        record_count = len(var_data["records"])

        candidates_to_create.append(
            AuditCandidate(
                plan=audit_plan,
                sap_location=var_ref.sap_location,
                variance_record=var_ref,
                part=part_ref,
                part_number_snapshot=part_ref.part_number,
                description_snapshot=part_ref.description,
                book_value=var_ref.sap_quantity * var_ref.map_price,
                map_price=var_ref.map_price,
                variance_value=var_ref.variance_value,
                abs_variance=abs(var_ref.variance_value),
                count_records=record_count,
                location_count=AuditRecord.objects.filter(variance=var_ref).values("physical_location_snapshot").distinct().count(),
                sub_location_count=AuditRecord.objects.filter(variance=var_ref).values("sub_location_snapshot").distinct().count(),
                tag_count=AuditRecord.objects.filter(variance=var_ref).values("tag_snapshot").distinct().count(),
                created_by=curr_user,
                coverage_pct=0,
            )
        )

    if candidates_to_create:
        candidate_set = AuditCandidate.objects.bulk_create(candidates_to_create, batch_size=1000)

        # Map variance IDs to created candidates
        variance_id_to_candidate = {}
        for candidate in candidate_set:
            variance_id_to_candidate[candidate.variance_record_id] = candidate

        # Link audit records to their candidates
        for record in audit_records:
            if record.variance and record.variance.id in variance_id_to_candidate:
                record.candidate = variance_id_to_candidate[record.variance.id]

        AuditRecord.objects.bulk_update(audit_records, ["candidate"], batch_size=1000)


@transaction.atomic
def regenerate_candidates(plan_ref, curr_user):
    target_count = plan_ref.target_count
    top_80_target = int(target_count * plan_ref.value_pct / 100)
    # TODO:
    # Top 80% is calculated separately for each SAP Location and part_number. ignore count_quantity = 0
    # Lines are sorted by positive Book Value * book inventory, highest first.
    # if top 80% count >= target_count, stop selecting 85% from the top 80% candidates for that SAP Location and part_number.
    # else select all top 80% candidates
    # after top_80 record selection, continue selecting from the remaining candidates based on High Value and High Abs Variance until target_count is reached.
    top_80_count_real, small_audit = generate_top_80_candidates(plan_ref, target_count, top_80_target, curr_user)

    if small_audit:
        # Variance and MAP > 100
        top_variance_target = min(target_count - top_80_count_real, int(target_count * plan_ref.variance_pct / 100))
        real_top_variance_count = generate_top_variance_candidates(plan_ref, top_variance_target, curr_user)
        # MAP
        top_map_target = min(target_count - top_80_count_real - real_top_variance_count, int(target_count * plan_ref.map_pct / 100))
        real_top_map_count = generate_top_map_candidates(plan_ref, top_map_target, curr_user)

        plan_ref.real_top_80_count = top_80_count_real
        plan_ref.real_variance_count = real_top_variance_count
        plan_ref.real_map_count = real_top_map_count
        plan_ref.real_total_count = top_80_count_real + real_top_variance_count + real_top_map_count
        plan_ref.save()
    else:
        # 10% MAP
        top_map_target = min(target_count - top_80_count_real, int(target_count * plan_ref.map_pct / 100))
        real_top_map_count = generate_top_map_candidates(plan_ref, top_map_target, curr_user)
        # 5% of abs variance
        top_variance_target = min(
            target_count - top_80_count_real - real_top_map_count, int(target_count * plan_ref.variance_pct / 100)
        )
        real_top_variance_count = generate_top_variance_candidates(plan_ref, top_variance_target, curr_user)

        plan_ref.real_top_80_count = top_80_count_real
        plan_ref.real_variance_count = real_top_variance_count
        plan_ref.real_map_count = real_top_map_count
        plan_ref.real_total_count = top_80_count_real + real_top_variance_count + real_top_map_count
        plan_ref.save()


def generate_top_80_candidates(plan_ref, target_count, top_80_target, curr_user):
    candidate_set = AuditCandidate.objects.filter(plan=plan_ref, records__selected=False).distinct().order_by("-book_value")

    if not candidate_set:
        return 0, False

    top_80_count_real = sum(item.count_records for item in candidate_set)
    book_set = []
    small_audit = False
    partial_selected = None
    partial_count = 0
    if top_80_count_real >= target_count:
        temp_sum = 0

        for item in candidate_set:
            if temp_sum >= top_80_target:
                break
            partial_selected = item
            partial_count = min(item.count_records, top_80_target - temp_sum)
            item.selected_records = partial_count
            item.updated_by = curr_user
            item.selection_reason += "Top 80% Value"
            item.coverage_pct = 100
            book_set.append(item)
            temp_sum += partial_count

        top_80_count_real = temp_sum
    else:
        book_set = candidate_set
        for item in book_set:
            item.selected_records = item.count_records
            item.updated_by = curr_user
            item.coverage_pct = 100
            item.selection_reason += "Top 80% Value"
        small_audit = True
    AuditCandidate.objects.bulk_update(book_set, ["selected_records", "updated_by", "selection_reason", "coverage_pct"])
    # Batch update selected records
    if book_set:
        # Build Q filter for all book_set items
        q_filter = Q()
        for item in book_set:
            q_filter |= Q(sap_location_code=item.sap_location.code, part_number_snapshot=item.part_number_snapshot)

        # Single bulk update
        AuditRecord.objects.filter(q_filter).update(selected=True)

    if partial_selected:
        partial_selected.refresh_from_db()
        partial_selected.coverage_pct = partial_count / partial_selected.count_records * 100
        partial_selected.save()
        unselect_count = partial_selected.count_records - partial_count
        if unselect_count:
            update_set = AuditRecord.objects.filter(candidate=partial_selected).order_by("-count_quantity_snapshot", "id")[
                partial_count:
            ]
            for record in update_set:
                record.selected = False
            AuditRecord.objects.bulk_update(update_set, ["selected"])

    return top_80_count_real, small_audit


def generate_top_variance_candidates(plan_ref, top_variance_target, curr_user):
    candidate_set = AuditCandidate.objects.filter(plan=plan_ref, records__selected=False).distinct().order_by("-abs_variance")

    if not candidate_set:
        return 0

    variance_count_real = sum(item.count_records for item in candidate_set)
    variance_set = []

    # Select candidates until reaching top_variance_target
    temp_sum = 0
    partial_selected = None
    partial_count = 0
    for item in candidate_set:
        if temp_sum >= top_variance_target:
            break
        partial_count = min(item.count_records, top_variance_target - temp_sum)
        variance_set.append(item)
        temp_sum += partial_count
        item.selected_records = partial_count
        item.coverage_pct = 100

        partial_selected = item
        item.selection_reason += "High Abs Variance"
        item.updated_by = curr_user

    variance_count_real = temp_sum
    AuditCandidate.objects.bulk_update(variance_set, ["selected_records", "selection_reason", "updated_by", "coverage_pct"])
    # Batch update selected records

    q_filter = Q()
    for item in variance_set:
        q_filter |= Q(sap_location_code=item.sap_location.code, part_number_snapshot=item.part_number_snapshot)

    # Single bulk update
    AuditRecord.objects.filter(q_filter).update(selected=True)

    if partial_selected:
        partial_selected.refresh_from_db()
        unselect_count = partial_selected.count_records - partial_count
        partial_selected.coverage_pct = partial_count / partial_selected.count_records * 100
        partial_selected.save()
        if unselect_count:
            update_set = AuditRecord.objects.filter(candidate=partial_selected).order_by("-count_quantity_snapshot")[partial_count:]
            for record in update_set:
                record.selected = False
            AuditRecord.objects.bulk_update(update_set, ["selected"])

    return variance_count_real


def generate_top_map_candidates(plan_ref, top_map_target, curr_user):
    candidate_set = AuditCandidate.objects.filter(plan=plan_ref, records__selected=False).distinct().order_by("-map_price")

    if not candidate_set:
        return 0

    map_count_real = sum(item.count_records for item in candidate_set)
    map_set = []

    # Select candidates until reaching top_map_target
    temp_sum = 0
    partial_selected = None
    partial_count = 0
    for item in candidate_set:
        if temp_sum >= top_map_target:
            break
        partial_count = min(item.count_records, top_map_target - temp_sum)
        item.selected_records = partial_count
        map_set.append(item)
        temp_sum += partial_count
        partial_selected = item
        item.coverage_pct = 100
        item.selection_reason += "High Value"
        item.updated_by = curr_user
    map_count_real = temp_sum

    AuditCandidate.objects.bulk_update(map_set, ["selected_records", "selection_reason", "updated_by", "coverage_pct"])

    q_filter = Q()
    for item in map_set:
        q_filter |= Q(sap_location_code=item.sap_location.code, part_number_snapshot=item.part_number_snapshot)
    AuditRecord.objects.filter(q_filter).update(selected=True)

    if partial_selected:
        partial_selected.refresh_from_db()
        unselect_count = partial_selected.count_records - partial_count
        partial_selected.coverage_pct = partial_count / partial_selected.count_records * 100
        partial_selected.save()
        if unselect_count:
            update_set = AuditRecord.objects.filter(candidate=partial_selected).order_by("-count_quantity_snapshot")[partial_count:]
            for record in update_set:
                record.selected = False
            AuditRecord.objects.bulk_update(update_set, ["selected"])
    return map_count_real
