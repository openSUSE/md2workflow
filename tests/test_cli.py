# -*- coding: utf-8 -*-

import pytest
import os
import configparser

import md2workflow.cli as cli


def test_validate_example_config():
    config = configparser.ConfigParser()
    config.read(cli.DEFAULT_CONFIG_PATH)
    assert config._sections  # check if it's not empty
    client = cli.Cli(config)
    # returns empty list if no error was found
    assert not cli.Cli.validate_config(config)


def test_validate_example_project():
    config = configparser.ConfigParser()
    config.read(os.path.join(cli.EXAMPLE_DIR, "my_project.conf"))
    assert config._sections  # check if it's not empty
    # returns empty list if no error was found
    assert not cli.Cli.validate_project(config)


def test_handle_local_project():
    config = configparser.ConfigParser()
    config.read(cli.DEFAULT_CONFIG_PATH)
    assert config._sections  # check if it's not empty
    client = cli.Cli(config)

    project_conf = configparser.ConfigParser()
    project_conf.read(os.path.join(cli.EXAMPLE_DIR, "my_project.conf"))
    client.handle_project(project_conf)


def test_jira_backend_example():
    config_raw = u"""
    [global]
    backend = jira

    [jira]
    server = None
    insecure = True
    cert = None

    [logging]
    level = DEBUG

    [TaskRelations]
    relations = Blocks, Depends On, Implements, Implemented by
    """
    config = configparser.ConfigParser()
    config.read_string(config_raw)
    client = cli.Cli(config)

    project_conf = configparser.ConfigParser()
    project_conf.read(os.path.join(
        cli.EXAMPLE_DIR, "release-checklist", "my_project.conf"))
    client.handle_project(project_conf)


def test_jira_unknown_backend_example():
    config_raw = u"""
    [global]
    backend = unknown

    [logging]
    level = DEBUG
    """
    config = configparser.ConfigParser()
    config.read_string(config_raw)
    client = cli.Cli(config)

    project_conf = configparser.ConfigParser()
    project_conf.read(os.path.join(
        cli.EXAMPLE_DIR, "release-checklist", "my_project.conf"))
    client.handle_project(project_conf)
