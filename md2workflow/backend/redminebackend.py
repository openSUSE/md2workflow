# -*- coding: utf-8 -*-

import codecs
import os
import getpass
import sys

import md2workflow.workflow as workflow
import md2workflow.markdown as markdown

from md2workflow.cli import get_md_abspath
from redminelib import Redmine


class RedmineSubtask(workflow.GenericTask):
    def __init__(self, summary, client_session=None, description="", environment=None, conf=None):
        super(RedmineSubtask, self).__init__(
            summary, description, environment, conf)
        self.client_session = client_session
        self._published = False
        self._issue = None
        self._updatable = None

class RedmineTask(RedmineSubtask, workflow.GenericNestedTask):
    pass # Hackweek19 subject

class RedmineBasedWorkflow(RedmineTask, workflow.GenericWorkflow):
    pass # Hackweek19 subject

class RedmineBasedProject(RedmineBasedWorkflow, workflow.GenericProject):
    def client_session_from_env(self):
        """
        This will be inherited to every added child task and it's child task ...
        """
        if self.client_session:
            return
        server = self.environment["redmine"]["server"]

        # use value passed by user if mapping is not found
        if self.environment["redmine"]["auth"] == "basic":
            user = None
            if "user" in self.environment["redmine"]:
                user = self.environment["redmine"]["user"]
            else:
                try:
                    user = raw_input("Redmine user for %s: " % server)
                except NameError:
                    user = input("Redmine user for %s: " % server)
            password = None
            if "password" in self.environment["redmine"]:
                password = self.environment["redmine"]["password"]
            else:
                password = getpass.getpass(
                    "Password of Redmine user %s for %s: " % (user, server))
            self.logger.debug("Creating redmine session %s@%s" % (user, server))
            self.client_session = Redmine(
                                                server,
                                                username=user,
                                                password=password)
        else:
            raise NotImplementedError("Authentication type '%s' is not implemented." % \
                                        self.environment["redmine"]["auth"])


def handle_project(cli):
    """
    Args:
        cli (Cli) - an object representing execution environment
    """
    server = cli.environment["redmine"]["server"]
    cli.logger.info(
        "Using Redmine Backend. Redmine Server is %s. Changes will be commited." % server)
    project = RedmineBasedProject(
        summary=cli.project_conf["project"]["name"], environment=cli.environment, conf=cli.project_conf)
    project.logger = cli.logger
    project.conf = cli.project_conf
    project.client_session_from_env()

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
