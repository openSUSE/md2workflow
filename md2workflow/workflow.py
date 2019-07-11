#!/usr/bin/env python

# -*- coding: utf-8 -*-

import configparser
import logging

from md2workflow.markdown import *


class TaskRelation(object):
    def __init__(self, relation_name, parent, source, target):
        """
        Args:
            relation_type (str) - A flexible string describing given relation
            parent (Workflow or Project obj) - A reference to the parent workflow or project
                                     this is necessary as you can have multiple
                                     workflows linked to each other
            source (GenericTask instance) - a name/uid of source task for the relation
            target (GenericTask) - A name/uid of target task for the relation
                                   A TaskPlaceHolder instance can be used in case
                                   you're creating relation to a not yet existing task
        """

        self.relation_name = relation_name
        if not issubclass(type(source), GenericTask):
            raise ValueError(
                "Expected GenericTask subclass for source. Got %s" % type(source))
        self.source = source
        if not issubclass(type(source), GenericTask):
            raise ValueError(
                "Expected GenericTask subclass for target. Got %s" % type(target))
        self.target = target
        if not issubclass(type(parent), GenericWorkflow):
            raise ValueError(
                "Expected an actual Workflow object. Got %s" % type(parent))
        self.parent = parent


class GenericTask(object):
    def __init__(self, summary, description=None, environment=None, conf=None):
        self.summary = summary
        self.description = description
        self.environment = environment or configparser.ConfigParser()
        self.conf = conf or configparser.ConfigParser()  # project_conf
        self._variables = {}
        # Each Task needs to be able to have a parent
        # no matter if it supports further nesting or not
        self._tasks = []  # defined for inheritance purposes but can't be really accessed from outside
        self._parent_task = None
        # This should be correctly replaced in add_task by logger of the parent
        self.logger = logging.getLogger("Placeholder")
        self._published = False

    def publish(self, force_publish=False):
        if not self._published and not force_publish:
            "This callback signalizes that we're all set with setting all attributes. And that task is ready to be created"
            self.logger.debug("Publishing task '%s' description '%s'. All attrs were set. Task owner: %s" % (
                self.summary, self.description[:20], self.owner))
            self._published = True

    def __str__(self):
        return self._summary

    @property
    def variables(self):
        return self._variables

    def add_variable(self, name, value):
        self._variables[name] = value
        self.logger.debug("Adding variable %s=%s to (%s)" %
                          (name, value, self.variables))

    @property
    def owner(self):
        try:
            group = self.variables[self.conf['ownership']['markdown_variable']]
            group = group.replace("*", "").strip()
            self.logger.debug(
                "Found ownership group %s for task %s" % (group, self.summary))
            ownr = self.conf['ownership'][group]
            self.logger.debug("Found owner %s for task %s" %
                              (ownr, self.summary))
            return ownr
        except KeyError:
            pass
            #self.logger.debug("Failed to find owner for task %s. Variables: %s Conf: %s" % (self.summary, self.variables, self.conf._sections))
        return None

    @property
    def supports_tasks():
        return True

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, text):
        self._summary = text or ""  # Make sure there is not None

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, text):
        if text == None:
            text = ""
        self._description = text.strip() or ""  # Make sure there is not None

    @property
    def parent_task(self):
        # Setter part is done in add_child_task
        return self._parent_task

    @parent_task.setter
    def parent_task(self, task):
        # Setter part is done in add_child_task
        self.logger.debug("Setting parent '%s' to task '%s'" %
                          (self.summary, task.summary))
        self._parent_task = task

    def parent_by_subclass(self, subclass):
        """
        Args:
            subclass (class name)

        Iterates over parents of object until it finds nearest instance of a matching subclass.
        Returns object matching given subclass or None if not found
        """
        head = self

        if issubclass(type(head), subclass):
            return head

        while head.parent_task and not issubclass(type(head), subclass):
            head = head.parent_task

        if not issubclass(type(head), subclass):
            self.logging.warning("Couldn't find parent of  %s with subclass %s" % (
                repr(self), repr(subclass)))
            return None  # Did not find anything, just return itself

        return head

    def get_task_by_summary(self, summary, from_top=False):
        """
        Args
            summary (str) - summary of a task (uid)
            from_top=False - start to seek from the project/workflow level
        """
        summary = u"%s" % summary.strip()
        if self.summary == summary:
            return self

        for task in self.tasks:
            if task.summary == summary:
                return task.get_task_by_summary(summary)

        if from_top:
            top = self.parent_by_subclass(GenericWorkflow)
            # we do have a project (might not be case for unittests)
            if top.parent_task:
                top = top.parent_task

            for task in top.tasks:
                res = task.get_task_by_summary(summary)
                if res:
                    return res

        self.logger.warning("Could not find task with summary '%s'" % summary)
        return None

    @property
    def tasks(self):
        return self._tasks


class GenericNestedTask(GenericTask):
    """
    This class can have also child nodes aside from parent
    """
    @property
    def task_class(self):
        # these tasks should not support nesting as\we have only one level of subtasks
        # (not counting project and workflow)
        return GenericTask

    def new_task(self, **kwargs):
        """
        Returns a new instance of class returned by task_class()
        """
        return self.task_class(**kwargs)

    def add_task(self, task):
        """
        Args
            task (GenericTask)
        """
        if not (issubclass(type(task), GenericTask)):
            raise ValueError(
                "Expected a subclass of GenericTask. Got %s" % type(task))
        task.logger = self.logger
        task.parent_task = self
        task.environment = self.environment
        task.conf = self.conf
        self._tasks.append(task)

        self.logger.debug("Added child task '%s' under '%s'" %
                          (task.summary, self.summary))


class TaskPlaceHolder(GenericTask):
    """
    This is a class which is used to reference not yet created target of a relation
    """

    def publish(self):
        raise ValueError(
            "TaskPlaceHolder should never be published. Please make sure to replace them properly")


class GenericWorkflow(GenericNestedTask):
    """
    Worklfow is basically a task which gives tasks and nested tasks order and introduces relations
    Relations need to be supported with a environment config .environment file definig them
    """

    def __init__(self, summary, description=None, environment=None, conf=None):
        super(GenericWorkflow, self).__init__(
            summary, description, environment, conf)
        self._task_relations = []

    def _replace_task_placeholders(self):
        """
        This function ensure that all TaskPlaceHolder tasks, including subclasses
        are replaced by reference to a valid GenericTask subclass.

        This needs to be called manually if you're not using from_markdown()
        """

        self.logger.debug("in _replace_task_placeholders (self=%s)" % self)
        # first find all references to the PlaceHolder
        for i in range(len(self.tasks)):
            if issubclass(type(self.tasks[i]), TaskPlaceHolder):
                tasks[i] = self.get_task_by_summary(
                    self.tasks[i].summary, from_top=True)

        # update all references in relations
        for i in range(len(self.task_relations)):
            if issubclass(type(self.task_relations[i].target), TaskPlaceHolder) or \
                    issubclass(type(self.task_relations[i].source), TaskPlaceHolder):

                self.logger.debug("Replacing Placeholder relation reference for %s -> %s" %
                                  (self.task_relations[i].source, self.task_relations[i].target))
                t = self.get_task_by_summary(
                    self.task_relations[i].target.summary, from_top=True)
                s = self.get_task_by_summary(
                    self.task_relations[i].source.summary, from_top=True)
                assert t != None, "Relations: Could not find task with summary '%s'" % self.task_relations[
                    i].target.summary
                assert s != None, "Relations: Could not find task with summary '%s'" % self.task_relations[
                    i].source.summary
                relation = TaskRelation(
                    relation_name=self.task_relations[i].relation_name,
                    parent=self,
                    source=s,
                    target=t
                )

                self.task_relations[i] = relation

    @property
    def task_class(self):
        return GenericNestedTask  # Needs to support Nesting

    @property
    def task_relations(self):
        return self._task_relations

    def find_relation(self, source, target):
        """
        Args
            source (GenericTask)
            target (GenericTask)
        """
        result = []
        for relation in self.task_relations:
            # check both directions
            if (relation.source == source and relation.target == target) or \
                    (relation.source == target and relation.target == source):
                result.append(relation)
        if result:
            assert len(
                result) == 1, "Expected only one relation in between two tasks. %s" % result
        return result

    def add_task_relation(self, relation):
        """
        Args:
            relation (TaskRelation)

        Adding relation is skipped in case that tasks already have an existing relation.
        This is done so we do not dupplicate effort on checking both inbound and outbound references

        I can't really think of good example why tasks should have multiple different relations in betwen each other
        """
        if not isinstance(relation, TaskRelation):
            raise ValueError(
                "Expected instance of TaskRelation. Got %s" % type(relation))
        self.logger.info("Adding relation %s %s %s" % (
            relation.source, relation.relation_name, relation.target))
        if self.find_relation(relation.source, relation.target):
            logging.debug("Some relation in between %s and %s already exists. Skipping creation" % (
                relation.source, relation.target))
        else:
            self._task_relations.append(relation)

    def get_task_or_placeholder_by_summary(self, summary):
        result = self.get_task_by_summary(summary, from_top=True)
        if not result:
            logging.debug("Creating a task placeholder for %s" % summary)
            result = TaskPlaceHolder(summary)
        return result

    def _variable_is_relation(self, variable):
        """
        Args
            variable (Variable)
        Does the variable.name match with one of comma separated relations from the config?
        Comma is used so the relation can contain space e.g. 'Depends on'

        Example section:
        [TaskRelations]
        relations = Blocks, Depends On, Implements, Implemented by

        """
        if not isinstance(variable, Variable):
            raise ValueError("Expected a Variable node, got %s" %
                             type(variable))

        if self.environment.has_section("TaskRelations"):
            if not "relations" in self.environment["TaskRelations"]:
                raise ValueError(
                    "Section [TaskRelations] expected variable relations = Relation A ...")

            self.logger.debug(
                "Testing if variable '%s' is a relation" % variable.name)
            if u"%s" % variable.name.lower() in [u"%s" % x.lower().strip() for x in self.environment["TaskRelations"]["relations"].split(",")]:
                self.logger.debug(
                    "variable %s was identified as a relation" % variable)
                return True
            else:
                self.logger.debug("variable '%s' was not identified as a relation. (Supported list: %s)" % (
                    variable.name, self.environment["TaskRelations"]["relations"]))
        return False

    def publish_task_relations(self):
        """
        This needs to be called after all tasks were published.
        """
        self._replace_task_placeholders()
        for relation in self.task_relations:
            self.logger.debug("Publishing task relation %s" % repr(relation))
            if not relation.source or not relation.target:
                self.logger.warning("Could not one of find relation items source=%s target=%s. SKIPPING" % (
                    relation.source, relation.target))
                continue
            self.publish_task_relation(relation)

    def publish_task_relation(self):
        """
        Please override me
        """
        pass


class GenericProject(GenericWorkflow):
    """
    Project may contain several linked workflows and supports from_markdown()
    """
    @property
    def task_class(self):
        return GenericWorkflow

    def from_markdown(self, obj, override_workflow_name=None):
        if not isinstance(obj, MarkDown):
            raise ValueError(
                "Expected a md2workflow.MarkDown object as an argument")
        self._process_markdown_node(
            obj, override_workflow_name=override_workflow_name)

    def relations_from_conf_section(self, config, section_name):
        for relation in self.environment["TaskRelations"]['relations'].split(','):
            relation = relation.strip()
            # ini does attr names lowercase
            if relation.lower() not in config[section_name].keys():
                continue
            # is this an inbound relation (need to reverse target/source)
            inbound = False
            for inbound_relation in self.environment["TaskRelations"]['inbound'].split(','):
                if relation == inbound_relation.strip():
                    inbound = True

            for target in config[section_name][relation].split(","):
                t = None
                s = None
                if inbound:
                    t = self.get_task_or_placeholder_by_summary(section_name)
                    s = self.get_task_or_placeholder_by_summary(target)
                else:
                    s = self.get_task_or_placeholder_by_summary(section_name)
                    t = self.get_task_or_placeholder_by_summary(target)

                self.logger.info(
                    "Adding relation from conf %s to %s" % (relation, repr(self)))

                self.add_task_relation(
                    TaskRelation(
                        relation_name=relation,
                        parent=self,
                        source=s,
                        target=t)  # At this point the task is most likely not yet created, store name reference instead
                )

    def _get_workflow_level_heading(self):
        return Heading1

    def _get_task_level_heading(self):
        return Heading4

    def _get_subtask_level_heading(self):
        return eval("Heading%d" % (self._get_task_level_heading().level + 1))

    def _process_markdown_node(self, node, head=None, override_workflow_name=None):
        # reference to currently processed task
        for nd in node.nodes:
            self.logger.debug("Processing node %s (HEAD: %s) - %s" %
                              (nd.__class__.__name__, repr(head), str(head).strip()[20:]))
            # E.g This wouldb be an epic in JIRA
            if isinstance(nd, self._get_workflow_level_heading()):
                # if head:
                #    head.publish()
                # Section overrides the
                if override_workflow_name:
                    self.logger.debug("Overriding heading value '%s' with section name '%s' " % (
                        nd, override_workflow_name))
                head = self.new_task(summary=override_workflow_name or nd.text)
                self.add_task(head)  # Epics live on toplevel

            elif isinstance(nd, self._get_task_level_heading()):
                # if head:
                #    head.publish()
                # in case that workflow file has no Workflow level identifier (no H1)
                if head == None and override_workflow_name:
                    self.logger.debug(
                        "Workflow level heading is missing. Using %s for workflow name" % override_workflow_name)
                    head = self.new_task(summary=override_workflow_name)
                    self.add_task(head)
                    head.publish()
                elif head == None:
                    raise ValueError(
                        ".md file doesn't have Workflow level heading and override_workflow_name was not supplied")

                head = head.parent_by_subclass(GenericWorkflow)
                head.publish()
                task = head.new_task(summary=nd.text)
                # Head should be in this case one of self.tasks / workflow level
                head.add_task(task)
                head = task

            # make sure that this gets processed before Paragraph
            elif isinstance(nd, Variable):
                if not head:
                    self.logger.error(
                        "Identified markdown variable, but no preceeding heading or ask definition. Is this a valid markdown?")
                else:
                    self._process_markdown_variable(nd, head)

            elif isinstance(nd, Paragraph):
                # Skip any initial text until we really found heading
                # keep in mind that this applies also for Heading1 / Workflow
                head.description = nd.text
                self.logger.debug("Identified paragraph node. %s, (%s...)" % (
                    nd, nd.text[:20].strip()))
                head.publish()
            elif isinstance(nd, self._get_subtask_level_heading()):
                # head.publish() # call after all attr gathering is done
                # Add task under Workflow
                while not issubclass(type(head), GenericNestedTask):
                    head = head.parent_task
                task = head.new_task(summary=nd.text)
                # Head should be in this case one of self.tasks / workflow level
                head.add_task(task)
                head = task
            else:
                self.logger.debug("handler for node %s. Skipping" % nd)

            if nd.nodes:
                self._process_markdown_node(nd, head)

        if head and not head._published:
            head.publish()  # call after all attr gathering is done

    def _process_markdown_variable(self, variable, task):
        """
        Args
            variable (Variable)
            task (GenericTask) - a task which will shall contain the variable
        """
        self.logger.debug("Processing task variable %s" % variable)
        # Is it a relation?
        if self._variable_is_relation(variable):
            # Links in between tasks are defined in Workflow level object
            head = task.parent_by_subclass(GenericWorkflow)

            inbound = False
            for inbound_relation in self.environment["TaskRelations"]['inbound'].split(','):
                if variable.name == inbound_relation.strip():
                    inbound = True

                t = None
                s = None
                if inbound:
                    t = task
                    s = self.get_task_or_placeholder_by_summary(variable.value)
                else:
                    s = task
                    t = self.get_task_or_placeholder_by_summary(variable.value)

            assert t != None
            assert s != None
            self.logger.info(
                "Adding relation from a task definition from %s to %s" % (s, t))
            head.add_task_relation(
                TaskRelation(
                    relation_name=variable.name,
                    parent=self,
                    source=s,
                    target=t  # At this point the task is most likely not yet created, store name reference instead
                )
            )
        else:
            self.logger.debug(
                "Task variable %s was not identified as a relation" % variable)
            task.add_variable(variable.name, variable.value)
