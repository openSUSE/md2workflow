# -*- coding: utf-8 -*-

import configparser
import os

import md2workflow.markdown as markdown
import md2workflow.workflow as workflow
import md2workflow.backend.genericbackend as genericbackend
import md2workflow.cli as cli

"""
def test_beta_example_generic_backend():

    environment_config = configparser.ConfigParser()
    environment_config.read(cli.DEFAULT_CONFIG_PATH)
    environment = configparser.ConfigParser()
    environment.read(environment_config)

    client = cli.Cli(environment, cli.CliAction.CREATE)
    assert client.handle_project(os.path.join(cli.EXAMPLE_DIR, "release-checklist", "my_project.conf"))
"""
