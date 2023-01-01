# tool_arc.py
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

import cairo
from .abstract_classic_tool import AbstractClassicTool
from .utilities_paths import utilities_add_arrow_triangle

class ToolArc(AbstractClassicTool):
	__gtype_name__ = 'ToolArc'

	def __init__(self, window, **kwargs):
		super().__init__('arc', _("Curve"), 'tool-arc-symbolic', window)
		self.use_operator = True

		# Default values
		self._cap_id = cairo.LineCap.ROUND
		self._1st_segment = None
		self._dashes_type = 'none'
		self._arrow_type = 'none'
		self._use_outline = False

		self.add_tool_action_enum('line_shape', 'round')
		self.add_tool_action_enum('dashes-type', self._dashes_type)
		self.add_tool_action_enum('arrow-type', self._arrow_type)
		self.add_tool_action_boolean('pencil-outline', self._use_outline)

	def give_back_control(self, preserve_selection, next_tool=None):
		self._1st_segment = None
		self.restore_pixbuf()
		return next_tool

	############################################################################
	# Options ##################################################################

	def set_active_shape(self):
		state_as_string = self.get_option_value('line_shape')
		if state_as_string == 'thin':
			self._cap_id = cairo.LineCap.BUTT
		else:
			self._cap_id = cairo.LineCap.ROUND

	def get_options_label(self):
		return _("Curve options")

	def get_editing_tips(self):
		self._use_outline = self.get_option_value('pencil-outline')
		self._dashes_type = self.get_option_value('dashes-type')
		self._arrow_type = self.get_option_value('arrow-type')
		self.set_active_shape()
		is_arrow = self._arrow_type != 'none'
		use_dashes = self._dashes_type != 'none'

		label_segments = self.label + " - "
		if self._1st_segment is not None:
			label_segments += _("Draw a second segment to complete the curve")
		else:
			label_segments = None

		label_options = self.label + " - "
		if is_arrow and use_dashes:
			label_options += _("Dashed arrow")
		elif is_arrow:
			label_options += _("Arrow")
		elif use_dashes:
			label_options += _("Dashed")
		else:
			label_options = None

		if self.get_image().get_mouse_is_pressed():
			label_modifier_alt = None
		else:
			label_modifier_alt = self.label + " - " + \
			                     _("Press <Alt> to toggle the 'outline' option")

		full_list = [label_segments, label_options, label_modifier_alt]
		return list(filter(None, full_list))

	############################################################################

	def on_press_on_area(self, event, surface, event_x, event_y):
		self.set_common_values(event.button, event_x, event_y)

		self.update_modifier_state(event.state)
		if 'ALT' in self._modifier_keys:
			self._use_outline = not self._use_outline

	def on_motion_on_area(self, event, surface, event_x, event_y, render=True):
		cairo_context = self.get_context()
		if self._1st_segment is None:
			cairo_context.move_to(self.x_press, self.y_press)
			cairo_context.line_to(event_x, event_y)
		else:
			cairo_context.move_to(self._1st_segment[0], self._1st_segment[1])
			cairo_context.curve_to(self._1st_segment[2], self._1st_segment[3], \
			                       self.x_press, self.y_press, event_x, event_y)
		self._path = cairo_context.copy_path()

		if not render:
			return
		operation = self.build_operation(event_x, event_y)
		self.do_tool_operation(operation)

	def on_release_on_area(self, event, surface, event_x, event_y):
		if self._1st_segment is None:
			self._1st_segment = (self.x_press, self.y_press, event_x, event_y)
			return
		else:
			cairo_context = self.get_context()
			cairo_context.move_to(self._1st_segment[0], self._1st_segment[1])
			cairo_context.curve_to(self._1st_segment[2], self._1st_segment[3], \
			                       self.x_press, self.y_press, event_x, event_y)
			self._1st_segment = None

		self._path = cairo_context.copy_path()
		operation = self.build_operation(event_x, event_y)
		self.apply_operation(operation)

	############################################################################

	def build_operation(self, event_x, event_y):
		operation = {
			'tool_id': self.id,
			'rgba': self.main_color,
			'rgba2': self.secondary_color,
			'antialias': self._use_antialias,
			'operator': self._operator,
			'line_width': self.tool_width,
			'line_cap': self._cap_id,
			'dashes': self._dashes_type,
			'arrow': self._arrow_type,
			'outline': self._use_outline,
			'path': self._path,
			'x_release': event_x,
			'y_release': event_y,
			'x_press': self.x_press,
			'y_press': self.y_press
		}
		return operation

	def do_tool_operation(self, operation):
		cairo_context = self.start_tool_operation(operation)

		cairo_context.set_operator(operation['operator'])
		line_width = operation['line_width']
		cairo_context.set_line_width(line_width)
		self.set_dashes_and_cap(cairo_context, line_width, \
		                             operation['dashes'], operation['line_cap'])

		if operation['arrow'] == 'double':
			for pts in operation['path']:
				# how to do without a for???
				if(pts[0] == cairo.PathDataType.MOVE_TO):
					x1 = pts[1][0]
					y1 = pts[1][1]
				else:
					x2 = pts[1][0]
					y2 = pts[1][1]
			utilities_add_arrow_triangle(cairo_context, x1, y1, x2, y2, line_width)

		cairo_context.append_path(operation['path'])

		if operation['arrow'] != 'none':
			x1 = operation['x_press']
			y1 = operation['y_press']
			x2 = operation['x_release']
			y2 = operation['y_release']
			utilities_add_arrow_triangle(cairo_context, x2, y2, x1, y1, line_width)

		if operation['outline']:
			cairo_context.set_source_rgba(*operation['rgba2'])
			cairo_context.set_line_width(line_width * 1.2 + 2)
			cairo_context.stroke_preserve()

		cairo_context.set_line_width(line_width)
		cairo_context.set_source_rgba(*operation['rgba'])
		cairo_context.stroke()

	############################################################################
################################################################################

