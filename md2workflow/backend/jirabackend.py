# -*- coding: utf-8 -*-

import codecs
import os
import getpass
import re
import sys

import jira  # python-jira, also the only reason why this file is called jirabackend.py
try:
    import simplejson as json
except ImportError:
    import json
import md2workflow.workflow as workflow
import md2workflow.markdown as markdown

from md2workflow.cli import get_md_abspath
from configparser import ConfigParser

from md2workflow.cli import CliAction, EXAMPLE_DIR

# cache to optmize behavior, as it's expected to be called 100+ times
GLOBAL_ALL_FIELDS = []


def substitute_links(text, topurl=None):
    """
    Replaces relative markdown links [name](ref) with corresponding internal/external jira links
    Args:
        text (str): substitute links in this string
        topurl (str): topurl for the http/https links
    Returns:
        text: substituted text
    """
    substituted_text = text
    # [link_name](#anchor) ... [link_name2](http://url) ... [link_name3](filename.md#anchor)
    link_groups = re.findall(r"\[([\w\s]+)\]\(([A-Za-z0-9_.-~#-]+)\)", text)
    if not link_groups:
        return substituted_text

    for group in link_groups:
        # local anchor link
        if group[1].startswith("#"):
            replacement = "[#%s]" % group[1]
        # remote http link
        elif group[1].startswith("http://") or group[1].startswith("https://"):  # http link
            replacement = "[%s|%s]" % (group[0], group[1])

        else:  # external markdown link
            replacement = "[%s|%s]" % (group[0], "%s/%s" % (topurl, group[1]))

        substituted_text = substituted_text.replace(
            "[%s](%s)" % (group[0], group[1]), replacement)
    return substituted_text


class JiraSubTask(workflow.GenericTask):
    def __init__(self, summary, jira_session=None, description="", environment=None, conf=None):
        super(JiraSubTask, self).__init__(
            summary, description, environment, conf)
        self.jira_session = jira_session
        self._issue = None
        self._published = False
        self.action = CliAction.CREATE
        self._updatable = None  # for UPDATE operations only

    def is_updatable(self):
        if self._updatable != None:
            return self._updatable

        if self.parent_task and self.parent_task._updatable == False:
            self._updatable = False
            return self._updatable

        elif self.parent_task and self.parent_task._updatable == None:
            if type(self.parent_task) == JiraBasedProject:
                # All workflows should be updatable as long as they're not resolved
                self.parent_task._updatable = True
            else:
                self.parent_task.fetch_myself()
                p_status = u"%s" % self.parent_task._issue.fields.status
                p_update_states = [u"%s" % x.strip(
                ) for x in self.environment["jira"]["epic_update_states"].split(",")]
                if p_status not in p_update_states:
                    self.parent_task.updatable = False
                    self._updatable = False
                    return self._updatable

        self.fetch_myself()
        if self._issue:  # If issue was found
            status = u"%s" % self._issue.fields.status
            update_states = [
                u"%s" % x.strip() for x in self.environment["jira"]["update_states"].split(",")]
            if status not in update_states:
                self._updatable = False
                return self._updatable

        # If issue doesn't exist or is updatable and parent is updatable
        return True

    def set_action(self, action):
        if action not in (CliAction.CREATE, CliAction.UPDATE):
            raise ValueError(
                "JiraBasedProject: unsupported action %s" % action)
        self.action = action

    def _get_field(self, field_name):
        field_name = u"%s" % field_name
        self.logger.debug("Getting field id for '%s'" % field_name)
        global GLOBAL_ALL_FIELDS
        if not GLOBAL_ALL_FIELDS:
            GLOBAL_ALL_FIELDS = self.jira_session.fields()

        for field in GLOBAL_ALL_FIELDS:
            if field[u"name"] == field_name or field[u"id"] == field_name:
                self.logger.debug("Found %s for field '%s'" %
                                  (field[u"id"], field_name))
                return field[u"id"]

        self.logger.debug(
            "Couldn't find field with id or name '%s' in fields(), using field_name itself." % field_name)
        return field_name

    @property
    def description(self):
        res = self._description
        res = res.replace("${%Project}", self.conf["project"]["name"])
        # both are valid
        res = res.replace("${%Product}", self.conf["project"]["name"])
        res = res.replace("${Epic}", str(self.parent_by_subclass(
            JiraBasedWorkflow).summary))  # XXX will not work for subtask
        res = substitute_links(
            res, topurl=self.environment["jira"]['relative_link_topurl'])
        #res = res.replace(">", "&gt;")
        #res = res.replace("<", "&lt;")
        return res

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def _jira_fields(self):
        """
        Returns dict expected by Jira.create_issue()
        """
        # unicode in keys matters, otherwise the field is not set
        fields = {
            u"project": {u"key": self.environment["jira"]["project"]},
            u"summary": self.summary,
            u"description": self.description,
            u"issuetype": {u"name": self.environment["jira"]["mapping_%s" % self.__class__.__name__]},
        }
        if issubclass(type(self), JiraBasedWorkflow) and "mapping_EpicName" in self.environment["jira"]:
            fields[self._get_field(self.environment["jira"]["mapping_EpicName"])] = str(
                self._summary)

        if "mapping_ProjectName" in self.environment["jira"]:
            fields[self._get_field(self.environment["jira"]["mapping_ProjectName"])] = {
                "name": self.conf["project"]["name"]}
        if type(self) == JiraSubTask:
            fields[self._get_field("parent")] = {
                "id": self.parent_task._issue.id}
        fields[self._get_field(self.environment["jira"]["mapping_Assignee"])] = {
            'name': self.owner}

        if "ownership" in self.conf and self.owner:
            if not "mapping_Assignee" in self.environment["jira"]:
                logger.warning(
                    "Unable to find [jira] mapping_Assignee in config. Ownership will be skipped")
            else:
                fields[self._get_field(self.environment["jira"]["mapping_Assignee"])] = {
                    'name': self.owner}

        return fields

    def _get_linktype(self, name):
        name = name.lower()  # ini attr names are lowercase
        assert u"%s" % name in [u"%s" % x.lower().strip(
        ) for x in self.environment["TaskRelations"]["relations"].split(",")]

        if name not in self.environment["JiraTaskRelations"]:
            raise ValueError(
                "Link type %s was not found in [JiraTaskRelations]")
        return self.environment["JiraTaskRelations"][name]

        return

    def publish(self, force_publish=False):
        if not self._published and not force_publish:
            "This callback signalizes that we're all set with setting all attributes. And that task is ready to be created"
            self.logger.debug("Publishing task '%s' description '%s'. All attrs were set. Task owner: %s" % (
                u"%s" % self.summary, u"%s" % self.description[:20].strip(), u"%s" % self.owner))
            self._jira_create_or_update()
            self._published = True

    def fetch_myself(self, force=False):
        def filter_result_by_summary(result, summary):
            self.logger.debug(
                "filter_result_by_summary input is %s" % str(result))
            res = []
            for issue in result:
                self.logger.debug("filter_result_by_summary: issue summary='%s' comparing with '%s'" % (
                    issue.fields.summary, summary))
                if u"%s" % issue.fields.summary == u"%s" % summary:
                    self.logger.debug("filter_result_by_summary: issue passed")
                    res.append(issue)
            return res

        if self._issue and not force:
            return

        # jira.search_issues('project=PROJ and assignee != currentUser()')
        query = 'project=%s AND summary ~ "%s"' % (
            self.environment["jira"]["project"], self.summary)
        if self.parent_task and type(self) == JiraTask:
            query = '%s AND "%s" = "%s"' % (
                query, self.environment["jira"]['mapping_EpicNameQuery'], self.parent_task.summary)

        if self.parent_task and type(self) == JiraSubTask:
            if not self.parent_task._issue:
                if self.action == CliAction.UPDATE:
                    self.logger.debug(
                        "Parent doesn't have _issue. This can happen if Epic is DONE (not editable), and task changed summary and has new subtasks.")
                    return

            self.logger.debug("fetch_myself: Sub task parent %s" %
                              self.parent_task)
            query = '%s AND parent = %s' % (query, self.parent_task._issue.key)

        # pair over product! DANGEROUS if unset
        if "mapping_ProjectName" in self.environment["jira"]:
            query = '%s AND %s ~ "%s"' % (
                query, self.environment["jira"]["mapping_ProjectName"], self.conf["project"]["name"])
        else:
            self.logger.warning(
                "mapping_ProjectName is unset. This may lead to unexpected results while updating existing jiras.")
        self.logger.debug(
            "Using following query to find and update task '%s'" % query)

        # ~ doesn't do exact match
        result = filter_result_by_summary(
            self.jira_session.search_issues(query), self.summary)
        if len(result) > 1:  # ~ doesn't do exact match
            self.logger.error(
                "Found more than 1 result with given EXACT summary, update failed. Query '%s'" % query)
            raise ValueError(
                "Found more than 1 result with given EXACT summary, update failed. Query '%s'" % query)

        self.logger.debug("Query result %s" % str(result))
        if result:
            self._issue = result[0]
        else:
            self.logger.debug("Could not find issue '%s'" % self.summary)

    @property
    def _jira_updatable_fields(self):
        """
        This function is supposed to return only fields which are safe
        to be updated
        """
        return self._jira_fields

    def _description_needs_update(self):
        # in case that jira returns None
        current_description = self._issue.fields.description or u""
        if current_description != u"%s" % self.description:
            return True
        return False

    def _jira_create_or_update(self):
        if self.action == CliAction.UPDATE:
            self.parent_task.fetch_myself()

            if not self.is_updatable():
                self.logger.info(
                    "Issue '%s' or it's parent is not updatable. Skipping" % self.summary)
                return

        # Either create new or not found
        if not self._issue:
            self.logger.debug("Issue fields %s" % self._jira_fields)
            self._issue = self.jira_session.create_issue(
                fields=self._jira_fields)
            self.logger.info("Created issue %s - %s/browse/%s" %
                             (self.summary, self.environment["jira"]["server"], self._issue.key))
            self.logger.info("Assigning task %s to %s " %
                             (self.summary, self.owner))
        else:
            if self._description_needs_update():
                self.logger.info("Issue %s/browse/%s needs to be updated" %
                                 (self.environment["jira"]["server"], self._issue.key))
            # TODO ensure that we process only updatable fields
                self._issue.update(fields=self._jira_updatable_fields)
                self.logger.info("Updated issue %s/browse/%s" %
                                 (self.environment["jira"]["server"], self._issue.key))
            else:
                self.logger.info("Issue %s/browse/%s is up to date. No update needed." %
                                 (self.environment["jira"]["server"], self._issue.key))
        # Doesn't really work with Project
        if self.parent_task and type(self.parent_task) == JiraBasedWorkflow:
            self.jira_session.add_issues_to_epic(self.parent_task._issue.id, issue_keys=[
                                                 self._issue.id, ], ignore_epics=True)
            self.logger.info("Added issue %s under epic %s" %
                             (self._issue.key, self.parent_task._issue.key))


class JiraTask(JiraSubTask, workflow.GenericNestedTask):
    def __init__(self, summary, jira_session=None, description="", environment=None, conf=None):
        super(JiraSubTask, self).__init__(
            summary, description, environment, conf)
        self.jira_session = jira_session
        self._published = False
        self._issue = None
        self._updatable = None

    @property
    def task_class(self):
        return JiraSubTask

    def new_task(self, **kwargs):
        """
        Returns a new instance of class returned by task_class()
        """
        return self.task_class(jira_session=self.jira_session, environment=self.environment, conf=self.conf, **kwargs)

    def add_task(self, task):
        task.logger = self.logger
        task.parent_task = self
        task.action = self.action
        super(JiraTask, self).add_task(task)

    def _locate_issue(self):
        self.jira_session.query()


class JiraBasedWorkflow(JiraTask, workflow.GenericWorkflow):
    def __init__(self, summary, jira_session=None, description="", environment=None, conf=None):
        super(JiraBasedWorkflow, self).__init__(
            summary, jira_session, description, environment, conf)
        self._published = False
        self._issue = None
        self.action = CliAction.CREATE
        self._updatable = None

    @property
    def task_class(self):
        return JiraTask

    def publish_task_relation(self, relation):
        relation.source.fetch_myself()
        relation.target.fetch_myself()

        if self.action == CliAction.UPDATE:
            if not relation.source._issue or not relation.target._issue:
                relation.source.fetch_myself()
                relation.target.fetch_myself()

            # Double check on update, perhaps fetch_myself returned None
            if not relation.source._issue or not relation.target._issue:
                self.logger.debug(
                    "publish_task_relation source: %s" % relation.source._issue)
                self.logger.debug(
                    "publish_task_relation target: %s" % relation.target._issue)
                self.logger.warning("SKIPPED creating of JIRA issue link '%s' %s '%s'  as one of _issues was None " %
                                    (relation.source.summary, relation.relation_name, relation.target.summary))
                return

        self.logger.info("Creating JIRA issue link '%s' %s '%s'" % (
            relation.source.summary, relation.relation_name, relation.target.summary))
        self.jira_session.create_issue_link(self._get_linktype(
            relation.relation_name), relation.source._issue.key, relation.target ._issue.key)


class JiraBasedProject(JiraBasedWorkflow, workflow.GenericProject):

    def publish_task_relations(self):
        super(JiraBasedProject, self).publish_task_relations()
        for task in self.tasks:
            task._replace_task_placeholders()
            task.publish_task_relations()  # publish individual workflows as well

    def fetch_myself(self, force=False):
        return

    @property
    def task_class(self):
        return JiraBasedWorkflow

    @property
    def _jira_fields(self):
        return {}  # not supported , this would be represented best by a dashboard

    def jira_session_from_env(self):
        """
        This will be inherited to every added child task and it's child task ...
        """
        if self.jira_session:
            return

        verify = False
        if "cert" in self.environment["jira"] and self.environment["jira"]["cert"].lower != "none":
            verify = self.environment["jira"]["cert"]
            self.logger.debug("jira_session: Using cert %s" % verify)
        else:
            self.logger.warn("jira_session: Using insecure connection.")
        server = self.environment["jira"]["server"]

        # use value passed by user if mapping is not found
        if self.environment["jira"]["auth"] == "basic":
            user = None
            if "user" in self.environment["jira"]:
                user = self.environment["jira"]["user"]
            else:
                user = raw_input("JIRA user for %s: " % server)

            password = None
            if "password" in self.environment["jira"]:
                password = self.environment["jira"]["password"]
            else:
                password = getpass.getpass(
                    "Password of JIRA user %s for %s: " % (user, server))

            self.jira_session = jira.JIRA(options={"server": server, "verify": verify},
                                          basic_auth=(user, password))

        else:
            raise NotImplementedError(
                "Auth %s is not implemented" % options.auth)


def handle_project(cli):
    """
    Args:
        cli (Cli) - an object representing execution environment
    """
    server = cli.environment["jira"]["server"]
    cli.logger.info(
        "Using JIRA Backend. JIRA Server is %s. Changes will be commited." % server)
    project = JiraBasedProject(
        summary=cli.project_conf["project"]["name"], environment=cli.environment, conf=cli.project_conf)
    project.logger = cli.logger
    project.jira_session_from_env()
    project.set_action(cli.action)

    for workflow_section in cli.project_conf.sections():  # Workflow as in Milestone (e.g Beta) or Epic
        # these are not milestone sections
        if workflow_section in ('product', 'ownership'):
            continue

        # this can be skipped for handling virtual milestones such as Public Beta,
        # where the only purpose is to have a separate set of Milestone Tasks
        # which are named differently
        if 'markdown_filename' in cli.project_conf[workflow_section]:
            # section represents e.g. milestone1, order is important due Blocks/Depends On
            project_relpath = cli.project_conf[workflow_section]['markdown_filename']
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
            project.relations_from_conf_section(
                cli.project_conf, workflow_section)
            project.publish_task_relations()
    return True  # for testing purposes


class FakeJiraInstance(object):
    def __init__(self):
        self.__issues = {}
        self.__next_id = 1
        self.__lock = False

    def _lock_session(self):
        self.__lock = True

    def _unlock_session(self):
        self.__lock = False

    def _wait_lock(self):
        while self.__lock:
            time.sleep(0.5)
        return

    def _next_id(self):
        self._wait_lock()
        self._lock_session()
        i = self.__next_id
        self.__next_id += 1
        self._unlock_session()
        return i

    def client_info(self):
        return SERVER_MAPPING["fake"]

    def issue(self, id):
        return self.__issues.get(str(id), None)

    def create_issue(self, fields):
        assert fields['issuetype'], "Issue type is needed. Got following fields %s" % fields
        issue = FakeIssue(fields, id=self._next_id())
        self.__issues[issue.id] = issue
        return issue

    def add_issues_to_epic(self, epic_id, issue_keys, ignore_epics=True):
        return

    def create_issue_link(self, relation, issue1, issue2):
        return

    def fields(self):
        with open(os.path.join(EXAMPLE_DIR, "jira-fields.json")) as fd:
            return json.load(fd)


class FakeIssue(object):  # for test execution without --commit
    def __init__(self, fields, id):
        if id:
            self.id = u"%s" % id
        self.key = u"%s-%s" % (fields['project']['key'], self.id)

        for key, value in fields.items():
            setattr(self, key, value)

    def __getitem__(self, item):
        return getattr(self, item)
