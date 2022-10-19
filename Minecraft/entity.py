import pygame, os, time
from settings import *
from misc import *

pygame.init()

class Entity(pygame.sprite.Sprite):
	def __init__(self, image, rect, *, level, groups):
		super().__init__(groups)

		self.image = image
		self.rect = rect.copy()

		# movement
		self.direction = pygame.math.Vector2(0, .5)

		self.jumping = False
		self.speed = 0
		self.falling = False

		# misc
		self.level = level
		self.obstacles_sprites = level.obstacles_sprites


	def collision(self, direction): # make sure the entity is not doing wall hacks
		if direction == 'horizontal': # right-left
			for sp in self.obstacles_sprites:
				if sp.rect.colliderect(self.rect):
					if self.falling or self.jumping: # if the entity is in the air simply do normal collisions 
						if self.direction.x > 0:
							self.rect.right = sp.rect.left
							return 0

						if self.direction.x < 0:
							self.rect.left = sp.rect.right
							return 1
					else:
						sp.rect.y += 33 # move the block down 33 pixels, if the entity no longer collides with it then we don't do collision
						group = pygame.sprite.GroupSingle(sp)
						sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask)
						sp.rect.y -= 33 # reset the block's position

						if sprite: # the block still collides, let's do collision
							# TODO: check if the entity goes to the top of this block if it will collide with any other blocks
							if self.direction.x > 0:
								self.rect.right = sprite.rect.left
								group.empty()
								return 0

							if self.direction.x < 0:
								self.rect.left = sprite.rect.right
								group.empty()
								return 1
		if direction == 'vertical': # up-down
			for sprite in self.obstacles_sprites:
				if sprite.rect.colliderect(self.rect):
					group = pygame.sprite.GroupSingle(sprite)
					if self.direction.y > 0: # the entity is jumping, this is in case the entity attempts to jump into an upper half of a slab for example
						sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask)
						if sprite:
							while True:
								self.rect.y -= 1
								sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask)
								if not sprite:
									break
						else:
							self.rect.y += 1
						return 0

					if self.direction.y < 0: # the entity is falling, this is in case the entity falls into the bottom half of a slab for example
						sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask)
						if sprite:
							while True:
								self.rect.y += 1
								sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask)
								if not sprite:
									break
						else:
							self.rect.y -= 1
						return 1

	def jump(self, power): # the lower the power the higher the jump
		if not self.jumping and not self.falling: # no double jumping in my game >:(
			self.direction.y = power
			self.jumping = True

	def apply_gravity(self): # although this may be implied, this does not actually move the player. It simply makes sure the variables are correct
		if self.jumping:
			if self.direction.y < 0:
				self.direction.y += .6

				self.collision('vertical')
				collide = False
				for sprite in self.obstacles_sprites:
					if sprite.rect.bottom in range(self.rect.top, self.rect.bottom) and self.rect.right > sprite.rect.left and self.rect.left < sprite.rect.right: # is the player jumping into a block?
						collide = True
						break
				if collide: # end the jump prematurely
					self.direction.y = 1
					self.falling = True
					self.jumping = False
			else: # end the jump normally
				self.direction.y = 1
				self.jumping = False
				self.falling = True
		else: # if we're not jumping then we're falling)
			self.collision('vertical')
			collide = False
			self.rect.y += 1 # if you're at the top of the block then it wouldn't consider you colliding so we have to push the player a pixel down
			for sprite in self.obstacles_sprites:
				if sprite.rect.top in range(self.rect.top, self.rect.bottom+1) and self.rect.right > sprite.rect.left and self.rect.left < sprite.rect.right:
					group = pygame.sprite.GroupSingle(sprite)
					sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask) # we have to make sure that the player is colliding with the sprite not the rect
					if sprite:
						collide = True
						group.empty()
						break
			self.rect.y -= 1

			if collide: # we're no longer falling nor jumping, here is where we will calculate fall damage
				self.direction.y = 1
				self.falling = False
			else:
				self.falling = True
				if self.direction.y < 30: # cap the falling speed at 30
					self.direction.y += .6


	def move(self): # make sure the player is moving correctly
		# for _ in range(self.speed):
		self.rect.x += self.direction.x*self.speed
		self.collision('horizontal')
		self.rect.y += self.direction.y
		self.collision('vertical')
		self.coor = [self.rect.x, self.rect.y]

	def update(self):
		pass

class DroppedEntity(Entity): # when a block is broken, this comes too existence
	def __init__(self, obj, image, rect, *, level, thrown=False):
		self.obj = obj

		# Hovering
		self.hover = 0
		self.hover_up = True

		# Picking up cooldown
		self.can_be_picked = 60 # 60 frames, 1 seconds if running at 60 fps

		super().__init__(image, rect, level=level, groups=[level.dropped_entities, level.visible_sprites])

		# # Movement
		# self.speed = 5
		# if thrown: # For future me
		# 	pos = pygame.mouse.get_pos()
		# 	angle = calculate_angle(self.level.player.rect.center, pos)
		# 	fx, _ = calculate_force(angle, 35)
		# 	self.speed = fx

		# 	self.direction.x = -1 if 0 > fx else 1





	def edit_rects(self):
		if self.hover_up:
			self.hover -= .3
			if self.hover <= -15:
				self.hover_up = False
		else:
			self.hover += .3
			if self.hover >= 0:
				self.hover_up = True

	def pickup(self):
		if self.can_be_picked <= 0 and self.rect.colliderect(self.level.player.pickup_range):
			self.kill()
			self.level.player.add_item(self.obj)

	def update(self):
		self.can_be_picked -= 1

		# if not (self.falling or self.jumping):
		# 	self.speed = 0
		# elif self.speed < 0 and self.direction.x > 0:
		# 	self.speed = 0
		# elif self.speed > 0 and self.direction.x < 0:
		# 	self.speed = 0
		# else:
		# 	self.speed -= 1

		self.pickup()
		self.apply_gravity()
		self.move()
		self.edit_rects()