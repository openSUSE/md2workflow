# -*- coding: utf-8 -*-

import requests
import icalendar

PROJECT_CONFIG_SECTION="schedule"
PROJECT_CONFIG_ATTR="calendar_url"
MARKDOWN_VARIABLE="Calendar"

class ProjectSchedule(object):
    def __init__(self):
        self._calendar = icalendar.Calendar()

    def from_url(self, url):
        """
        Args
            url (str) - url or path to ical/ics file

        Reads icalendar data from url or path
        """
        if url.startswith("http://") or url.startswith("https://"):
            self._calendar = self._calendar.from_ical(requests.get(url).text)
        else:
            self.__from_path(url)

    def __from_path(self, path):
        """
        Args
            path (str) - path to ical/ics file

        Reads icalendar data from path. Do not use this directly.
        """
        fd=open(path, "r")
        content=fd.read()
        fd.close()
        self._calendar = self._calendar.from_ical(content)

    def event_by_name(self, name):
        """
        Args
            name (str) - string matchig summary of ical/ics event

        Returns the first icalendar subcomponent matching name (vevent) or None
        """
        if not self._calendar:
            return None

        for vevent in self._calendar.subcomponents:
            if vevent["SUMMARY"] == name:
                return vevent
        return None

    def start_end_by_name(self, name):
        """
        Args
            name (str) - string matchig summary of ical/ics event

        Returns the first tuple with two datetime objects or None
        """
        if not self._calendar:
            return None

        vevent = self.event_by_name(name)
        if vevent:
            return (vevent.decoded("dtstart"), vevent.decoded("dtend"))
        return None
