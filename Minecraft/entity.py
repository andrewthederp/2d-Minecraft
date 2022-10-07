import pygame, os
from settings import *

pygame.init()

class Entity(pygame.sprite.Sprite):
	def __init__(self, obj, image, rect, *, level, groups):
		super().__init__(groups)

		self.obj = obj
		self.image = image
		self.real_rect = rect
		self.rect = rect.copy()

		self.direction = pygame.math.Vector2(0, .5)

		self.level = level

		self.hover = 0
		self.hover_up = True

	def collision(self):
		for sprite in self.level.player.obstacles_sprites:
			if sprite != self and sprite.rect.colliderect(self.real_rect):
				self.direction.y = .5
				self.real_rect.bottom = sprite.rect.top
				return

	def apply_gravity(self):
		self.collision()

		if self.direction.y < 15:
			self.direction.y += .2

	def move(self):
		self.real_rect.y += self.direction.y
		self.collision()

	def edit_rects(self):
		self.rect.center = self.real_rect.center
		self.rect.y += self.hover

		if self.hover_up:
			self.hover -= .2
			if self.hover <= -10:
				self.hover_up = False
		else:
			self.hover += .2
			if self.hover >= 0:
				self.hover_up = True

	def update(self):
		self.apply_gravity()
		self.move()
		self.edit_rects()