# md2workflow

Markdown To Workflow. A tool which can convert typically "VCS managed" mardown checklist into e.g. a linked structure of Jira Epics.
Tool can not only create checklists, but also update them!

## Get the tool and data

**Tool requires python-jira**

```

setup.py install # if you use virtualenv

# Install Dependencies on openSUSE
zypper install python2-jira python3-jira # based on your system

# Install Dependencies on Fedora
yum install python2-jira python3-jira

# Get tool from git
git clone https://github.com/lkocman/md2workflow.git
```

## How does it work?

Tool parses a project configuration (.ini) file, which is mapping individual markdown files to predefined workflows (e.g. Jira Epics).
Tasks are defined in the depic

JIRA Epic name is taken from the configuration section and tasks are simply Heading4 (####) from the markdown file, subtasks would be Heading5 (#####)
The project configuration file can also define workflow/epic level dependencies.

The markdown file is suppose to contain only 1 Workflow/Epic at the time.
You can also skip H1 (heading) in the markdown file, jira will still create Epic for you.

Tool can create (default) and also --update existing.


### Update existing Jira workflow

Update means to create a new task (in case of summary and product mismatch) or update existing (description, issue links).
Update is applied on tasks in states defined in configuration. States of both Epic and task affect whether it can be updated.

These need to be updated to match the instance configuration.

**If your update is failing on "missing tasks" in already resolved epic, then please temporarily remove these epic references
from your project file.** 

This can typically happen if closed tasks were renamed and there is a new dependency on given task in already resolved Epic.

```
[jira]
...
update_states = Open, Backlog
epic_update_states = Open, Backlog, In Progress
```

### Variable in tasks

Lines after heading (H1/H4/H5) with following syntax are identified as variables.

```
#### My Task
Some Variable: Some Value

This is a description of the example My Task. Task has a variable.

##### My Sub Task
Some Variable: Some Value

This is a description of the example Subtask My Sub Task, which is a subtask of My Task. Task has also a variable.
``` 

These variables have further use in inter-task relations and ownership (Blocks: My Task, Responsible: team_name, ...)
Ownership syntax is set by default by "Responsible: $GROUP". (Variable name can be changed in config)
Tool supports setting various group assignees and therefore assign issues to a particular person.

#### Text subsitution in task body.

Both ${Project} and ${Product} in task description get expanded to the value of relevant JIRA field  (see mapping_Product).
${Epic} gets replaced by the Epic name. 

```
#### My Task
Some Variable: Some Value

This ${Product} ${Epic} gets expanded into e.g. "Suse Linux Enterprise Server 15 Beta 2"
Where Beta 2 is the Epic name. This is specific only to the jira backend.
```


## Configuration

If you just cloned the tool, the configuration files are located in the example directory.
Tool uses two files as an input. 

### Environment config
Is an .ini file which holds information about backend (e.g. jira or generic)
and instance specific configuration, custom fields etc.  It's supplied by the --env option

```
bin/md2workflow --env $ENV # e.g. local, jira-example or config/local.conf
```

The tool is looking up for following locations for the env file in given order.
You do not need to specify full config name (e.g. --env examples/local.conf) but rather just --env local

Lookup order
* Path passed to command line (e.g --env /tmp/env.conf)
* ~/.md2workflow/
* example directory of the git checkout
* /etc/md2workflow/
* config resources from setup.py


### Project config

Project config (an .ini file) which defines the workflow by combining data from linked markdown files.
It's passed to the tool as an argument not an option.

```
md2workflow --env $ENV /path/to/your/project_config.conf
```

#### Example project config 
```
$ cat md2workflow/example/my_project.conf 
[project]
name = My cool product 1.0

[ownership]
markdown_variable = Responsible
build = lkocman
pm = lkocman
qa = lkocman
rel-mgmt = lkocman
scc = lkocman


[Project config]
markdown_filename = project_config.md

[Alpha phase]
Depends on = Project config
markdown_filename = alpha.md

[Alpha 1]
Implements = Alpha phase
markdown_filename = repetitiveTasksForMilestones.md

[Beta Phase]
Depends on = Alpha Phase
markdown_filename = beta.md

[Beta 1]
Implements = Beta Phase
markdown_filename = repetitiveTasksForMilestones.md

[Public Beta]
Implements = Beta Phase
Depends on = Beta 1
markdown_filename = repetitiveTasksForMilestones.md

[Beta 2]
Implements = Beta Phase
Depends on = Public Beta
markdown_filename = repetitiveTasksForMilestones.md

[RC]
markdown_filename = rc.md
Depends on = Beta 2

[GA]
Depends on = RC
markdown_filename = ga.md
```

## Example execution

### Hello World 

This is a Local dry-run of example config (using backend=generic)
Consider this a Hello World in md2workfow

```
bin/md2workflow --env config/local.conf example/my_project.conf # or simply --env local
```

### Creating or updating checklist in Jira

Following is descibing simple workflow of how was the tool intended to use.
Perpaps think of that the first two runs are executed before change request to markdown files is done.
And update to production is done with already merged changes.

```
# First check if dryrun of your project works, this catches any syntax issues
bin/md2workflow --env config/local.conf example/my_project.conf # or simply --env local

# Deploy on devel instance (if you have one), perhaps after cleanup of existing data
bin/md2workflow --env jira-devel example/my_project.conf 

# Update existing checklist on production instance
bin/md2workflow --env jira-prod --update example/my_project.conf
```

## Test coverage

You can execute pytest in the project directory to execute the unittest suite.

```
md2workflow$ pytest
======================================== test session starts =========================================
platform linux2 -- Python 2.7.16, pytest-3.10.1, py-1.8.0, pluggy-0.12.0
rootdir: /home/lkocman/Workspace/snowflow/md2workflow, inifile:
collected 37 items                                                                                   

tests/test_cli.py .....                                                                        [ 13%]
tests/test_jirabackend.py .                                                                    [ 16%]
tests/test_markdown.py ................                                                        [ 59%]
tests/test_workflow.py ...............                                                         [100%]

===================================== 37 passed in 0.20 seconds ======================================
```
