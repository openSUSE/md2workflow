# -*- coding: utf-8 -*-


def allowed_section_keys(section, allowed_keys):
    """
    Args
        section (ConfigParser[section])
        allowed_keys(list)

    Returns list of errors (str) in case that section contains invalid keys
    """
    errors = []
    ak = [k.lower() for k in allowed_keys]
    for key in section:
        key=key.lower()
        if key not in ak:
            errors.append("[%s] section has unknown key %s" % (section.name, key))
    return errors

def allowed_values(section, value, allowed_values):
    """
    Args
        section (ConfigParser[section])
        value
        allowed_values(list)

    Returns list of errors (str) if section.attr contains invalid value
    """
    errors = []
    if value not in allowed_values:
        errors.append("[%s] unknown value %s" % (section.name, value))
    return errors

def required_section_keys(section, required_keys):
    """
    Args
        section (ConfigParser[section])
        required_keys(list)

    Returns list of errors (str) in case that section is missing certain keys
    """
    errors = []
    rk = [k.lower() for k in required_keys]
    for key in rk:
        key=key.lower()
        if key not in section:
            errors.append("[%s] attribute %s is required." % (section.name, key))
    return errors
