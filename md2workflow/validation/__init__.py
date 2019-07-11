#!/usr/bin/env python

# -*- coding: utf-8 -*-


def allowed_section_keys(section, allowed_keys):
    """
    Args
        section (ConfigParser[section])
        allowed_keys(list)
    """
    errors = []
    for key in section:
        if key not in allowed_keys:
            errors.append("[%s] level has unknown key %s" % (section, key))
    return errors


def allowed_values(section, value, allowed_values):
    errors = []
    if value not in allowed_values:
        errors.append("[%s] unknown value %s" % (section, value))
    return errors
