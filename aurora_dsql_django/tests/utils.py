"""Shared test utilities for Aurora DSQL Django tests."""

import django
from django.db.models import CheckConstraint


# noinspection PyArgumentList
def create_check_constraint(condition, name):
    """Create CheckConstraint with Django version compatibility"""
    if django.VERSION >= (5, 0):
        return CheckConstraint(condition=condition, name=name)
    else:
        return CheckConstraint(check=condition, name=name)
