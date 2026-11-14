def add_tag_info(tag_ref, count_ref, user_ref, *, ex_part_ref=None):
    tag_ref.count_record = count_ref
    tag_ref.exception_record = ex_part_ref
    tag_ref.is_counted = True
    tag_ref.updated_by = user_ref
    tag_ref.save()
