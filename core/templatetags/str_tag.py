from django.template.defaulttags import register


@register.filter
def contains(str_arg, substr_arg):
    if not str_arg:
        return False
    return substr_arg in str_arg
