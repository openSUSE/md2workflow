# -*- coding: utf-8 -*-

import codecs
import os
import getpass
import sys

import md2workflow.workflow as workflow
import md2workflow.markdown as markdown

from md2workflow.cli import get_md_abspath


def handle_project(cli):
    """
    Args:
        cli (Cli) - an object representing execution environment
    """
    cli.logger.info(
        "Using GenericBackend. No changes will be commited to server")
    project = workflow.GenericProject(
        summary=cli.project_conf["project"]["name"], environment=cli.environment, conf=cli.project_conf)
    project.logger = cli.logger
    project.conf = cli.project_conf

    for workflow_section in project.conf.sections():  # Workflow as in Milestone (e.g Beta) or Epic
        # these are not milestone sections
        if workflow_section in ('project', 'ownership'):
            continue

        # this can be skipped for handling virtual milestones such as Public Beta,
        # where the only purpose is to have a separate set of Milestone Tasks
        # which are named differently
        if 'markdown_filename' in project.conf[workflow_section]:
            # section represents e.g. milestone1, order is important due Blocks/Depends On
            project_relpath = project.conf[workflow_section]['markdown_filename']
            md_path = get_md_abspath(cli.project_path, project_relpath)

            cli.logger.debug("Processing %s" % md_path)
            if not os.path.exists(md_path):
                cli.logger.error("Referenced filename doesn't exist! relpath: %s abspath: %s" % (
                    project_relpath, md_path))
                sys.exit(3)

            fd = codecs.open(md_path, encoding='utf-8')
            md = markdown.MarkDown()
            md.logger = cli.logger
            md.read(fd)
            project.from_markdown(md, override_workflow_name=workflow_section)
            project.relations_from_conf_section(project.conf, workflow_section)

    return True  # for testing purposes
