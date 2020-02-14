# -*- coding: utf-8 -*-

# Do not use from, it would trick inspect
import md2workflow.validation as validation

def validate_global_section(config):
    errors = []
    if not config.has_section("global"):
        errors.append("Missing [global]. Sections %s" % config._sections)
    else:
        errors.extend(validation.allowed_section_keys(
            config["global"], allowed_keys=["backend",]))
        errors.extend(validation.required_section_keys(
            config["global"], required_keys=["backend",]))
    return errors

def validate_config_logging(config):
    errors = []
    if config.has_section("logging"):  # not a mandatory section
        errors.extend(validation.allowed_values(config["logging"], config["logging"]["level"],
                                                allowed_values=("DEBUG", "ERROR", "WARNING", "INFO",)))
        errors.extend(validation.allowed_section_keys(
            config["logging"], allowed_keys=["level", ]))
    return errors

def validate_backend_config(config):
    errors = []
    if config["global"]["backend"] == "redmine":
        import md2workflow.validation.redmine_validation as redmine_validation
        errors.extend(redmine_validation.validate_redmine_section(config))

    elif config["global"]["backend"] == "jira":
        import md2workflow.validation.jira_validation as jira_validation
        errors.extend(jira_validation.validate_jira_section(config))
    return errors
