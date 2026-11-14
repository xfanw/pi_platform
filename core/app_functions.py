from datetime import datetime

from django.http import JsonResponse, HttpResponse


def json_msg(status, msg, **kwargs):
    """Json Message

    Args:
        status: 'error' or 'success
        msg: message

    Returns:
        JsonResponse:  'status': status + msg
    """
    return JsonResponse({"status": status, "msg": msg})


def json_error(msg, **kwargs):
    """Json Error

    Args:
        msg: error message

    Returns:
        JsonResponse: 'status':'error' + msg
    """
    return JsonResponse({"status": "error", "msg": msg, **kwargs})


def json_success(msg="", **kwargs):
    """Json Success

    Args:
        msg (optional): success message. Defaults to ''.

    Returns:
        JsonResponse:  'status': 'success' + msg
    """
    return JsonResponse({"status": "success", "msg": msg, **kwargs})


def json_warning(msg, **kwargs):
    """Json Success

    Args:
        msg (optional): warning message. Defaults to ''.

    Returns:
        JsonResponse:  'status': 'warning' + msg
    """
    return JsonResponse({"status": "warning", "msg": msg, **kwargs})


def form_errors(form):
    error_msg = [error for field in form for error in field.errors]
    return error_msg
    return "<br>".join(
        f"{form.fields[field].label if field in form.fields else 'Form'}: {error}"
        for field, errors in form.errors.items()
        for error in errors
    )


def clean_errors(error_msg):
    return str(error_msg).replace("\n", " ").replace("\r", "").strip()


def http_excel(file, file_name):
    file_name = file_name.replace(" ", "_")
    time_tag = datetime.now().strftime("%y%m%d%H%M%S")
    response = HttpResponse(file, content_type=("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
    response["Content-Disposition"] = f'attachment; filename="{file_name}_{time_tag}.xlsx"'
    return response


def query_to_dict(query_set, key_field):
    return_dict = {}
    for query_ref in query_set:
        if key_field in query_ref:
            key_value = query_ref.pop(key_field)
            return_dict[key_value] = query_ref
    return return_dict


def swap_dict_key_value(original_dict):
    inverted_dict = {}
    for key, value in original_dict.items():
        inverted_dict.setdefault(value, []).append(key)
    return inverted_dict
