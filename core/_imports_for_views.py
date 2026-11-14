from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Case, Q, Value, When, F, Sum
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pprint import pprint
from access_control.app_functions import check_permission
from core.app_functions import *
from core.context_processors import get_basic_info


def info():

    build_in_func = [
        render,  # render HTML
        redirect,  # redirect to another HTML
        messages,  # show messages
        mark_safe,  # show messages, keep html format
        login_required,  # django security
    ]
    db_func = [Case, F, Q, Sum, Value, When]  # db functions
    datetime_func = [datetime, timedelta, ZoneInfo]  # datetime module
    print_func = [pprint]  # pprint

    # suppress warning
    _ = [build_in_func, db_func, datetime_func, print_func, check_permission, get_basic_info]
