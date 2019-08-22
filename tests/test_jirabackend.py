# -*- coding: utf-8 -*-

import configparser
import logging
import os

import md2workflow.markdown as markdown
import md2workflow.workflow as workflow
import md2workflow.backend.jirabackend as jirabackend
import md2workflow.cli as cli


def test_user_group_raw():
    raw = "# workflow name\n#### task 1\nResponsible: group_a\ndescription\n#### task 2\nResponsible: group_b\ndescription2"
    md = markdown.MarkDown()
    md.reads(raw)

    environment_config = u"""
    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by

    [jira]
    relative_link_topurl = http://localhost
    server = http://localhost
    project = Test
    mapping_JiraSubTask = Sub-Task
    mapping_JiraTask = Task
    mapping_JiraBasedWorkflow = Epic
    mapping_EpicName = Epic Name
    mapping_EpicNameQuery = Epic Link
    mapping_Assignee = Worker
    mapping_ProjectName = Product
    update_states = Open, Backlog
    """

    project_conf = u"""
    [project]
    name = Test Product

    [ownership]
    markdown_variable = Responsible
    group_a = foo
    group_b = bar
    """

    project = jirabackend.JiraBasedProject("Test Product")
    project.environment.read_string(environment_config)
    project.conf.read_string(project_conf)
    project.jira_session = jirabackend.FakeJiraInstance()
    project.from_markdown(md)
    project.publish_task_relations()

    assert project.tasks[0].tasks[0].variables  # used for ownership
    print(project.tasks[0].tasks[0].variables)
    assert project.tasks[0].tasks[1].variables
    print(project.tasks[0].tasks[1].variables)
    assert project.tasks[0].tasks[0].summary == "task 1"
    assert project.tasks[0].tasks[0].description == "description"
    assert project.tasks[0].tasks[0].owner == "foo"
    assert project.tasks[0].tasks[1].summary == "task 2"
    assert project.tasks[0].tasks[1].description == "description2"
    assert project.tasks[0].tasks[1].owner == "bar"

def test_bold_description():
    # Using subtask as it's a lowest level object
    subtask = jirabackend.JiraSubTask(summary="test")
    subtask.logging = logging.getLogger()
    subtask.description = "This is a **Bold** text"
    assert subtask.description == "This is a *Bold* text" # Jira uses single star

    subtask.description = "This is a __Bold__ text"
    assert subtask.description == "This is a *Bold* text" # Jira uses single star
