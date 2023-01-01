# tool_shape.py
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

import cairo, math
from .abstract_classic_tool import AbstractClassicTool
from .utilities_paths import utilities_smooth_path

class ToolShape(AbstractClassicTool):
	__gtype_name__ = 'ToolShape'

	SHAPE_TYPES = {
		'rectangle': _("Rectangle"),
		'roundedrect': _("Rounded rectangle"),
		'oval': _("Oval"),
		'circle': _("Circle"),
		'polygon': _("Polygon"),
		'freeshape': _("Free shape"),
	}

	OUTLINE_TYPES = {
		'solid': _("Solid outline"),
		'dashed': _("Dashed outline"),
		'none': _("No outline"),
	}

	FILLING_TYPES = {
		'empty': _("Empty shape"),
		# Context: fill a shape with the color of the left click
		'filled': _("Filled with main color"),
		# Context: fill a shape with the color of the right click
		'secondary': _("Filled with secondary color"),
		'h-gradient': _("Horizontal gradient"),
		'v-gradient': _("Vertical gradient"),
		'r-gradient': _("Radial gradient"),
	}

	def __init__(self, window, **kwargs):
		super().__init__('shape', _("Shape"), 'tool-freeshape-symbolic', window)
		self.use_operator = True

		self._reset_temp_points()

		self.add_tool_action_simple('shape_close', self._force_close_shape)
		self.set_action_sensitivity('shape_close', False)

		self.load_tool_action_enum('shape_type', 'last-active-shape')
		self._set_active_shape() # that's to initialize a consistent join_id too

		self._filling_id = self.load_tool_action_enum('shape_filling', \
		                                                   'last-shape-filling')

		self._outline_id = 'solid'
		self._outline_label = _("Solid outline")
		self.add_tool_action_enum('shape_outline', self._outline_id)

	def _reset_temp_points(self):
		self._path = None
		self.x_press = None
		self.y_press = None
		self.initial_x = None
		self.initial_y = None

	def get_tooltip(self, event_x, event_y, motion_behavior):
		if motion_behavior != 1:
			return None # no line is being drawn
		if self._shape_id in ['polygon', 'freeshpae']:
			return None # no tooltip for these shapes

		delta_x = abs(self.x_press - event_x)
		delta_y = abs(self.y_press - event_y)

		if self._shape_id == 'circle':
			length = round(math.sqrt(delta_x * delta_x + delta_y * delta_y), 2)
			return _("Radius: %spx") % length

		line1 = _("Width: %spx") % str(delta_x)
		line2 = _("Height: %spx") % str(delta_y)
		return line1 + "\n" + line2

	############################################################################

	def _set_filling_style(self):
		self._filling_id = self.get_option_value('shape_filling')

	def _set_outline_style(self):
		self._outline_id = self.get_option_value('shape_outline')

	def _set_active_shape(self, *args):
		self._shape_id = self.get_option_value('shape_type')
		if self._shape_id == 'rectangle' or self._shape_id == 'polygon':
			self._join_id = cairo.LineJoin.MITER
			# maybe BEVEL for polygon?
		else:
			self._join_id = cairo.LineJoin.ROUND

	def get_options_label(self):
		return _("Shape options")

	def get_editing_tips(self):
		self._set_active_shape()
		shape_name = self.SHAPE_TYPES[self._shape_id]

		label_options = shape_name
		self._set_filling_style()
		self._set_outline_style()
		if self._outline_id != 'solid':
			label_options += " - " + self.OUTLINE_TYPES[self._outline_id]
		if self._filling_id != 'empty':
			label_options += " - " + self.FILLING_TYPES[self._filling_id]

		if (self._shape_id == 'polygon' or self._shape_id == 'freeshape') and \
		                                                 self._path is not None:
			label_instruction = shape_name + " - " + \
			                  _("Click on the shape's first point to close it.")
		else:
			label_instruction = None
			self.set_action_sensitivity('shape_close', False)

		if self.get_image().get_mouse_is_pressed():
			label_modifiers = None
		else:
			label_modifiers = _("Press <Alt>, <Shift>, or both, to quickly " + \
			                                      "change the 'filling' option")

		full_list = [label_options, label_instruction, label_modifiers]
		return list(filter(None, full_list))

	def give_back_control(self, preserve_selection, next_tool=None):
		self.restore_pixbuf()
		self._reset_temp_points()
		return next_tool

	############################################################################

	def on_press_on_area(self, event, surface, event_x, event_y):
		self.last_mouse_btn = event.button
		self.set_common_values(self.last_mouse_btn, event_x, event_y)

		self.update_modifier_state(event.state)
		if 'SHIFT' in self._modifier_keys and 'ALT' in self._modifier_keys:
			self._filling_id = 'secondary'
		elif 'SHIFT' in self._modifier_keys:
			self._filling_id = 'empty'
			if self._outline_id == 'none':
				self._outline_id = 'solid'
		elif 'ALT' in self._modifier_keys:
			self._filling_id = 'filled'
			self._outline_id = 'none'

	def on_motion_on_area(self, event, surface, event_x, event_y, render=True):
		if self._shape_id == 'freeshape':
			operation = self._add_point(event_x, event_y, True)
		elif self._shape_id == 'polygon':
			operation = self._add_point(event_x, event_y, False)
		else:
			if self._shape_id == 'rectangle':
				self._draw_rectangle(event_x, event_y)
			elif self._shape_id == 'roundedrect':
				self._draw_roundedrect(event_x, event_y)
			elif self._shape_id == 'oval':
				self._draw_ellipse(event_x, event_y)
			elif self._shape_id == 'circle':
				self._draw_circle(event_x, event_y)
			operation = self.build_operation(self._path)
		if render:
			self.do_tool_operation(operation)

	def on_release_on_area(self, event, surface, event_x, event_y):
		if self._shape_id == 'freeshape' or self._shape_id == 'polygon':
			operation = self._add_point(event_x, event_y, True)
			self.set_action_sensitivity('shape_close', not operation['closed'])
			if operation['closed']:
				self.apply_operation(operation)
				self._reset_temp_points()
			else:
				self.do_tool_operation(operation)
				self.non_destructive_show_modif()
		else:
			if self._shape_id == 'rectangle':
				self._draw_rectangle(event_x, event_y)
			elif self._shape_id == 'roundedrect':
				self._draw_roundedrect(event_x, event_y)
			elif self._shape_id == 'oval':
				self._draw_ellipse(event_x, event_y)
			elif self._shape_id == 'circle':
				self._draw_circle(event_x, event_y)
			operation = self.build_operation(self._path)
			self.apply_operation(operation)
			self._reset_temp_points()

	############################################################################

	def _force_close_shape(self, *args):
		self.set_common_values(self.last_mouse_btn, self.x_press, self.y_press)
		self.on_release_on_area(None, None, self.initial_x, self.initial_y)

	def _add_point(self, event_x, event_y, memorize):
		"""Add a point to a shape (used by both freeshape and polygon)."""
		cairo_context = self.get_context()
		if self.initial_x is None:
			# print('init polygon')
			(self.initial_x, self.initial_y) = (self.x_press, self.y_press)
			cairo_context.move_to(self.x_press, self.y_press)
			self._path = cairo_context.copy_path()
		else:
			cairo_context.append_path(self._path)
		should_close = self._should_close_shape(event_x, event_y)
		if not should_close:
			# print('continue polygon')
			cairo_context.line_to(event_x, event_y)
		if memorize:
			# print('memorize polygon')
			self._path = cairo_context.copy_path()
		operation = self.build_operation(cairo_context.copy_path())
		operation['closed'] = should_close
		return operation

	def _should_close_shape(self, event_x, event_y):
		if self.initial_x is None or self.initial_y is None:
			return False
		delta_x = max(event_x, self.initial_x) - min(event_x, self.initial_x)
		delta_y = max(event_y, self.initial_y) - min(event_y, self.initial_y)
		closing_limit = max(2, self.tool_width)
		return (delta_x < closing_limit and delta_y < closing_limit)

	############################################################################

	def _draw_rectangle(self, event_x, event_y):
		cairo_context = self.get_context()
		cairo_context.move_to(self.x_press, self.y_press)
		cairo_context.line_to(self.x_press, event_y)
		cairo_context.line_to(event_x, event_y)
		cairo_context.line_to(event_x, self.y_press)
		cairo_context.close_path()
		self._path = cairo_context.copy_path()

	def _draw_roundedrect(self, event_x, event_y):
		cairo_context = self.get_context()
		a = min(self.x_press, event_x)
		b = max(self.x_press, event_x)
		c = min(self.y_press, event_y)
		d = max(self.y_press, event_y)
		radius = min(d - c, b - a) / 6 # c'est arbitraire
		pi2 = math.pi / 2
		cairo_context.arc(a + radius, c + radius, radius, 2 * pi2, 3 * pi2)
		cairo_context.arc(b - radius, c + radius, radius, 3 * pi2, 4 * pi2)
		cairo_context.arc(b - radius, d - radius, radius, 0 * pi2, 1 * pi2)
		cairo_context.arc(a + radius, d - radius, radius, 1 * pi2, 2 * pi2)
		cairo_context.close_path()
		self._path = cairo_context.copy_path()

	def _draw_ellipse(self, event_x, event_y):
		cairo_context = self.get_context()
		saved_matrix = cairo_context.get_matrix()

		halfw = int((self.x_press - event_x) / 2)
		halfh = int((self.y_press - event_y) / 2)
		# Ensure the matrix will be invertible
		if halfw == 0:
			halfw = 1
		if halfh == 0:
			halfh = 1
		cairo_context.translate(event_x + halfw, event_y + halfh)
		cairo_context.scale(halfw, halfh)
		cairo_context.arc(0, 0, 1, 0, 2 * math.pi)

		cairo_context.set_matrix(saved_matrix)
		cairo_context.close_path()
		self._path = cairo_context.copy_path()

	def _draw_circle(self, event_x, event_y):
		cairo_context = self.get_context()
		delta_x2 = (self.x_press - event_x) * (self.x_press - event_x)
		delta_y2 = (self.y_press - event_y) * (self.y_press - event_y)
		rayon = math.sqrt(delta_x2 + delta_y2)
		cairo_context.arc(self.x_press, self.y_press, rayon, 0.0, 2 * math.pi)
		self._path = cairo_context.copy_path()

	############################################################################

	def build_operation(self, cairo_path):
		pixelart_mode = self.get_image().is_zoomed_surface_sharp()
		operation = {
			'tool_id': self.id,
			'rgba_main': self.main_color,
			'rgba_secd': self.secondary_color,
			'antialias': self._use_antialias,
			'operator': self._operator,
			'line_join': self._join_id,
			'line_width': self.tool_width,
			'filling': self._filling_id,
			'outline': self._outline_id,
			'smooth': (self._shape_id == 'freeshape') and not pixelart_mode,
			'closed': True,
			'path': cairo_path
		}
		return operation

	def get_pattern_h(self, xmin, xmax):
		pattern = cairo.LinearGradient(xmin, 0.0, xmax, 0.0)
		return pattern

	def get_pattern_v(self, ymin, ymax):
		pattern = cairo.LinearGradient(0.0, ymin, 0.0, ymax)
		return pattern

	def get_pattern_r(self, center_x, center_y, rad):
		pattern = cairo.RadialGradient(center_x, center_y, 0.1 * rad, \
		                               center_x, center_y, 0.9 * rad)
		# the 2 centers could be 2 distinct points
		return pattern

	def _fill_pattern(self, cairo_context, pattern, c1, c2):
		"""Fill the shape defined in the context with a gradient from c1 to c2
		according to the given pattern. The colors are normalized arrays."""
		pattern.add_color_stop_rgba(0.1, *c1)
		pattern.add_color_stop_rgba(0.9, *c2)
		cairo_context.set_source(pattern)
		cairo_context.fill_preserve()

	def _fill_plain(self, cairo_context, color):
		"""Fill the shape defined in the context with the color c."""
		cairo_context.set_source_rgba(*color)
		cairo_context.fill_preserve()

	def do_tool_operation(self, operation):
		cairo_context = self.start_tool_operation(operation)

		line_width = operation['line_width']
		cairo_context.set_line_width(line_width)
		cairo_context.set_line_join(operation['line_join'])

		if operation['smooth']:
			utilities_smooth_path(cairo_context, operation['path'])
		else:
			cairo_context.append_path(operation['path'])
		if operation['closed']:
			cairo_context.close_path()

		cairo_context.set_operator(operation['operator'])
		color_main = operation['rgba_main']
		color_secd = operation['rgba_secd']

		filling = operation['filling']
		if filling == 'secondary':
			self._fill_plain(cairo_context, color_secd)
		elif filling == 'filled':
			self._fill_plain(cairo_context, color_main)
		elif filling == 'h-gradient':
			x1, y1, x2, y2 = cairo_context.path_extents()
			pattern = self.get_pattern_h(x1, x2)
			self._fill_pattern(cairo_context, pattern, color_main, color_secd)
		elif filling == 'v-gradient':
			x1, y1, x2, y2 = cairo_context.path_extents()
			pattern = self.get_pattern_v(y1, y2)
			self._fill_pattern(cairo_context, pattern, color_main, color_secd)
		elif filling == 'r-gradient':
			x1, y1, x2, y2 = cairo_context.path_extents()
			ddx = abs(x1 - x2) / 2
			ddy = abs(y1 - y2) / 2
			center_x = min(x1, x2) + ddx
			center_y = min(y1, y2) + ddy
			rad = max(ddx, ddy)
			pattern = self.get_pattern_r(center_x, center_y, rad)
			self._fill_pattern(cairo_context, pattern, color_main, color_secd)
		else: # filling == 'empty':
			pass

		outline = operation['outline']
		cairo_context.set_source_rgba(*color_main)
		if outline == 'dashed':
			cairo_context.set_dash([2 * line_width, 2 * line_width])
		if outline != 'none':
			cairo_context.stroke()

		# Reset the current path (maybe useful if no outline)
		cairo_context.new_path()

	############################################################################
################################################################################

