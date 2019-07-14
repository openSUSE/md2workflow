# -*- coding: utf-8 -*-

# Do not use from, it would trick inspect
import md2workflow.validation as validation


def validate_config_logging(config):
    errors = []
    if config.has_section("logging"):  # not a mandatory section
        errors.extend(validation.allowed_values(config["logging"], config["logging"]["level"],
                                                allowed_values=("DEBUG", "ERROR", "WARNING", "INFO",)))
        errors.extend(validation.allowed_section_keys(
            config["logging"], allowed_keys=["level", ]))
    return errors
