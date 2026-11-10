from django.template.defaulttags import register


@register.filter
def divide(value, arg):
    try:
        return int(float(value)) / int(float(arg))
    except (ValueError, ZeroDivisionError):
        return "-- --"


@register.filter
def int_divide(value, arg):
    try:
        return int(float(value)) // int(float(arg))
    except (ValueError, ZeroDivisionError):
        return "-- --"


@register.filter
def percentage_2_decimal(divisor, dividend):
    try:
        return f"{float(divisor) / float(dividend) * 100:.2f}%"
    except:
        return "-- --"


@register.filter
def remove_trailing_zeros(float_num):
    str_num = str(float_num).upper()

    if "0E" in str_num:
        return "0"
    if "N" in str_num:
        return "0"

    if len(str_num) == 0:
        return ""

    if "." in str_num:
        str_num = str_num.rstrip("0")
        if str_num[-1] == ".":
            return str_num[:-1]

        if str_num[-2] == ".":
            return str_num + "0"

    return str_num


@register.filter
def percentage(value, decimals=0):
    try:
        value = float(value) * 100
        return f"{value:.{int(decimals)}f}%"
    except (ValueError, TypeError):
        return ""


@register.filter
def multiply(value, arg):
    return float(value) * arg
