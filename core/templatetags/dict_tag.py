from collections import defaultdict

from django.template.defaulttags import register


@register.filter
def pop(my_dict, key):
    if type(my_dict) is dict:
        return my_dict.pop(key, "")
    return ""


@register.filter
def get(my_dict, key):
    if type(my_dict) is dict or type(my_dict) is defaultdict:
        return my_dict.get(key, "")
    return ""


@register.filter
def strf_dict(my_dict_str):
    try:
        my_dict = eval(my_dict_str)
        result = []
        for key, val in my_dict.items():
            if type(val) is list:
                result.append(f'{key}: {", ".join(val)}')
            else:
                result.append(f"{key}: {val}")
        return "; ".join(result)
    except Exception as e:
        return "-- --"


@register.filter
def strf_dict_key(my_dict_str):
    try:
        return ", ".join(eval(my_dict_str).keys())
    except Exception as e:
        return "-- --"



