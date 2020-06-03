# -*- coding: utf-8 -*-

# Do not use from, it would trick inspect
import md2workflow.validation as validation

allowed_keys = [
                    # lkocman's local redmine container setup, default port is 3000
                    "server",# http://redmine-example:3000
                    "auth", # basic
                    # default user password in the redmine container was admin/admin (min. req for pass is 8 char)
                    "user", # admin
                    "password", # admin
                    # We'll create subproject if project is defined
                    "parent", # identifier of parant process e.g. example
                    "is_project_public", #True
                ]
required_keys = [
                    "server",
                    "auth",
                    "user",
                    "password",
                    "parent",
                    "is_project_public",
                ]

def validate_redmine_section(config):
    errors = []
    if not config.has_section("redmine"):
        errors.append("Missing [redmine]. Sections %s" % config._sections)
    else:
        errors.extend(validation.allowed_section_keys(
            config["redmine"], allowed_keys=allowed_keys))
        errors.extend(validation.required_section_keys(
            config["redmine"], required_keys=required_keys))

    return errors
