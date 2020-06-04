# -*- coding: utf-8 -*-

import pytest
import os
import configparser
import logging
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO
import csv


import md2workflow.conversion.redmine_csv as redmine_csv
import md2workflow.markdown as markdown

# Tasks 2 and 4 are subtasks
# Epics are Alpha, Beta, RC
# rest of info is dummy
# Task and Subtask for Alpha, Task and Subtask for Beta, Only one Task for RC

def test_headings1():
    content=StringIO("""#,Project,Tracker,Parent task,Status,Priority,Subject,Author,Assignee,Updated,Category,Target version,Start date,Due date,Estimated time,Spent time,% Done,Created,Closed,Related issues,Private,Description
1,My Project,action,,Status,Priority,Test task 1,lkocman,lkocman,Updated,Category,Alpha,Start date,Due date,Estimated time,Spent time,% Done,Created,Closed,Related issues,Private,Task 1 Description
2,My Project,action,Test task 1,Status,Priority,Test task 2,lkocman,lkocman,Updated,Category,Alpha,Start date,Due date,Estimated time,Spent time,% Done,Created,Closed,Related issues,Private,Task 2 Description
3,My Project,action,,Status,Priority,Test task 3,lkocman,lkocman,Updated,Category,Beta,Start date,Due date,Estimated time,Spent time,% Done,Created,Closed,Related issues,Private,Task 3 Description
4,My Project,action,Test task 3,Status,Priority,Test task 4,lkocman,lkocman,Updated,Category,Beta,Start date,Due date,Estimated time,Spent time,% Done,Created,Closed,Related issues,Private,Task 4 Description
5,My Project,action,Parent task,Status,Priority,Test task 5,lkocman,lkocman,Updated,Category,RC,Start date,Due date,Estimated time,Spent time,% Done,Created,Closed,Related issues,Private,Task 5 Description""")

    markdown_parser = markdown.MarkDown()
    parser = redmine_csv.get_optparse()
    parser.add_option("--ignore", action="append") # pytest injected
    opts, args = parser.parse_args()

    csv_reader = csv.reader(content, dialect=csv.Dialect.doublequote)
    line_no=0
    for row in csv_reader:
        if line_no == 0:
            line_no += 1
            continue # skip initial heading
        redmine_csv.process_row(row, markdown_parser, opts, logging)

    assert len(markdown_parser.nodes) == 3 # Alpha, Beta, RC
    assert str(markdown_parser.nodes[0]) == "Alpha"
    assert str(markdown_parser.nodes[1]) == "Beta"
    assert str(markdown_parser.nodes[2]) == "RC"

    # Alpha
    assert len(markdown_parser.nodes[0].nodes) == 1 # 1 Epic Task
    assert len(markdown_parser.nodes[0].nodes[0].nodes) == 3 # 1 Epic Task -> 1 Subtask (consisting of 3 markdown nodes)

    ## Heading
    assert str(markdown_parser.nodes[0].nodes[0]) == "Test task 1"

    ## Variable
    assert markdown_parser.nodes[0].nodes[0].nodes[0].name == "Responsible"
    assert markdown_parser.nodes[0].nodes[0].nodes[0].value == "lkocman"

    ## Description / Paragraph
    assert str(markdown_parser.nodes[0].nodes[0].nodes[1]) == "Task 1 Description"

    ## Subtask heading node (children node)
    assert str(markdown_parser.nodes[0].nodes[0].nodes[2]) == "Test task 2"

    ## Subtask Variable
    assert markdown_parser.nodes[0].nodes[0].nodes[2].nodes[0].name == "Responsible"
    assert markdown_parser.nodes[0].nodes[0].nodes[2].nodes[0].value == "lkocman"

    ## Subtask description / Paragraph
    assert str(markdown_parser.nodes[0].nodes[0].nodes[2].nodes[1]) == "Task 2 Description"

    # Beta
    assert len(markdown_parser.nodes[1].nodes) == 1 # 1 Epic Task
    assert len(markdown_parser.nodes[1].nodes[0].nodes) == 3 # 1 Epic Task -> 1 Ttask (consisting of 3 markdown nodes)

    ## Heading
    assert str(markdown_parser.nodes[1].nodes[0]) == "Test task 3"

    ## Variable
    assert markdown_parser.nodes[1].nodes[0].nodes[0].name == "Responsible"
    assert markdown_parser.nodes[1].nodes[0].nodes[0].value == "lkocman"

    ## Description / Paragraph
    assert str(markdown_parser.nodes[1].nodes[0].nodes[1]) == "Task 3 Description"

    ## Subtask heading node (children node)
    assert str(markdown_parser.nodes[1].nodes[0].nodes[2]) == "Test task 4"

    ## Subtask Variable
    assert markdown_parser.nodes[1].nodes[0].nodes[2].nodes[0].name == "Responsible"
    assert markdown_parser.nodes[1].nodes[0].nodes[2].nodes[0].value == "lkocman"

    ## Subtask description / Paragraph
    assert str(markdown_parser.nodes[1].nodes[0].nodes[2].nodes[1]) == "Task 4 Description"

    # RC
    assert len(markdown_parser.nodes[2].nodes) == 1 # 1 Epic Task
    assert len(markdown_parser.nodes[2].nodes[0].nodes) == 2 # Description and Variable

    assert markdown_parser.nodes[2].nodes[0].nodes[0].name == "Responsible"
    assert markdown_parser.nodes[2].nodes[0].nodes[0].value == "lkocman"
    assert str(markdown_parser.nodes[2].nodes[0].nodes[1]) == "Task 5 Description"
