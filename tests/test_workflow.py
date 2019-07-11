#!/usr/bin/env python

# -*- coding: utf-8 -*-

import configparser

import md2workflow.markdown as markdown
import md2workflow.workflow as workflow


def test_workflow_read_config():
    environment_config = u"""
    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by
    """

    project = workflow.GenericProject("Test Project")
    wf = workflow.GenericWorkflow("Test Workflow")
    wf.environment.read_string(environment_config)
    assert wf.environment.has_section("TaskRelations")


def test_from_md_empty_task1_task2():
    raw = "# workflow name\n#### task 1\n#### task 2"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.from_markdown(md)

    assert len(project.tasks) == 1  # Workflow level task
    assert len(project.tasks[0].tasks) == 2
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == ""
    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == ""


def test_from_md_empty_task1_task2_no_h1():
    raw = "#### task 1\n#### task 2"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.from_markdown(md, override_workflow_name="TestWorkflow")

    assert len(project.tasks) == 1  # Workflow level task
    assert len(project.tasks[0].tasks) == 2
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == ""
    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == ""


def test_from_md_empty_task1_variable():
    raw = "# workflow name\n#### task 1\nvar1: value"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.from_markdown(md)

    assert len(project.tasks) == 1  # Workflow level task
    assert len(project.tasks[0].tasks) == 1
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == ""
    assert project.tasks[0].tasks[0].variables["var1"] == "value"


def test_from_md_task1_task2():
    raw = u"# workflow name\n#### task 1\ndescription 1\n#### task 2\ndescription 2"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.from_markdown(md)

    assert len(project.tasks) == 1  # Workflow level
    assert len(project.tasks[0].tasks) == 2
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == "description 1"

    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == "description 2"


def test_from_md_task_with_subtask_and_task():
    """
    This is to check that parser correcty processes subtask and then upcomming
    top level task as well.
    """
    raw = "# workflow name\n#### task 1\ndescription 1\n##### sub task 1\n#### task 2\ndescription 2"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.from_markdown(md)

    assert len(project.tasks) == 1  # The Workflow task is just one
    assert len(project.tasks[0].tasks) == 2  # top level tasks
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == "description 1"

    assert len(project.tasks[0].tasks[0].tasks) == 1

    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == "description 2"


def test_add_relation_inbound_outbound():
    """
    This test is checking whether following produces exactly one relation

    A Blocks B
    B is Blocked by A
    """
    wf = workflow.GenericWorkflow("Test Workflow")
    task1 = workflow.GenericTask("Task 1")
    task2 = workflow.GenericTask("Task 2")

    assert len(wf.task_relations) == 0

    wf.add_task(task1)
    wf.add_task(task2)

    wf.add_task_relation(workflow.TaskRelation(
        relation_name="relation",
        parent=wf,
        source=task1,
        target=task2
    )
    )

    assert len(wf.task_relations) == 1
    assert wf.task_relations[0].relation_name == "relation"
    assert wf.task_relations[0].source.summary == "Task 1"
    assert wf.task_relations[0].target.summary == "Task 2"

    wf.add_task_relation(workflow.TaskRelation(
        relation_name="outbound relation",
        parent=wf,
        source=task2,
        target=task1
    )
    )

    assert len(
        wf.task_relations) == 1, "Inbound and Outbound relation are counted as 1. Found many"
    assert wf.task_relations[0].relation_name == "relation"
    assert wf.task_relations[0].source.summary == "Task 1"
    assert wf.task_relations[0].target.summary == "Task 2"


def test_add_relations():
    wf = workflow.GenericWorkflow("Test Workflow")
    task1 = workflow.GenericTask("Task 1")
    task2 = workflow.GenericTask("Task 2")
    task3 = workflow.GenericTask("Task 3")

    assert len(wf.task_relations) == 0

    wf.add_task(task1)
    wf.add_task(task2)
    wf.add_task(task3)

    wf.add_task_relation(workflow.TaskRelation(
        relation_name="relation",
        parent=wf,
        source=task1,
        target=task2
    )
    )

    assert len(wf.task_relations) == 1
    assert wf.task_relations[0].relation_name == "relation"
    assert wf.task_relations[0].source.summary == "Task 1"
    assert wf.task_relations[0].target.summary == "Task 2"

    wf.add_task_relation(workflow.TaskRelation(
        relation_name="some relation",
        parent=wf,
        source=task2,
        target=task3,
    )
    )
    assert len(wf.task_relations) == 2

    assert wf.task_relations[0].relation_name == "relation"
    assert wf.task_relations[0].source.summary == "Task 1"
    assert wf.task_relations[0].target.summary == "Task 2"

    assert wf.task_relations[1].relation_name == "some relation"
    assert wf.task_relations[1].source.summary == "Task 2"
    assert wf.task_relations[1].target.summary == "Task 3"


def test_add_relation_from_markdown():
    environment_config = u"""
    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by
    inbound = Implemented by, Depends On
    """
    environment = configparser.ConfigParser()
    environment.read_string(environment_config)

    raw = u"# workflow name\n#### task 1\nBlocks: task 2\ndescription 1\n#### task 2\ndescription 2"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.environment = environment
    project.from_markdown(md)

    # The relation from raw are for workflow, project level relations are in project_conf
    assert len(project.task_relations) == 0
    assert len(project.tasks[0].task_relations) == 1
    assert project.tasks[0].task_relations[0].relation_name == "Blocks"
    assert project.tasks[0].task_relations[0].source.summary == "task 1"
    assert project.tasks[0].task_relations[0].target.summary == "task 2"


def test_ignore_variable_inside_paragraph_from_markdown():
    environment_config = u"""
    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by
    inbound = Implemented by, Depends On
    """
    environment = configparser.ConfigParser()
    environment.read_string(environment_config)

    raw = u"# workflow name\n#### task 1\ndescription 1\nSomeVariable: lala\n#### task 2\ndescription 2"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.environment = environment
    project.from_markdown(md)

    # The relation from raw are for workflow, project level relations are in project_conf
    assert len(project.tasks) == 1
    assert len(project.tasks[0].variables) == 0
    assert len(project.tasks[0].tasks) == 2
    assert len(project.tasks[0].tasks[1].variables) == 0
    assert len(project.tasks[0].tasks[0].variables) == 0


def test_ignore_heading_inside_quoted_teqt():
    environment_config = u"""
    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by
    inbound = Implemented by, Depends On
    """
    environment = configparser.ConfigParser()
    environment.read_string(environment_config)

    raw = u"# workflow name\n#### task 1\ndescription 1\n```\n#h1\n```\n#### task 2\ndescription 2"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.environment = environment
    project.from_markdown(md)

    # The relation from raw are for workflow, project level relations are in project_conf
    assert len(project.tasks) == 1
    assert len(project.tasks[0].tasks) == 2
    assert project.tasks[0].description == ""
    assert project.tasks[0].tasks[0].description == "description 1\n```\n#h1\n```"
    assert project.tasks[0].tasks[1].description == "description 2"


def test_cross_workflow_relations():
    environment_config = u"""
    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by
    inbound = Implemented by, Depends On
    """
    environment = configparser.ConfigParser()
    environment.read_string(environment_config)

    project_conf = u"""
    [Alpha]
    markdown_filename = fake

    [Beta]
    Depends on = Alpha
    """
    conf = configparser.ConfigParser()
    conf.read_string(project_conf)

    # keep it short
    raw = u"# Alpha\nThis is alpha checklist"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.environment = environment

    project.from_markdown(md)

    # keep it short
    raw = u"# Beta\nThis is beta checklist"
    md = markdown.MarkDown()
    md.reads(raw)
    project.relations_from_conf_section(conf, "Beta")

    # The relation from raw are for workflow, project level relations are in project_conf
    assert len(project.task_relations) == 1


def test_user_group():
    raw = "# workflow name\n#### task 1\nResponsible: group_a\n#### task 2\nResponsible: group_b"
    md = markdown.MarkDown()
    md.reads(raw)

    environment_config = u"""
    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by
    inbound = Implemented by, Depends On
    """

    project_conf = u"""
    [ownership]
    markdown_variable = Responsible
    group_a = foo
    group_b = bar
    """

    project = workflow.GenericProject("Test Project")
    project.environment.read_string(environment_config)
    project.conf.read_string(project_conf)
    project.from_markdown(md)

    assert project.tasks[0].tasks[0].variables  # used for ownership
    print(project.tasks[0].tasks[0].variables)
    assert project.tasks[0].tasks[1].variables
    print(project.tasks[0].tasks[1].variables)
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == ""
    assert project.tasks[0].tasks[0].owner == "foo"
    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == ""
    assert project.tasks[0].tasks[1].owner == "bar"


def test_user_group_nondefault_var():
    raw = "# workflow name\n#### task 1\nOwner: group_a\n#### task 2\nOwner: group_b"
    md = markdown.MarkDown()
    md.reads(raw)

    environment_config = u"""
        [TaskRelations]
        relations = Blocks, Depends On, Implements, Implemented by
        inbound = Implemented by, Depends On
    """

    project_conf = u"""
    [ownership]
    markdown_variable = Owner
    group_a = foo
    group_b = bar
    """

    project = workflow.GenericProject("Test Project")
    project.environment.read_string(environment_config)
    project.conf.read_string(project_conf)
    project.from_markdown(md)

    assert project.tasks[0].tasks[0].variables  # used for ownership
    print(project.tasks[0].tasks[0].variables)
    assert project.tasks[0].tasks[1].variables
    print(project.tasks[0].tasks[1].variables)
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == ""
    assert project.tasks[0].tasks[0].owner == "foo"
    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == ""
    assert project.tasks[0].tasks[1].owner == "bar"


def test_get_epic_task():
    raw = "# workflow name\n#### task 1\n#### task 2\n##### subtask 2.1"
    md = markdown.MarkDown()
    md.reads(raw)

    project = workflow.GenericProject("Test Project")
    project.from_markdown(md)

    assert len(project.tasks) == 1  # Workflow level task
    assert len(project.tasks[0].tasks) == 2
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == ""
    assert len(project.tasks[0].tasks[0].tasks) == 0
    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == ""
    assert len(project.tasks[0].tasks[1].tasks) == 1

    assert project.tasks[0].parent_by_subclass(
        workflow.GenericWorkflow).summary == "workflow name"
    assert project.tasks[0].tasks[1].parent_by_subclass(
        workflow.GenericWorkflow).summary == "workflow name"
    assert project.tasks[0].tasks[1].tasks[0].parent_by_subclass(
        workflow.GenericWorkflow).summary == "workflow name"
