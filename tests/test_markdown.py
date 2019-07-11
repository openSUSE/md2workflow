#!/usr/bin/env python

# -*- coding: utf-8 -*-

import pytest
import md2workflow.markdown as markdown


def test_heading_fm():
    for x in (1, 4, 5):  # 1..6
        text = "%s test" % (int(x) * "#")
        h = markdown.Heading.from_markdown(text)
        assert str(h) == "test"


def test_invalid_h7_fm():
    with pytest.raises(ValueError):
        markdown.Heading.from_markdown("####### test")


def test_invalid_h0_fm():
    with pytest.raises(ValueError):
        markdown.Heading.from_markdown("test")


def test_heading():
    heading = markdown.Heading("test")
    heading.text = "test"


def test_heading2md():
    heading = markdown.Heading("test")
    assert heading.to_markdown() == "# test"  # Just like Heading1

    heading = markdown.Heading1("test h1")
    assert heading.to_markdown() == "# test h1"

    heading = markdown.Heading4("test h4")
    assert heading.to_markdown() == "#### test h4"

    heading = markdown.Heading5("test h5")
    assert heading.to_markdown() == "##### test h5"


def test_heading_line_end_too_soon():
    assert markdown.Heading.is_heading("#")
    assert not markdown.Heading.is_heading("##")
    assert not markdown.Heading.is_heading("###")
    assert markdown.Heading.is_heading("####")
    assert markdown.Heading.is_heading("#####")
    assert not markdown.Heading.is_heading("######")
    assert not markdown.Heading.is_heading("#######")


def test_paragraph():
    raw = "line\nline2"
    para = markdown.Paragraph(raw)
    assert para.text == raw


def test_reads_md_single_heading():
    raw = "# test h1"
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 1
    assert isinstance(md.nodes[0], markdown.Heading1)
    assert md.nodes[0].text == "test h1"


def test_reads_md_h1_h2():
    raw = "# test h1\n## test h2"  # [h1.h2,]
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 1
    assert isinstance(md.nodes[0], markdown.Heading1)
    assert md.nodes[0].text == "test h1"
    assert len(md.nodes[0].nodes) == 1
    assert isinstance(md.nodes[0].nodes[0], markdown.Paragraph)
    assert md.nodes[0].nodes[0].text == "## test h2"


def test_reads_md_h1_h1():
    raw = "# test h1\n# test h1.1"  # [h1, h1]
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 2
    assert isinstance(md.nodes[0], markdown.Heading1)
    assert md.nodes[0].text == "test h1"
    assert isinstance(md.nodes[1], markdown.Heading1)
    assert md.nodes[1].text == "test h1.1"


def test_reads_md_h1_h1_para():
    raw = "# test h1\n# test h1.1\nparagraph test"  # [h1, h1]
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 2
    assert isinstance(md.nodes[0], markdown.Heading1)
    assert md.nodes[0].text == "test h1"

    assert len(md.nodes[0].nodes) == 0
    assert isinstance(md.nodes[1], markdown.Heading1)
    assert md.nodes[1].text == "test h1.1"

    assert len(md.nodes[1].nodes) == 1
    assert isinstance(md.nodes[1].nodes[0], markdown.Paragraph)
    assert md.nodes[1].nodes[0].text == "paragraph test"


def test_reads_para_para():
    raw = "paragraph test\nparagraph 2 test"  # [h1, h1]
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 1  # expected to be merged into a single Paragraph
    assert isinstance(md.nodes[0], markdown.Paragraph)
    assert md.nodes[0].text == raw  # should be unchanged


def test_recognize_variable():
    examples = ["variable: test",
                "variable : test 2",
                "variable 3 : test 3",
                "variable_4: test"]

    for eg in examples:
        assert markdown.Variable.is_variable(
            eg), "'%s' is not recognized as a Variable" % eg


def test_process_variable():
    """
    Check the Markdown tree which contains variable definitions if it matches with expectations
    """
    raw = "# test h1\n#### test task\nvar: value\ndescription\n"
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 1 and isinstance(md.nodes[0], markdown.Heading1)
    assert len(md.nodes[0].nodes) == 1 and isinstance(
        md.nodes[0].nodes[0], markdown.Heading4)
    assert len(md.nodes[0].nodes[0].nodes) == 2
    assert isinstance(md.nodes[0].nodes[0].nodes[0], markdown.Variable)
    assert isinstance(md.nodes[0].nodes[0].nodes[1], markdown.Paragraph)

    assert not md.nodes[0].nodes[0].nodes[0].nodes
    assert not md.nodes[0].nodes[0].nodes[1].nodes


def test_process_variables():
    """
    Check the Markdown tree which contains multiple variable definitions if it matches with expectations
    """
    raw = "# test h1\n#### test task\nvar: value\nvar2: value\ndescription\n"
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 1 and isinstance(md.nodes[0], markdown.Heading1)
    assert len(md.nodes[0].nodes) == 1 and isinstance(
        md.nodes[0].nodes[0], markdown.Heading4)
    assert len(md.nodes[0].nodes[0].nodes) == 3

    # TODO: Better to check whether the order of childs isn't random but this seem to work

    assert isinstance(md.nodes[0].nodes[0].nodes[0], markdown.Variable)
    assert isinstance(md.nodes[0].nodes[0].nodes[1], markdown.Variable)
    assert isinstance(md.nodes[0].nodes[0].nodes[2], markdown.Paragraph)

    assert not md.nodes[0].nodes[0].nodes[0].nodes
    assert not md.nodes[0].nodes[0].nodes[1].nodes
    assert not md.nodes[0].nodes[0].nodes[2].nodes


def test_process_subtask():
    """
    Check the Markdown tree if it matches with expectations
    """
    raw = "# test h1\n#### test task\ndescription\n##### test subtask\ndescription\n"
    md = markdown.MarkDown()
    md.reads(raw)
    assert len(md.nodes) == 1 and isinstance(md.nodes[0], markdown.Heading1)
    print "second", md.nodes[0].nodes
    assert len(md.nodes[0].nodes) == 1 and isinstance(
        md.nodes[0].nodes[0], markdown.Heading4)
    assert len(md.nodes[0].nodes[0].nodes) == 2

    # TODO: Better to check whether the order of childs isn't random but this seem to work
    assert isinstance(md.nodes[0].nodes[0].nodes[0], markdown.Paragraph)
    assert isinstance(md.nodes[0].nodes[0].nodes[1], markdown.Heading5)

    assert not md.nodes[0].nodes[0].nodes[0].nodes
    assert len(md.nodes[0].nodes[0].nodes[1].nodes) == 1 and isinstance(
        md.nodes[0].nodes[0].nodes[1].nodes[0], markdown.Paragraph)
    assert not md.nodes[0].nodes[0].nodes[1].nodes[0].nodes
