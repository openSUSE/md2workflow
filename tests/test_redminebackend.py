# -*- coding: utf-8 -*-

import configparser
import os

import md2workflow.markdown as markdown
import md2workflow.workflow as workflow
import md2workflow.backend.redminebackend as redminebackend
import md2workflow.cli as cli

def test_redmine_objects():
    task = redminebackend.RedmineTask(summary="Test task")
    subtask = redminebackend.RedmineSubtask(summary="Test sub task")
    workflow = redminebackend.RedmineBasedWorkflow(summary="Test work flow")
    project = redminebackend.RedmineBasedProject(summary="Test project")
