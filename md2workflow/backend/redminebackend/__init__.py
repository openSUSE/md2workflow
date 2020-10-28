# -*- coding: utf-8 -*-

import codecs
import os
import getpass
import sys

from redminelib import Redmine, exceptions

import md2workflow.workflow as workflow
import md2workflow.markdown as markdown
import md2workflow.schedule as schedule

from md2workflow.cli import get_md_abspath
from md2workflow.cli import CliAction


user_cache = {}

def str_to_bool(value):
    return True if value.lower() == 'true' else False

class RedmineSubTask(workflow.GenericTask):
    def __init__(self, summary, client_session=None, description="",
                    environment=None, conf=None):
        super(RedmineSubTask, self).__init__(
            summary, description, environment, conf)
        self.client_session = client_session
        self._redmine = None
        self._published = False
        self.action = CliAction.CREATE # default
        self._updatable = None

    def set_action(self, action):
        if action not in (CliAction.CREATE, CliAction.UPDATE):
            raise ValueError(
                "%s: unsupported action %s" % (self.__class__.__name__, action))
        self.action = action

    def _save_redmine(self):
        try:
            self._redmine.save()
            self._published = True
        # either issue exists or e.g. invalid user   which is e.g. missing role in a project
        except exceptions.ValidationError:
            self.logger.error("Failed to assign user %s" % self.owner)
            raise
        except exceptions.ForbiddenError:
            self.logger.error("Unauthorized to create project %s. " \
            "Is Redmine API enabled? Do you have role with permission to create project?" % self.summary)
            raise

    @property
    def summary(self):
        return self._summary[:59] # 60 is the limit, let's store full string internally, so it can still be accessed

    @summary.setter
    def summary(self, text):
        self._summary = text or ""  # Make sure there is not None


    @property
    def owner(self):
        ownr = super(RedmineSubTask, self).owner
        if not ownr:
            return None

        self.logger.debug("Looking up redmine owner id for user %s" % ownr)
        if ownr not in user_cache:
            res = self.client_session.user.filter(name=ownr)
            if not res:
                self.logger.warning("User %s not found." % ownr)
                return None

            assert len(res) == 1, "Multiple users found for name %s" % ownr
            user_cache[ownr] = int(res[0].id)


        self.logger.debug("Identified id=%d for user %s." % (user_cache[ownr], ownr))
        return user_cache[ownr]

    def publish(self, force_publish=False):
        if self._published: # Idempotency
            return

        self._redmine = self.client_session.issue.new()
        self._redmine.subject = self.summary
        self._redmine.description = self.description

        # our parent task is RedmineTask
        self._redmine.parent_issue_id = self.parent_task._redmine.id #

        # take it from the most upper level
        # sub-task -> task -> target_version -> project.id
        self._redmine.project_id = self.parent_task.parent_task.parent_task._redmine.id

        # parent's parent is target_version
        self._redmine.fixed_version_id = self.parent_task.  parent_task._redmine.id

        if self.owner:
            self._redmine.assigned_to_id = self.owner

        if self.calendar_entry:
            self._redmine.start_date = self.calendar_entry[0]
            self._redmine.due_date = self.calendar_entry[1]

        self._save_redmine()

    @property
    def description(self):
        res = self._description.strip()
        res = res.replace("${Project}", self.conf["project"]["name"])
        res = res.replace("${Product}", self.conf["project"]["name"])

        if self.parent_by_subclass(RedmineBasedWorkflow):
            target_version = str(self.parent_by_subclass(
                RedmineBasedWorkflow).summary)
            res = res.replace("${Epic}", target_version)
            res = res.replace("${Milestone}", target_version)

        # bold and links should be fine
        # TODO: support url refrences to the git repo
        return res

    @description.setter
    def description(self, value):
        self._description = value

class RedmineTask(RedmineSubTask, workflow.GenericNestedTask):
    def publish(self, force_publish=False):
        if self._published: # Idempotency
            return
        self._redmine = self.client_session.issue.new()
        self._redmine.subject = self.summary
        self._redmine.description = self.description

        # our parent would be a version, so let's go for parent of the version
        #self._redmine.fixed_version_id = self.parent_task._redmine.id
        #self._redmine.parent = self.parent_task.parent_task._redmine.id
        self._redmine.project_id = self.parent_task.parent_task._redmine.id

        # parent is target_version
        self._redmine.fixed_version_id = self.parent_task._redmine.id
        # Following save requires Issue states, Issue Workflow and Issue Tracker
        # to be set up manually. Unfortunatelly this can't be done over API
        # However we can inherit it from the parent project.
        # Users using fresh redmine container without configuration need to
        # pre-configure the instance
        # https://python-redmine.com/resources/tracker.html

        # XXX: I see that some issues are multiplied perhaps we have to check
        # Whether the issue was already published or not.

        if self.owner:
            self._redmine.assigned_to_id = self.owner

        if self.calendar_entry:
            self._redmine.start_date = self.calendar_entry[0]
            self._redmine.due_date = self.calendar_entry[1]

        self._save_redmine()

    @property
    def task_class(self):
        return RedmineSubTask

    def new_task(self, **kwargs):
        """
        Returns a new instance of class returned by task_class()
        """
        return self.task_class(client_session=self.client_session, environment=self.environment, conf=self.conf, **kwargs)


    def add_task(self, task):
        """
        Args
            task (RedmineSubTask instance)

        Make sure to publish new Redmine Version (our Workflow)
        on creation.
        """
        task.action = self.action # Make sure that tasks knows Update/Create
        task.parent_task = self
        task.logger = self.logger
        super(RedmineTask, self).add_task(task)


class RedmineBasedWorkflow(RedmineTask, workflow.GenericWorkflow):
    """
    Redmine version representation of our Workflow (e.g. EPIC in others)
    """

    @property
    def task_class(self):
        return RedmineTask

    def publish(self, force_publish=False):
        if self._published: # Idempotency
            return
        if self.action == CliAction.UPDATE:
            all_versions = self.parent_task._redmine.versions
            for ver in all_versions:
                if ver.name == self.summary:
                    self._redmine = self.client_session.version.get(ver.id)
                    break

        # Not --update, or the version was simply not created yet e.g. brand new one
        if not self._redmine:
            self._redmine = self.client_session.version.new()
            self._redmine.project_id = self.parent_task._redmine.id
            self._redmine.name = self.summary
            self._redmine.status = 'open'
            self._redmine.sharing = 'none'
            #self._redmine.due_date = datetime.date(2014, 1, 30) # TODO Issue #17
            self._redmine.description = self.description
            self._redmine.wiki_page_title = self.summary

            if self.calendar_entry:
                # Only due date for Target version
                self._redmine.due_date = self.calendar_entry[1]

            self._save_redmine()
            self.logger.debug("New Redmine version (workflow) create id=%s" % self._redmine.id)


        self._published = True # for Update in case that target_version already existed

        def publish_task_relation(self, relation):
            self.logger.debug("redmine: relations are not supported.")
            # TODO: write a task comment or a custom field?

class RedmineBasedProject(RedmineBasedWorkflow, workflow.GenericProject):
    """
    Redmine project representation of our Workflow Project
    """

    @property
    def task_class(self):
        return RedmineBasedWorkflow

    def new_task(self, **kwargs):
        """
        Returns a new instance of class returned by task_class()
        """
        return self.task_class(client_session=self.client_session, environment=self.environment, conf=self.conf, **kwargs)


    def add_task(self, task):
        """
        Args
            task (RedmineSubTask instance)

        Make sure to publish new Redmine Version (our Workflow)
        on creation.
        """
        task.action = self.action # Make sure that tasks knows Update/Create
        task.parent_task = self
        task.logger = self.logger
        super(RedmineBasedWorkflow, self).add_task(task)
        task.publish() # there is nothing to wait for no pending task relations etc.

    def publish(self, force_publish=False):
        if self._published: # Idempotency
            return
        # Let's refer to all issue/project redmine representations as _redmnie in every class
        if self.action == CliAction.UPDATE:
            self.logger.debug("Update: Looking up Redmine project %s" % self.conf["project"]["identifier"])
            self._redmine = self.client_session.project.get(self.conf["project"]["identifier"])
            self.logger.debug("Update: Found Redmine project=%s id=%s" % (self._redmine, self._redmine.id))
            return

        self._redmine = self.client_session.project.new()
        self._redmine.name = self.summary
        self._redmine.identifier =  self.conf["project"]["identifier"]
        self._redmine.description = self.description
        self._redmine.is_public = str_to_bool(self.environment["redmine"]["is_project_public"])
        self._redmine.inherit_members = True

        # XXX: parent was not set
        if "parent" in self.environment["redmine"]:
            parent_id = self.environment["redmine"]["parent"]

            self.logger.debug("Looking up Redmine parent project %s" % parent_id)
            try:
                parent = self.client_session.project.get(parent_id)
                self._redmine.parent_id = parent.id
                self.logger.debug("Found Redmine parent project=%s id=%s" % (parent, parent.id))
            except exceptions.ResourceNotFoundError as e:
                self.logger.error("Could not find Redmine parent project=%s" % parent_id)
                raise e

        if "homepage" in self.conf["project"]:
            self._redmine.homepage=self.conf.get("project", "homepage")

        # Publish
        self._save_redmine()

    def client_session_from_env(self):
        """
        This will be inherited to every added child task and it's child task ...
        """
        if self.client_session:
            return
        server = self.environment["redmine"]["server"]

        # use value passed by user if mapping is not found
        if self.environment["redmine"]["auth"] == "apikey":
            key = None
            if "apikey" in self.environment["redmine"]:
                key = self.environment["redmine"]["apikey"]
            else:
                key = getpass.getpass("Please enter apikey")
            self.logger.debug("Creating redmine session with apikey for %s" % (server))
            self.client_session = Redmine(server, key=key)

        elif self.environment["redmine"]["auth"] == "basic":
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
            elif "apikey" in self.environment["redmine"]:
                pass
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
    project.schedule = schedule.ProjectSchedule()
    if "schedule" in project.conf:
        # relpath has to be handled for non-url entries
        url = project.conf["schedule"]["calendar_url"]
        if not (url.startswith("https://") or url.startswith("http://")):
            url = get_md_abspath(cli.project_path, url)
        cli.logger.info("Using calendar: %s" % url)
        project.schedule.from_url(url)
    project.client_session_from_env()
    project.set_action(cli.action)
    project.publish() # let's create redmine (sub) project

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
            project.publish_task_relation()

    return True  # for testing purposes
