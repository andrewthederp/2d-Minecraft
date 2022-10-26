import pygame
from misc import *

class Stick:
	name = 'stick'
	slot_image = get_item_image('stick')
	data = {'type':'crafting'}

	def __init__(self, *, level):
		self.image = self.slot_image.copy()

	def on_right_click(self, *args, **kwargs):
		return False

class WoodenPickaxe:
	name = 'wooden pickaxe'
	slot_image = get_item_image('wooden_pickaxe')
	data = {'type':'tool', 'tool_type':'pickaxe', 'material':'wood'}

	def __init__(self, *, level):
		self.image = self.slot_image.copy()

	def on_right_click(self, *args, **kwargs):
		return False

class WoodenAxe:
	name = 'wooden axe'
	slot_image = get_item_image('wooden_axe')
	data = {'type':'tool', 'tool_type':'axe', 'material':'wood'}

	def __init__(self, *, level):
		self.image = self.slot_image.copy()

	def on_right_click(self, *args, **kwargs):
		return False

class WoodenShovel:
	name = 'wooden shovel'
	slot_image = get_item_image('wooden_shovel')
	data = {'type':'tool', 'tool_type':'shovel', 'material':'wood'}

	def __init__(self, *, level):
		self.image = self.slot_image.copy()

	def on_right_click(self, *args, **kwargs):
		return False




class StonePickaxe:
	name = 'stone pickaxe'
	slot_image = get_item_image('stone_pickaxe')
	data = {'type':'tool', 'tool_type':'pickaxe', 'material':'stone'}

	def __init__(self, *, level):
		self.image = self.slot_image.copy()

	def on_right_click(self, *args, **kwargs):
		return False

class StoneAxe:
	name = 'stone axe'
	slot_image = get_item_image('stone_axe')
	data = {'type':'tool', 'tool_type':'axe', 'material':'stone'}

	def __init__(self, *, level):
		self.image = self.slot_image.copy()

	def on_right_click(self, *args, **kwargs):
		return False

class StoneShovel:
	name = 'stone shovel'
	slot_image = get_item_image('stone_shovel')
	data = {'type':'tool', 'tool_type':'shovel', 'material':'stone'}

	def __init__(self, *, level):
		self.image = self.slot_image.copy()

	def on_right_click(self, *args, **kwargs):
		return False
