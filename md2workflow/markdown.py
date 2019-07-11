#!/usr/bin/env python

# -*- coding: utf-8 -*-

import logging
import re


class MarkDownObject(object):
    """A generic MarkDownObject"""

    def __init__(self):
        self.nodes = []
        self.__parent = None
        self._head = None
        self.logger = logging  # Please replace this while creating an instance

    @staticmethod
    def is_multiline():
        """
        Please change this only in case that this MarkdownObject can be defined
        over multiple lines
        """
        return False

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, obj):
        self.__parent = obj

    def add_node(self, node):
        """
        Args:
            node - One of MarkDown objects e.g. Heading1
        """
        if not self._head:  # first element
            node.parent = self  # document
            node.logger = self.logger
            self.nodes.append(node)
        # are we same level as last block?
        elif self._head.level == node.level:
            # Paragraphs are special, merge objects into ones
            # Since there is also Variable which has same level, we'll check all nodes on the level of head
            node.parent = self._head.parent
            merged = False
            if node.is_multiline():
                self.logger.debug(
                    "Markdown: Found multiline node %s" % repr(node))
                for child in node.parent.nodes:
                    self.logger.debug("Markdown: checking child %s multline=%s and type=%s" % (
                        repr(child), str(child.is_multiline()), type(child)))

                    if int(node.level) == (child.level) and child.is_multiline() and isinstance(child, node.__class__):
                        self.logger.debug("Markdown: merging nodes %s and %s" % (
                            repr(node), repr(child)))
                        child.merge(node)
                        self.logger.debug("Markdown: merged '%s'" % child.text)
                        merged = True
                        self.head = child
                        return
                    else:
                        self.logger.debug("Markdown: node %s doesn't match same level %d (%d) or type %s as child node %s" % (
                            repr(node), node.level, child.level, type(node), repr(child)))

            # Everything else should be simply appended to nodes
            if not node.is_multiline() or not merged:
                self.logger.debug("Markdown: Adding node %s to %s" %
                                  (repr(node), repr(self._head.parent)))
                self._head.parent.nodes.append(node)

        # are we lower (h2 < h1) level than last block?
        elif self._head.level < node.level:
            self.logger.debug("Markdown: Setting parent of %s to %s" %
                              (repr(node), repr(self._head)))
            node.parent = self._head
            self._head.nodes.append(node)

        elif self._head.level > node.level:
            while self._head.parent and self._head.level > node.level:
                self.logger.debug("Markdown: Moving head to parent lvl of node %d > current head %d" % (
                    node.level, self._head.level))
                if not self._head.parent:
                    self.logger.debug("Markdown: head.parent = None")
                self.logger.debug("Markdown: head.parent.level %d" %
                                  self._head.parent.level)
                self._head = self._head.parent

            self.logger.debug("Markdown: Setting parent of %s to %s" %
                              (repr(node), repr(self._head)))
            node.parent = self._head
            self._head.nodes.append(node)
        else:
            raise ValueError("This should not happen")

        # Always point head at latest added node
        self._head = node


class MarkDown(MarkDownObject):
    """
    This is a simply stupid parser of a simplified MarkDown file

    # h1
    ## h2
    ### h3
    #### h4
    ##### h5
    ###### h6
    variable: value
    text text
    """
    level = 0  # top level element / Document

    def read(self, fd):
        """
        Args:
            fd (file descriptor) - parse content of a file
        """
        while 1:
            line = fd.readline()
            if not line:
                break
            self.__handle_line(line)
        fd.close()

    def reads(self, text):
        """
        Args:
            text (str) - parse string
        """
        for line in text.splitlines():
            self.__handle_line(line)

    def __handle_line(self, line, previous_node=None):
        line = u"%s" % line  # ensure we're processing it in unicode works for both python2/python3
        if Heading.is_heading(line, self._head):
            self.logger.debug(
                "Markdown: Line '%s' was identified as heading" % line)
            self.add_node(Heading.from_markdown(line))

        elif Variable.is_variable(line, self._head):
            self.logger.debug(
                "Markdown: Line '%s' was identified as variable" % line)
            self.add_node(Variable.from_markdown(line))

        elif Paragraph.is_paragraph(line, self._head):
            self.logger.debug(
                "Markdown: Line '%s' was identified as paragraph" % line)
            self.add_node(Paragraph.from_markdown(line))
        else:
            self.logger.debug(
                "Markdown: Ignoring line as it didn't match any known type.'%s'" % line)


class Paragraph(MarkDownObject):
    level = 10

    def __init__(self, text=None, variables=None):
        super(Paragraph, self).__init__()
        self.__text = text or ""  # Basically a text including newline breaks

    @staticmethod
    def is_multiline():
        return True  # paragraphs support multiple lines, therefore nodes are merged

    @staticmethod
    def is_paragraph(data, previous_node=None):
        """
        Args:
            data (str or MarkDownObject)
            previous_node=None (MarkDownObject)
        Returns:
            Returns True if currently processed line of Markdown text is a paragraph
        """
        if isinstance(data, Paragraph):
            return True
        return (not Heading.is_heading(data, previous_node) and not Variable.is_variable(data, previous_node))

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, value):
        self.__text = value

    @staticmethod
    def from_markdown(text):
        return Paragraph(text)

    def merge(self, obj):
        """
        This function simply appends text of obj into itself.
        Stacking multiple paragraphs into self.nodes will result into only one Paragraph obj
        Args:
            obj (Paragraph)
        """
        if isinstance(obj, Paragraph):
            self.__text += "\n%s" % obj.text

    def __str__(self):
        return self.__text


class Variable(MarkDownObject):
    """
    Variable should be always node of a heading.
    In our case this applies for both node representing an epic, a task or a subtask

    Variable can contain letters, numbers underscore and space
    """
    level = Paragraph.level  # should be exactly same level as paragraph

    # so it's accessible from staticmethod as well
    __pattern = r'^([a-zA-z_0-9 ]+)\s*:\s*(.*)'

    def __init__(self, name, value):
        super(Variable, self).__init__()
        self.name = str(name)
        self.value = str(value)

    @staticmethod
    def is_variable(data, previous_node=None):
        """
        Args:
            data (str or Node)
            previous_node=None (MarkDownObject)
        Returns:
            Returns True if currently processed line of Markdown text is a variable: value
        """
        if isinstance(data, Variable):
            return True

        if re.search(Variable.__pattern, data):
            # Do not process "variable-like" lines in paragraph as variables
            if previous_node and Paragraph.is_paragraph(previous_node):
                return False
            return True

        return False

    @staticmethod
    def from_markdown(text):
        match = re.search(Variable.__pattern, text)
        if not match:
            raise ValueError("Expected a string 'name: value'")
        return Variable(match.groups(1)[0], match.groups(1)[1])

    def __str__(self):
        return self.name


class Heading(MarkDownObject):
    level = 1  # 1..6 # Default is 1

    @staticmethod
    def is_heading(data, previous_node=None):
        """
        Args:
            data (str or MarkDownObject)
        Returns:
            int : function returns non-zero if currently processed line of Markdown is a Heading
                  Returns number of heading characters e.g. 4 for h4. Returns 0 if it's not a heading.
                  Also returns 0 in case that N > 6
        """
        if isinstance(data, Heading):
            return data.level

        elif not isinstance(data, MarkDownObject):
             #  mentioned # in an open comment section of markdown file
            if isinstance(previous_node, Paragraph) and previous_node.text.count("```") % 2:
                return 0

            i = 0
            while i <= len(data) - 1 and data[i] == "#":
                i += 1

            if i > 6:  # H can be only 1..6.
                i = 0

            # HACK XXX: needs to be configurable. Process only heading 1 4 and 5
            # Rest should be treat as normal text
            if i not in (1, 4, 5):
                return 0
            # HACK XXX: People can easily add comments in code sections
            return i
        return 0

    def __init__(self, text=None):
        super(Heading, self).__init__()
        self.__nodes = []
        self.__text = None

        if text.startswith("#"):
            raise ValueError(
                "Unexpected # at the beginning of string. Please use .from_MarkDown() to parse heading from MarkDown instead.")

        self.text = text.strip()

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, value):
        self.__text = value

    def __str__(self):
        return self.__text

    @staticmethod
    def from_markdown(text):
        """
        Args:
            line (str): heading with MarkDown syntax
        Returns:
            automatically detects heading N and returns corresponding HeadingN object
        """
        lvl = Heading.is_heading(text)
        text = text[lvl:].strip()
        if not lvl:
            raise ValueError(
                ''"%s' was not recognized as a valid MarkDown heading." % text)
        if lvl == 1:
            return Heading1(text)
        elif lvl == 2:
            return Heading2(text)
        elif lvl == 3:
            return Heading3(text)
        elif lvl == 4:
            return Heading4(text)
        elif lvl == 5:
            return Heading5(text)
        elif lvl == 6:
            return Heading6(text)
        else:
            raise ValueError("Unexpected value %s" % lvl)

    def to_markdown(self):
        return "%s %s" % (self.level * "#", self)


class Heading1(Heading):
    level = 1


class Heading2(Heading):
    level = 2


class Heading3(Heading):
    level = 3


class Heading4(Heading):
    level = 4


class Heading5(Heading):
    level = 5


class Heading6(Heading):
    level = 6
