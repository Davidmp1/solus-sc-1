#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  groups.py - SSC Group Navigation
#  
#  Copyright 2014 Ikey Doherty <ikey.doherty@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
# 
import gi.repository
from gi.repository import Gtk, GObject

import pisi.api
from widgets import PackageLabel

class GroupsView(Gtk.VBox):

    __gsignals__ = {
        'group-selected': (GObject.SIGNAL_RUN_FIRST, None,
                          (object,)),
        'package-selected': (GObject.SIGNAL_RUN_FIRST, None,
                          (object,object))
    }
    
    def __init__(self, groups, packagedb, installdb, basket):
        Gtk.VBox.__init__(self)

        self.packagedb = packagedb
        self.installdb = installdb
        self.basket = basket
        
        self.grid = Gtk.FlowBox()

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_UP_DOWN)
        self.stack.add_named(self.grid, "groups")

        self.packages_list = Gtk.ListBox()
        placeholder = Gtk.Label("<big>Searching</big>")
        self.placeholder = placeholder
        placeholder.set_use_markup(True)
        placeholder.get_style_context().add_class("dim-label")
        self.packages_list.set_placeholder(placeholder)
        placeholder.show_all()
        self.packages_list.connect("row-activated", self._selected)
        self.scroller = Gtk.ScrolledWindow(None, None)
        self.scroller.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.scroller.add(self.packages_list)
        self.stack.add_named(self.scroller, "packages")

        self.pack_start(self.stack, True, True, 0)
        
        self.groupdb = groups
        group_names = self.groupdb.list_groups()
        max_columns = int(len(group_names) / 2)

        self.grid.set_border_width(40)
        self.grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.grid.set_row_spacing(0)
        self.grid.set_valign(Gtk.Align.START)

        self.packages = list()

        self.do_reset()

        self.show_all()
        self.packages_list.set_sort_func(self.sort, None)

    def build_groups(self):
        for kid in self.grid.get_children():
            kid.destroy()

        for group_name in self.groupdb.list_groups():
            group = self.groupdb.get_group(group_name)
            components = self.groupdb.get_group_components(group_name)
            if len(components) == 0:
                continue
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            label = Gtk.Label("<big>%s</big>\n%d categories" % (str(group.localName), len(components)))
            label.set_use_markup(True)
            label.set_justify(Gtk.Justification.LEFT)
            label.set_halign(Gtk.Align.START)
            image = Gtk.Image()
            image.set_from_icon_name(group.icon, Gtk.IconSize.INVALID)
            image.set_pixel_size(64)

            btn_layout = Gtk.HBox()
            btn.add(btn_layout)
            btn_layout.pack_start(image, False, False, 0)
            image.set_halign(Gtk.Align.START)
            btn_layout.pack_start(label, True, True, 0)
            label.set_halign(Gtk.Align.START)
            label.set_margin_left(10)
            btn.key_word = group
            btn.connect("clicked", lambda x: self.emit('group-selected', x.key_word))
            #btn.set_halign(Gtk.Align.CENTER)
            btn.set_hexpand(False)
            btn.set_vexpand(False)
            btn.set_valign(Gtk.Align.START)
            self.grid.add(btn)
        self.grid.show_all()

    def searching(self, entry, event=None):
        text = entry.get_text().strip()
        if text == "":
            self.stack.set_visible_child_name("groups")
        else:
            self.stack.set_visible_child_name("packages")
            self.packages_list.set_filter_func(self.filter, text)
            
            res = False
            for child in self.packages_list.get_children():
                if child.get_visible() and child.get_child_visible():
                    res = True
                    break
            if not res:
                self.placeholder.set_markup("<big>Sorry, no results</big>")
            else:
                self.placeholder.set_markup("<big>Searching</big>")

    def filter(self, row, text):
        child = row.get_children()[0]
        package = child.package
        
        if text in package.name or text in str(package.summary).lower():
            return True
        return False

    def _selected(self, box, row):
        if row is None:
            return
        child = row.get_children()[0]

        self.emit('package-selected', child.package, child.old_package)

    def sort(self, row1, row2, data=None):
        package1 = row1.get_children()[0].package
        package2 = row2.get_children()[0].package

        return cmp(package1.name, package2.name)
        
    def rebuild_all_packages(self, data=None):
        for child in self.packages_list.get_children():
            child.destroy()
        self.build_groups()
        for pkg in pisi.api.list_available():
            package = self.packagedb.get_package(pkg)
            old_package = self.installdb.get_package(pkg) if self.installdb.has_package(pkg) else None

            status = self.basket.operation_for_package(package)
            panel = PackageLabel(package, old_package, interactive=True)
            panel.sig_id = panel.connect('operation-selected', self.op_select)
            panel.mark_status(status)
            self.packages_list.add(panel)
            self.packages_list.show_all()
            while (Gtk.events_pending()):
                Gtk.main_iteration()

    def op_select(self, package_label, operation, package, old_package):
        if operation == 'INSTALL':
            self.basket.install_package(package)
        elif operation == 'UNINSTALL':
            self.basket.remove_package(old_package)
        elif operation == 'UPDATE':
            self.basket.update_package(old_package, package)
        elif operation == 'FORGET':
            self.basket.forget_package(package)
            
    def do_reset(self):
        GObject.idle_add(self.rebuild_all_packages)
