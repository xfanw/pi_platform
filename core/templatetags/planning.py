# planning/templatetags/planning_extras.py
"""
Custom template tags and filters for the planning module
"""
from django.template.defaulttags import register


@register.filter(name="dict_get")
def dict_get(dictionary, key):
    """
    Template filter to get value from dictionary by key
    Usage: {{ my_dict|dict_get:key_variable }}

    Args:
        dictionary: Dictionary to look up
        key: Key to retrieve

    Returns:
        Value from dictionary or None if not found
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter(name="call")
def call_method(obj, arg):
    """
    Template filter to call a method with an argument
    Usage: {{ handler.render_row_data|call:obj }}

    Args:
        obj: Object with method to call
        arg: Argument to pass to the method

    Returns:
        Result of method call
    """
    if callable(obj):
        return obj(arg)
    return None


@register.filter(name="has_feature")
def has_feature(handler, feature_name):
    """
    Template filter to check if a handler supports a feature
    Usage: {{ handler|has_feature:'planner_notes' }}

    Args:
        handler: Plan handler object
        feature_name: Name of the feature to check

    Returns:
        Boolean indicating if feature is supported
    """
    method_name = f"supports_{feature_name}"
    if hasattr(handler, method_name):
        method = getattr(handler, method_name)
        if callable(method):
            return method()
    return False


@register.filter(name="get_plan_count")
def get_plan_count(plan_counts, plan_type):
    """
    Template filter to get count for a specific plan type
    Usage: {{ plan_counts|get_plan_count:'consumable' }}

    Args:
        plan_counts: Dictionary of plan type counts
        plan_type: Plan type key

    Returns:
        Count as integer, 0 if not found
    """
    if isinstance(plan_counts, dict):
        return plan_counts.get(plan_type, 0)
    return 0


@register.simple_tag
def query_string(request, **kwargs):
    """
    Template tag to build query strings while preserving existing parameters
    Usage: {% query_string request page_num=2 filter='hot_otd' %}

    Args:
        request: Django request object
        **kwargs: Parameters to add/update

    Returns:
        Query string with updated parameters
    """
    query_dict = request.GET.copy()

    for key, value in kwargs.items():
        if value is None or value == "":
            # Remove parameter if value is None or empty string
            query_dict.pop(key, None)
        else:
            query_dict[key] = value

    query_string = query_dict.urlencode()
    return f"?{query_string}" if query_string else ""


@register.inclusion_tag("planning/shoporder_management/pagination.html")
def render_pagination(page_obj, plan_type, **kwargs):
    """
    Inclusion tag for rendering pagination controls
    Usage: {% render_pagination page_obj plan_type search_date=search_date %}

    Args:
        page_obj: Django paginator page object
        plan_type: Current plan type
        **kwargs: Additional query parameters to preserve

    Returns:
        Context for pagination template
    """
    return {
        "page_obj": page_obj,
        "plan_type": plan_type,
        "query_params": kwargs,
    }


@register.filter(name="status_badge_class")
def status_badge_class(status, plan_type="consumable"):
    """
    Template filter to get Bootstrap badge class for a status
    Usage: {{ status|status_badge_class:plan_type }}

    Args:
        status: Status value
        plan_type: Type of plan (for type-specific mappings)

    Returns:
        Bootstrap class string (e.g., 'bg-success')
    """
    # Default mapping
    status_map = {
        "pending": "secondary",
        "in_progress": "warning",
        "completed": "success",
        "failed": "danger",
        "cancelled": "dark",
    }

    # Plan-specific mappings
    if plan_type == "vialwash":
        status_map = {
            0: "secondary",  # Start
            1: "warning",  # In Process
            2: "info",  # QC Finish
            -1: "success",  # Finished
        }

    return f'bg-{status_map.get(status, "secondary")}'


@register.filter(name="truncate_list")
def truncate_list(value, max_items=3):
    """
    Template filter to truncate a list and show "... X more" if needed
    Usage: {{ my_list|truncate_list:3 }}

    Args:
        value: List or iterable to truncate
        max_items: Maximum number of items to show

    Returns:
        String representation of truncated list
    """
    if not value:
        return ""

    try:
        items = list(value)
        if len(items) <= max_items:
            return ", ".join(str(item) for item in items)
        else:
            visible = ", ".join(str(item) for item in items[:max_items])
            remaining = len(items) - max_items
            return f"{visible} ... ({remaining} more)"
    except (TypeError, ValueError):
        return str(value)


@register.filter(name="format_shop_order")
def format_shop_order(value):
    """
    Template filter to format shop order numbers consistently
    Usage: {{ shop_order|format_shop_order }}

    Args:
        value: Shop order string

    Returns:
        Formatted shop order string
    """
    if not value:
        return "_"

    # Add any specific formatting rules here
    # For example, uppercase, add dashes, etc.
    return str(value).upper()


@register.filter(name="priority_label")
def priority_label(obj):
    """
    Template filter to get priority label for an order
    Usage: {{ order|priority_label }}

    Args:
        obj: Order object

    Returns:
        Priority label string ('HOT', 'OTD', 'NORMAL', or None)
    """
    if not obj:
        return None

    if hasattr(obj, "hot") and obj.hot:
        return "HOT"
    elif hasattr(obj, "otd") and obj.otd:
        return "OTD"
    else:
        return "NORMAL"


@register.filter(name="priority_badge_class")
def priority_badge_class(obj):
    """
    Template filter to get Bootstrap badge class for priority
    Usage: {{ order|priority_badge_class }}

    Args:
        obj: Order object

    Returns:
        Bootstrap class string
    """
    label = priority_label(obj)

    class_map = {
        "HOT": "bg-danger",
        "OTD": "bg-warning",
        "NORMAL": "bg-secondary",
    }

    return class_map.get(label, "bg-secondary")


@register.simple_tag
def get_handler_feature(handler, feature_name):
    """
    Template tag to get a feature support status from handler
    Usage: {% get_handler_feature handler 'planner_notes' as supports_notes %}

    Args:
        handler: Plan handler object
        feature_name: Name of the feature to check

    Returns:
        Boolean indicating if feature is supported
    """
    return has_feature(handler, feature_name)
