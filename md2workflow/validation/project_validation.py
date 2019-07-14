# -*- coding: utf-8 -*-

# Do not use from, it would trick inspect
import md2workflow.validation as validation


def validate_project_section(config):
    errors = []
    if not config.has_section("project"):
        errors.append("Missing [project]. Sections %s" % config._sections)
    if config.has_section("project"):
        errors.extend(validation.allowed_section_keys(
            config["project"], allowed_keys=["name", ]))
    return errors
