# -*- coding: utf-8 -*-

import csv
from optparse import OptionParser

import md2workflow.markdown as markdown

class RedmineFields(object):
    ID = 0
    Project = 1
    Tracker = 2
    Parent_task = 3
    Status = 4
    Priority = 5
    Subject = 6
    Author = 7
    Assignee = 8
    Updated = 9
    Category = 10
    Target_version = 11
    Start_date = 12
    Due_date = 13
    Estimated_time = 14
    Spent_time = 15
    progress_Done = 16
    Created = 17
    Closed = 18
    Related_issues = 19
    Private = 20
    Description = 21

def process_row(row, markdown_parser, opts, logger):
    """
    Nodes are in a tree structure
    H1 is essentially epic, H4 task, H5 subtask.
    Every heading can have paragraph and md2workflow custom variables
    """
    # This needs to point to respective parent Markdown Parser obj H1/H4/H5
    # This is important for the recursive print as the tree defines the order
    head = markdown_parser
    logger.debug("Current HEAD: %s, nodes: %s" % (head, [str(n) for n in head.nodes]))

    task_name = row[RedmineFields.Subject]

    # Target Version is treated as a Heading1
    # Ensure that when we end the block the HEAD points to matching H1
    if row[RedmineFields.Target_version]:
        target_version = row[RedmineFields.Target_version]
    else:
        target_version = "Unsorted" # This would otherwise make quite a mess in Markdown

    logger.debug("Target version: %s" % target_version)
    if opts.target_version and target_version not in opts.target_version:
        logger.debug("Skipping target_version %s due to --target-version=%s" % (target_version, opts.target_version))
        return

    for node in markdown_parser.nodes:
        logger.debug("Looking for existing H1 with value %s. Found: %s" % (target_version, str(node)))
        if str(node) == target_version:
            head = node
            logger.debug("Found match for target_version: %s" % (target_version))
            break

    if str(head) != target_version: # Is head on the matching H1?
        logger.debug("Did not find existing Heading 1 with value %s" % target_version)
        parent = head
        head = markdown.Heading1(target_version) # Set Head to H1
        logger.debug("Creating new H1 node: %s" % str(head))
        parent.add_node(head)
        logger.debug("Current HEAD: %s, nodes: %s" % (head, [str(n) for n in head.nodes]))


    # Task creation
    ## Are we task or subtask?
    logger.debug("Current HEAD: %s, nodes: %s" % (head, [str(n) for n in head.nodes]))
    logger.debug("Creating task %s" % task_name)
    task_heading_node = markdown.Heading4(task_name)
    if row[RedmineFields.Parent_task]:
        # Example parent_task name string
        # action #61320: update opensuse wiki
        parent_task_name = row[RedmineFields.Parent_task]
        parent_task_name = parent_task_name[parent_task_name.find(':'):]

        logger.debug("Task %s has parent %s" % (task_name, parent_task_name))
        # point head to matching task
        # keep in mind we're already pointing on the right parent of the task (H1)
        # subtasks can't have any more sub-sub-tasks
        logger.debug("Looking for a parent of %s. HEAD=%s" % (task_name, str(head)))
        for task_node in head.nodes:
            logger.debug("Comparing node='%s' with parent_task_name='%s'" % (str(task_node), parent_task_name))
            if str(task_node) == parent_task_name:
                head = task_node
                break
        ## Use H5 instead (sub-task)
        task_heading_node = markdown.Heading5(task_name)

    # Variables
    if row[RedmineFields.Assignee]:
        task_heading_node.add_node(markdown.Variable("Responsible", row[RedmineFields.Assignee]))

    # Description
    task_heading_node.add_node(markdown.Paragraph(row[RedmineFields.Description]))

    # Add task
    head.add_node(task_heading_node) # rest of nodes are nodes of task_heading

def handle_csv_export(csv_export_path, opts, logger):
    """
    Args:
        csv_export_path (str) - path to csv file with dump from redmine
        opts (OptionParser opts) - dictionary containing passed options

    Expected CSV format is following
    ['#', 'Project', 'Tracker', 'Parent task', 'Status', 'Priority', 'Subject',
    'Author', 'Assignee', 'Updated', 'Category', 'Target version', 'Start date',
    'Due date', 'Estimated time', 'Spent time', '% Done', 'Created', 'Closed',
    'Related issues', 'Private', 'Description']

    """
    # XXX - utf-8 returned
    # UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb9 in position 3625: invalid start byte
    # mac_roman seems to pass ...

    markdown_parser = markdown.MarkDown()
    with open(csv_export_path, encoding="mac_roman", newline="") as csvfile:
        csv_reader = csv.reader(csvfile, dialect=csv.Dialect.doublequote)
        line_no = 0
        for row in csv_reader:
            if line_no == 0:
                line_no += 1
                continue # skip initial heading

            logger.debug("Line %d %s" % (line_no, str(row)))
            process_row(row, markdown_parser, opts, logger)
        line_no += 1

    # Solely for debugging of the tree structure
    logger.debug("Tree summary: %s" % ([str(n) for n in markdown_parser.nodes]))
    for h1 in markdown_parser.nodes:
        logger.debug("%s, %s" % (h1, [str(n) for n in h1.nodes]))
        if not h1.nodes:
            continue
        for h4 in h1.nodes:
            logger.debug("%s, %s" % (h4, [str(n) for n in h4.nodes]))
        if not h4.nodes:
            continue
        for h5 in h4.nodes:
            logger.debug("%s, %s" % (h5, [str(n) for n in h5.nodes]))

    # Recursive print out
    if not opts.no_print:
        markdown_parser.print_markdown_tree()

def get_optparse():
    parser = OptionParser(usage="%prog [options] your-redmine-export.csv")
    parser.add_option("--debug", action="store_true")
    parser.add_option(
        "--no-print",
        action="store_true",
        help="Do not print the actual markdown."
    )
    parser.add_option(
        "--target-version",
        action="append",
        help="Process only specific Redmine Target version E.g. Alpha. No Target version can be specified as 'Unsorted'",
    )

    return parser
