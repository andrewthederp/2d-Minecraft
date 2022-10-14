import pygame
from player import Player, PlayerDraw
from debug import debug
from settings import *
import blocks
from entity import *
from misc import *
from threading import Thread
import time

class Level:
	def __init__(self):

		self.screen = pygame.display.get_surface()

		self.sky = Sky()

		self.start_dt = int(time.time())
		self.zoom = 1

		blocks.on_init_blocks()
		self.create_map()
		self.tick()

	def create_map(self):

		self.visible_sprites = Camera(self)
		self.obstacles_sprites = pygame.sprite.Group()
		self.falling_sprites = pygame.sprite.Group()
		self.dropped_entities = pygame.sprite.Group()

		conversion_dict = {'d':blocks.Dirt, 'g':blocks.Grass, 's':blocks.Sand, 'w':blocks.OakLog, 'l':blocks.OakLeaves, 'S':blocks.Stone, 'c':blocks.CobbleStone}

		x, y = player_starting_coor[0] * TILE_SIZE, player_starting_coor[1] * TILE_SIZE
		groups = {
			'obstacles_sprites':self.obstacles_sprites,
			'visible_sprites': self.visible_sprites,
			'falling_sprites': self.falling_sprites,
			'dropped_entities': self.dropped_entities
		}
		self.player = Player((x, y), [self.visible_sprites], groups, level=self)
		self.player_draw = PlayerDraw(self.player)

		for row_index, row in enumerate(WORLD_COPY):
			for col_index, col in enumerate(row):
				x = col_index * TILE_SIZE
				y = row_index * TILE_SIZE

				block = conversion_dict.get(col)
				if block:
					groups = [self.obstacles_sprites,self.visible_sprites]
					if getattr(block, 'fall', False):
						groups.append(self.falling_sprites)
					block = block((x, y), groups, level=self)

				WORLD_MAP[row_index][col_index] = block

	def get_neighbours(self, x, y):
		for x_ in (x-1, x, x+1):
			for y_ in (y-1, y, y+1):
				try:
					WORLD_MAP[y_][x_]
					yield x_, y_
				except IndexError:
					pass

	def tick(self):
		def inner_func():
			self.falling_sprites.update()
			while pygame.display.get_surface():

				pressing_block = self.player.pressing_block
				if pressing_block:
					self.player.pressing_block.tick()

				self.player.tick()
				time.sleep(FPS/300)
		thread = Thread(target=inner_func)
		thread.start()

	def drop(self, obj, image, rect):
		Entity(obj, image, rect, level=self, groups=[self.visible_sprites, self.dropped_entities])

	def run(self, events):
		self.events = events
		for event in events:
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_r and event.mod == 4160:
					self.create_map()
					self.player.rect.x = player_starting_coor[0] * TILE_SIZE
					self.player.rect.y = player_starting_coor[1] * TILE_SIZE
					self.zoom = 1

		dt = int(time.time()) - self.start_dt
		if dt >= FULL_DAY:
			self.start_dt = int(time.time())

		# keys_pressed = pygame.key.get_pressed()
		# if keys_pressed[pygame.K_EQUALS]:
		# 	self.zoom = min(self.zoom+.1, 2)
		# elif keys_pressed[pygame.K_MINUS]:
		# 	self.zoom = max(self.zoom-.1, .5)

		"""zooming isn't really worth it"""

		self.visible_sprites.update()
		self.visible_sprites.custom_draw(surface=self.screen, width=WIDTH, height=HEIGHT, zoom=self.zoom, max_zoom=2, center=self.player.rect.center)
		self.sky.display(dt)
		self.player_draw.draw()
		debug(self.zoom, x=WIDTH-50)

class Sky:
	def __init__(self):
		self.display_surface = pygame.display.get_surface()
		self.full_surf = pygame.Surface((WIDTH, HEIGHT))
		self.color = pygame.Color((255,255,255))
		self.night_color = pygame.Color((10,10,30))
		self.day_color = pygame.Color((255,255,255))

	def display(self, dt):
		if dt <= HALF_DAY:
			percent = dt/HALF_DAY
			col = self.day_color.lerp(self.night_color, percent)
		else:
			percent = (dt-HALF_DAY)/HALF_DAY
			col = self.night_color.lerp(self.day_color, percent)

		self.full_surf.fill(col)
		self.display_surface.blit(self.full_surf, (0,0), special_flags=pygame.BLEND_RGBA_MULT)

class Camera(pygame.sprite.Group):
	def __init__(self, level):
		super().__init__()

		self.offset = pygame.math.Vector2()


	def custom_draw(self, surface, *, width, height, zoom=1, max_zoom=1, **kwargs):
		rect = pygame.Rect((0,0), (width * max_zoom-zoom, height * max_zoom-zoom))
		for key, value in kwargs.items():
			setattr(rect, key, value)

		self.offset.x = (rect.centerx*zoom) - width * .5
		self.offset.y = (rect.centery*zoom) - height * .5

		# visible_x_range = int(self.offset.x)//TILE_SIZE, ((int(self.offset.x)+WIDTH)//TILE_SIZE)+1
		# visible_y_range = int(self.offset.y)//TILE_SIZE, ((int(self.offset.y)+HEIGHT)//TILE_SIZE)+1

		for sprite in self.sprites():
			pos_x = sprite.rect.x//TILE_SIZE
			pos_y = sprite.rect.y//TILE_SIZE
			if sprite.rect.colliderect(rect):
				if zoom != 1:
					x, y = sprite.rect.topleft
					offset_pos =  (x * zoom, y * zoom) - self.offset
					w, h = sprite.image.get_size()
					image = pygame.transform.scale(sprite.image, (w*zoom, h*zoom))
				else:
					offset_pos =  sprite.rect.topleft - self.offset
					image = sprite.image
				surface.blit(image, offset_pos)