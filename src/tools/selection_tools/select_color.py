# select_color.py
#
# Copyright 2018-2023 Romain F. T.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from .abstract_select import AbstractSelectionTool
from .utilities_colors import utilities_get_rgba_name, \
                              utilities_gdk_rgba_from_xy, \
                              utilities_gdk_rgba_to_hexadecimal
from .utilities_paths import utilities_get_magic_path

class ToolColorSelect(AbstractSelectionTool):
	__gtype_name__ = 'ToolColorSelect'

	def __init__(self, window, **kwargs):
		# Context: this is a tool to "magically" select an area depending on its
		# color. For example clicking on a white pixel will select the
		# surrounding area made of white pixels.
		super().__init__('color_select', _("Color selection"), 'tool-magic-symbolic', window)

	def get_tooltip(self, event_x, event_y, motion_behavior):
		color = utilities_gdk_rgba_from_xy(self.get_surface(), event_x, event_y)
		if color is None:
			return None
		color_name = utilities_get_rgba_name(color)
		color_code = utilities_gdk_rgba_to_hexadecimal(color)
		return color_name + "\n" + color_code

	def get_editing_tips(self):
		tips = super().get_editing_tips()
		if not self.selection_is_active():
			label_warning1 = self.label + " - " + _("May not work for complex shapes")
			tips.append(label_warning1)
			label_warning2 = self.label + " - " + _("It will not work well " + \
				                               "if the area's edges are blurry")
			tips.append(label_warning2)
		return tips

	############################################################################

	def press_define(self, event_x, event_y):
		pass

	def motion_define(self, event_x, event_y, render):
		pass

	def release_define(self, surfc, event_x, event_y):
		path = utilities_get_magic_path(surfc, event_x, event_y, self.window, 1)
		self._pre_load_path(path)
		if path is None:
			return
		self.operation_type = 'op-define'
		operation = self.build_operation()
		self.apply_operation(operation)

	############################################################################
################################################################################

