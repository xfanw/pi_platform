import json

from django.template.defaulttags import register


@register.filter
def split(value, arg):
    return value.split(arg)


@register.filter
def pretty_val(val):
    if type(val) == str:
        return f'"{val}"'
    if type(val) == list:
        return json.dumps(val)
    return val


@register.filter
def get_bag_label_sub_set(val):
    if len(val) >= 4 and " of " in val[3]:
        return f"(Set {val[3].split(' of ')[0]})"

    return ""
