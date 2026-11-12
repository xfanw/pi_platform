from count.models import CycleTagDetail


def create_tag_range_detail(tag_range):
    CycleTagDetail.objects.filter(tag_range=tag_range).delete()
    cycle_tag_detail = []
    for tag_number in range(int(tag_range.start_number), int(tag_range.end_number) + 1):
        cycle_tag_detail.append(
            CycleTagDetail(
                tag_range=tag_range,
                tag_number=tag_number,
                count_record=None,
                is_counted=False,
            )
        )
    CycleTagDetail.objects.bulk_create(cycle_tag_detail)
