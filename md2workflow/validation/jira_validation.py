# -*- coding: utf-8 -*-

# Do not use from, it would trick inspect
import md2workflow.validation as validation

allowed_jira_keys = [
                    "server", # https://jira.example.com
                    # cert is path to cert or None for insecure connection
                    "cert", # Path/to/cert
                    "auth", # basic
                    # A jira project where issues will be created
                    "project", # EXAMPLE

                    # These may differ per server, or at least SubTask
                    "mapping_JiraSubTask", # Sub-Task
                    "mapping_JiraTask", # Task
                    "mapping_JiraBasedWorkflow", # Epic
                    # Field where the Epic Name will be set (same as summary)
                    "mapping_EpicName", # Epic Name
                    # Field where the Epic Name should be queried
                    "mapping_EpicNameQuery", # Epic Link
                    # Ability to override assignee field
                    "mapping_Assignee", # e.g. Worker / GDPR
                    # Where to set [project] name. A must have for updates
                    "mapping_ProjectName", # Product
                    # This should be a giturl of the markdown files themselves. Used for relative links within markdown files
                    "relative_link_topurl", # https://github.com/lkocman/md2workflow/blob/master/example
                    "update_states", # Open, Backlog
                    "epic_update_states",  #Open, Backlog, In Progress
                ]
required_jira_keys = [
                    "server",
                    "auth",
                    "project",
                    "mapping_JiraSubTask",
                    "mapping_JiraTask",
                    "mapping_JiraBasedWorkflow",
                    "mapping_EpicName",
                    "mapping_EpicNameQuery",
                    "mapping_ProjectName",
                    "update_states",
                    "epic_update_states",
                ]

required_task_relations_keys = [
    "relations", # Blocs, Depends on, Impemented by ...
    #Jira internally tracks only one direction of relatione.g. Blocks -> Depends on
    # where Depends on is the inbound one
    "inbound", # Depends on, Implemented by
    ]
# All are mandatory
allowed_task_relations_keys = required_task_relations_keys

def validate_jira_section(config):
    errors = []
    if not config.has_section("jira"):
        errors.append("Missing [jira]. Sections %s" % config._sections)
    else:
        errors.extend(validation.allowed_section_keys(
            config["jira"], allowed_keys=allowed_jira_keys))
        errors.extend(validation.required_section_keys(
            config["jira"], required_keys=required_jira_keys))
    return errors


# Entries in TaskRelations define allowed values for JiraTaskRelations
# TaskRelations are the values used in Markdown, JiraTask relations are then
# mapping the MarkdownValue to eactual jira value.
# JIRA value might differ per jira instance within the same organization
def validate_task_relations_section(config):
    errors = []
    if not config.has_section("TaskRelations"):
        errors.append("Missing [TaskRelations]. Sections %s" % config._sections)
    else:
        errors.extend(validation.allowed_section_keys(
            config["TaskRelations"], allowed_keys=allowed_task_relations_keys))
        errors.extend(validation.required_section_keys(
            config["TaskRelations"], required_keys=required_task_relations_keys))
    return errors

def validate_jira_task_relations_section(config):
    errors = []
    if not config.has_section("JiraTaskRelations"):
        errors.append("Missing [JiraTaskRelations]. Sections %s" % config._sections)
    else:
        jira_task_relations_keys = config["TaskRelations"].keys()
        errors.extend(validation.allowed_section_keys(
            config["JiraTaskRelations"], allowed_keys=jira_task_relations_keys))
        errors.extend(validation.required_section_keys(
            config["JiraTaskRelations"], required_keys=jira_task_relations_keys))
    return errors
