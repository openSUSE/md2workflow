# -*- coding: utf-8 -*-

import md2workflow.markdown as markdown
import md2workflow.workflow as workflow
import md2workflow.validation.project_validation
import md2workflow.validation.config_validation
import md2workflow.validation
import codecs
import configparser
import getpass
import os
import sys
import logging
import pkg_resources

from optparse import OptionParser, OptionGroup, SUPPRESS_HELP
from inspect import getmembers, isfunction

DEFAULT_CONFIG_DIR = "/etc/md2workflow"
DEFAULT_CONFIG_PATH = os.path.join(DEFAULT_CONFIG_DIR, "local.conf")
EXAMPLE_DIR = os.path.join(DEFAULT_CONFIG_DIR, "config")
USER_CONFIG_DIR = os.path.expanduser(os.path.join("~", ".md2workflow"))
SHARE_CONFIG_DIR="share/md2workflow/config" # value is used in  setup.py

# for development
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "example")):
    dirname = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
    DEFAULT_CONFIG_DIR = os.path.normpath(os.path.join(dirname, "config"))
    DEFAULT_CONFIG_PATH = os.path.join(
        DEFAULT_CONFIG_DIR, os.path.basename(DEFAULT_CONFIG_PATH))
    EXAMPLE_DIR = os.path.normpath(os.path.join(dirname, "example"))

CONFIG_LOOKUP_DIRS = [".", USER_CONFIG_DIR, DEFAULT_CONFIG_DIR, os.path.join(sys.prefix, SHARE_CONFIG_DIR)]


class CliAction:
    CREATE = "create"
    UPDATE = "update"


def get_md_abspath(config, relpath):
    """
    Args:
        config - path to project config file (not the dir)
        relpath - relative path to .md file from config file

    Returns:
        returns abspath to .md file
    """
    return os.path.normpath(
        os.path.join(
            os.getcwd(),
            os.path.dirname(config),
            relpath
        )
    )


class Cli(object):

    def __init__(self, environment=None, action=CliAction.CREATE):
        """
        Args:
            environment=None (ConfigParser)
            action (CliAction) - one of ClieAction constants create|update
        """
        # Use environment so we can keep the name across classes and
        # avoid mixing with .conf which is a workflow/project config
        self.environment = environment or configparser.ConfigParser()

        self.__set_logger()
        self.project_conf = configparser.ConfigParser()
        self.project_path = None
        self.action = action

    def __set_logger(self):
        """
        Sets logger based on config
        """
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)

        if self.environment.has_section("logging") and "level" in self.environment["logging"]:
            # level is validated in validate_config
            self.logger.setLevel(eval("logging.%s" %
                                      self.environment["logging"]["level"]))
        else:
            self.logger.setLevel(logging.INFO)
        #self.logger.debug("Environment config: %s", self.environment._sections)

    @staticmethod
    def validate_config(config):
        """
        Args:
            project_conf (ConfigParser instance) - md2workflow config e.g /etc/md2workflow/configuration.ini
        Returns:
            list - Empty list is no errors, otherwise list of strings describing issues
        """
        errors = []

        functions_list = [o for o in getmembers(
            md2workflow.validation.config_validation) if isfunction(o[1])]
        for func in functions_list:
            errors.extend(func[1](config))
        return errors

    @staticmethod
    def get_config_abspath(env_or_path):
        # Check whether file is not specified by it's url

        for ldir in CONFIG_LOOKUP_DIRS:
            if os.path.exists(os.path.join(ldir, env_or_path)):
                return os.path.join(ldir, env_or_path)

            elif os.path.exists(os.path.join(ldir, "%s.conf" % env_or_path)):
                return os.path.join(ldir, "%s.conf" % env_or_path)

        return None

    @staticmethod
    def validate_project(project_conf):
        """
        Args:
            project_conf (ConfigParser instance) - e.g. exmple/release-checklist/my_project.conf
        Returns:
            list - Empty list is no errors, otherwise list of strings describing issues
        """
        errors = []

        functions_list = [o for o in getmembers(
            md2workflow.validation.project_validation) if isfunction(o[1])]
        for func in functions_list:
            errors.extend(func[1](project_conf))
        return errors

    def handle_project(self, project_path):
        """
        Args
            project_conf (str) - A path to project config file
        """
        self.project_path = project_path

        self.project_conf = configparser.ConfigParser()
        self.project_conf.read(project_path)

        errors = self.validate_project(self.project_conf)
        if errors:
            self.logger.error(
                "Project conf contains errors. Please validate it first. Exiting")
            return

        backend = self.environment["global"]["backend"]
        if backend == "jira":
            import md2workflow.backend.jirabackend
            md2workflow.backend.jirabackend.handle_project(self)
        elif backend == "generic":
            import md2workflow.backend.genericbackend
            md2workflow.backend.genericbackend.handle_project(self)
        else:
            logger.error("Backend %s is not supported." % backend)
            raise NotImplementedError("Backend %s is not supported." % backend)


def main():
    parser = OptionParser(usage="%prog --jira-project PROJECT md_file")
    config_group = OptionGroup(parser, "Global configuration options")
    config_group.add_option(
        "--env",
        help="E.g. prod (as in prod.conf) or full path to a file. [Default: %s]." % DEFAULT_CONFIG_PATH,
        default=DEFAULT_CONFIG_PATH
    )
    parser.add_option_group(config_group)
    action_group = OptionGroup(parser, "Workflow action related options")
    action_group.add_option(
        "--update",
        help="Update workflow rather than create.",
        default=CliAction.CREATE,
        action="store_const",
        const=CliAction.UPDATE,
        dest="action"
    )
    parser.add_option_group(action_group)
    opts, args = parser.parse_args()
    if len(args) != 1:
        parser.error(
            "Expected exactly one argument which is path to the project config.")

    if not opts.env:
        parser.error("--env is mandatory")

    config_full_path = Cli.get_config_abspath(opts.env)
    if not config_full_path:
        parser.error("Please make sure that .conf file for env is stored in %s or %s. Or it's a path to actual file" % (
            USER_CONFIG_DIR, DEFAULT_CONFIG_DIR))

    if not os.path.exists(args[0]):
        parser.error("File %s does not exist" % args[0])

    environment = configparser.ConfigParser()

    #print("Using config %s" % config_full_path)
    environment.read(config_full_path)

    #print("Using project_conf %s" % args[0])
    project_conf = configparser.ConfigParser()
    project_conf.read(args[0])

    environment_errors = Cli.validate_config(environment)
    if environment_errors:
        print("ERROR: Found following md2workflow environment config issues:\n%s" % (
            "\n".join(environment_errors)))
        sys.exit(1)

    project_errors = Cli.validate_project(project_conf)
    if project_errors:
        print("ERROR: Found following md2workflow product issues:\n%s" %
              ("\n".join(project_errors)))
        sys.exit(2)

    client = Cli(environment, opts.action)
    client.handle_project(args[0])


if __name__ == "__main__":
    main()
