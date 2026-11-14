from django.template.defaulttags import register


@register.filter
def eleindex(list, index):
    return list[index]


@register.filter
def strf_list(my_list_str):
    try:
        return ", ".join(eval(my_list_str))
    except Exception as e:
        return "-- --"


@register.filter
def in_list(value, the_list):
    return value in the_list
