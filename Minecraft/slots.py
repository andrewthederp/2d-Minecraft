import pygame, os, random, copy
from settings import *
import blocks, items


class Slot:
	def __init__(self, *, level, player, obj=None):
		self.change_item(obj)
		self.level = level
		self.player = player

		self.xy = tuple()
		self.rect = None
		self.location = ''

	def __repr__(self):
		return f'<Slot name="{self.slot_name}" amount={self.amount}>'

	def from_name(name, **kwargs):
		name = str(name)
		try:
			obj = getattr(blocks, name)((0,0), [], level=kwargs.get('level'))
		except AttributeError:
			try:
				obj = getattr(items, name)(level=kwargs.get('level'))
			except AttributeError:
				return Slot(**kwargs, obj=None)
		return Slot(**kwargs, obj=obj)

	@property
	def amount(self):
		return self._amount
	@amount.setter
	def amount(self, value):
		self._amount = value
		self.display_amount = value

	def copy(self):
		s = Slot(player=self.player, level=self.level, obj=self.obj)
		s.amount = self.amount
		return s

	def change_item(self, obj):
		if obj:
			self.obj = obj
			self.slot_name = obj.name
			self._amount = 1
			self.display_amount = 1

			self.image = obj.slot_image
			self.slot_data = obj.data
		else:
			self.obj = None
			self.slot_name = ''
			self._amount = 0
			self.display_amount = 0
			self.slot_data = dict()

			self.image = pygame.Surface((32,32)).convert_alpha()
			self.image.fill((0,0,0,0))

	def change_coor(self, x, y):
		self.xy = (x, y)

	def change_rect(self, rect):
		self.rect = rect

	def change_location(self, location):
		self.location = location

	def on_right_click(self, mouse_pos):
		if self.amount > 0:
			del_obj = self.obj.on_right_click(mouse_pos)
			if del_obj:
				self.amount -= 1

			if self.amount <= 0:
				self.change_item(None)

			return del_obj