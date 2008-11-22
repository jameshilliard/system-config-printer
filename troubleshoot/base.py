#!/usr/bin/env python

## Printing troubleshooter

## Copyright (C) 2008 Red Hat, Inc.
## Copyright (C) 2008 Tim Waugh <twaugh@redhat.com>

## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.

## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.

## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import gobject
import gtk
import subprocess
from gettext import gettext as _
from debug import *

__all__ = [ 'gtk',
            '_',
            'debugprint', 'get_debugging', 'set_debugging',
            'Question',
            'Multichoice',
            'TEXT_start_print_admin_tool',
            'TimedSubprocess' ]

TEXT_start_print_admin_tool = _("To start this tool, select "
                                "System->Administration->Printing "
                                "from the main menu.")

class Question:
    def __init__ (self, troubleshooter, name=None):
        self.troubleshooter = troubleshooter
        if name:
            self.__str__ = lambda: name

    def display (self):
        """Returns True if this page should be displayed, or False
        if it should be skipped."""
        return True

    def connect_signals (self, handler):
        pass

    def disconnect_signals (self):
        pass

    def can_click_forward (self):
        return True

    def collect_answer (self):
        return {}

    ## Helper functions
    def initial_vbox (self, title='', text=''):
        vbox = gtk.VBox ()
        vbox.set_border_width (12)
        vbox.set_spacing (12)
        if title:
            s = '<span weight="bold" size="larger">' + title + '</span>\n\n'
        else:
            s = ''
        s += text
        label = gtk.Label (s)
        label.set_alignment (0, 0)
        label.set_line_wrap (True)
        label.set_use_markup (True)
        vbox.pack_start (label, False, False, 0)
        return vbox

class Multichoice(Question):
    def __init__ (self, troubleshooter, question_tag, question_title,
                  question_text, choices, name=None):
        Question.__init__ (self, troubleshooter, name)
        page = self.initial_vbox (question_title, question_text)
        choice_vbox = gtk.VBox ()
        choice_vbox.set_spacing (6)
        page.pack_start (choice_vbox, False, False, 0)
        self.question_tag = question_tag
        self.widgets = []
        for choice, tag in choices:
            button = gtk.RadioButton (label=choice)
            if len (self.widgets) > 0:
                button.set_group (self.widgets[0][0])
            choice_vbox.pack_start (button, False, False, 0)
            self.widgets.append ((button, tag))

        troubleshooter.new_page (page, self)

    def collect_answer (self):
        for button, answer_tag in self.widgets:
            if button.get_active ():
                return { self.question_tag: answer_tag }

class TimedSubprocess:
    def __init__ (self, timeout=60000, parent=None, **args):
        self.subp = subprocess.Popen (**args)
        self.output = dict()
        self.io_source = []
        self.watchers = 2
        self.timeout = timeout
        self.parent = parent
        for f in [self.subp.stdout, self.subp.stderr]:
            source = gobject.io_add_watch (f,
                                           gobject.IO_IN |
                                           gobject.IO_HUP |
                                           gobject.IO_ERR,
                                           self.watcher)
            self.io_source.append (source)

        self.wait_window = None

    def run (self):
        self.timeout_source = gobject.timeout_add (self.timeout,
                                                   self.do_timeout)
        self.wait_source = gobject.timeout_add (1000, self.show_wait_window)
        gtk.main ()
        self.io_source.extend ([self.timeout_source, self.wait_source])
        for source in self.io_source:
            gobject.source_remove (source)
        if self.wait_window != None:
            self.wait_window.destroy ()
        return (self.output.get (self.subp.stdout, '').split ('\n'),
                self.output.get (self.subp.stderr, '').split ('\n'),
                self.subp.poll ())

    def do_timeout (self):
        gtk.main_quit ()
        return False

    def watcher (self, source, condition):
        if condition & gobject.IO_IN:
            buffer = self.output.get (source, '')
            buffer += source.read ()
            self.output[source] = buffer

        if condition & gobject.IO_HUP:
            self.watchers -= 1
            if self.watchers == 0:
                gtk.main_quit ()
                return False

        return True

    def show_wait_window (self):
        wait = gtk.Window ()
        if self.parent:
            wait.set_transient_for (self.parent)
        wait.set_modal (True)
        wait.set_position (gtk.WIN_POS_CENTER_ON_PARENT)
        wait.set_border_width (12)
        wait.set_title (_("Please wait"))
        vbox = gtk.VBox ()
        wait.add (vbox)
        label = gtk.Label (_("Gathering information"))
        vbox.pack_start (label)
        wait.show_all ()
        self.wait_window = wait
        return False
