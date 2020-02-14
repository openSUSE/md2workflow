# -*- coding: utf-8 -*-

# Do not use from, it would trick inspect
import md2workflow.validation as validation


def validate_project_section(config):
    errors = []
    if not config.has_section("project"):
        errors.append("Missing [project]. Sections %s" % config._sections)
    else:
        errors.extend(validation.allowed_section_keys(
            config["project"], allowed_keys=["name", "homepage", "identifier"]))
        errors.extend(validation.required_section_keys(
            config["project"], required_keys=["name",]))
    return errors
