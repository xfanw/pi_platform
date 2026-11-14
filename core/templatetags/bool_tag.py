from django.template.defaulttags import register


@register.filter
def bool_to_text(val):
    if val:
        return "Yes"
    return "No"


@register.filter
def bool_to_yes(val):
    if val:
        return "<input class='form-control bg-success text-white fw-medium text-center' value='YES' readonly>"
    return "<input class='form-control bg-danger text-white fw-medium text-center' value='NO' readonly>"


@register.filter
def bool_to_yes_revert(val):
    if val:
        return "<input class='form-control bg-danger text-white fw-medium text-center' value='YES' readonly>"
    return "<input class='form-control bg-success text-white fw-medium text-center' value='NO' readonly>"


@register.filter
def bool_to_pass(val):
    if val:
        return "<input class='form-control bg-success text-white fw-medium text-center' value='PASS' readonly>"
    return "<input class='form-control bg-danger text-white fw-medium text-center' value='FAIL' readonly>"


@register.filter
def text_to_pass(val):
    if val == "PASS":
        return "<input class='form-control bg-success text-white fw-medium text-center' value='PASS' readonly>"
    elif val == "FAIL":
        return "<input class='form-control bg-danger text-white fw-medium text-center' value='FAIL' readonly>"
    else:
        return "<input class='form-control text-white fw-medium text-center' value='Pending' readonly>"
