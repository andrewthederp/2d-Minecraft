import pygame, os, copy, time, json
import time
from settings import *
from misc import *
import random
from slots import Slot

pygame.init()

def round_to_nearest(num, ndigit=10):
	return round(num/ndigit)*ndigit


def on_init_blocks():
	global breaking_dict, screen, tool_mults

	tool_mults = {None:1, 'wood':2, 'stone':4, 'iron':6, 'diamond':8, 'netherite':9, 'gold':12}

	breaking_dict = {}

	for name in ('16.png', '32.png', '48.png', '64.png', '80.png', '96.png'):
		path = os.path.join(asset_path, name)
		img = pygame.image.load(path).convert_alpha()
		breaking_dict[name] = img

	screen = pygame.display.get_surface()

def change_block_image(self, original_image):
	self.original_image = original_image
	self.image = original_image.copy()
	self.mask = pygame.mask.from_surface(self.image)

def default_on_right_click(self, mouse_pos, groups, class_=None):
	class_ = class_ or self.__class__
	x, y = int(mouse_pos[0]//TILE_SIZE), int(mouse_pos[1]//TILE_SIZE)
	try:
		if not self.level.chunk_list.get_at(*mouse_pos, convert=True):
			can_build = False
			for x_, y_ in self.level.get_neighbours(x, y):
				if self.level.chunk_list.get_at(y_, x_):
					can_build = True
					break
			if not can_build:
				return False

			x_, y_ = x*TILE_SIZE, y*TILE_SIZE
			# groups = [self.level.obstacles_sprites,self.level.visible_sprites]
			block = class_((x_, y_), groups, level=self.level)
			# for group in groups:
			# 	group.add(self)

			self.level.chunk_list.set_at(block, y, x)
			return block
		return False
	except IndexError:
		return False

class BreakableBlock:
	def __init__(self, groups):
		super().__init__(groups)
		self.start_mine_time = float('inf')

		self.image = self.original_image.copy()

		self.last_use = 0

	def on_left_click(self):
		self.start_mine_time = time.time()

		tool = get_slot_player_holding(self.level.player)
		is_best_tool = self.best_tool in tool.slot_data.values()
		material = tool.slot_data.get("material")
		can_harvest = set(k for k, v in tool_mults.items() if v >= tool_mults[self.min_harvest])
		self.mine_cooldown = get_break_time(
			block_hardness=self.hardness,
			is_best_tool=is_best_tool,
			tool_multiplier=tool_mults[material],
			can_harvest=material in can_harvest,
			# tool_efficiency=False,
			# efficiency_level=1,
			# haste_effect=False,
			# haste_level=1,
			# mining_fatigue=False,
			# mining_fatigue_level=1,
			# in_water=False,
			# has_aqua_affinity=False
		)

	def on_left_release(self):
		self.image = self.original_image.copy()
		self.start_mine_time = float('inf')

	def break_tick(self, on_break):
		if self.start_mine_time != float('inf'):
			current_time = time.time()
			mined_time = (current_time-self.start_mine_time)
			if (self.level.player.falling or self.level.player.jumping):
				mined_time //= 5

			percent = (mined_time/self.mine_cooldown)*100
			if percent != -(float('inf')):
				if self.last_use-time.time() <= -.1:
					self.level.player_draw.item_used()
					self.last_use = time.time()
				num = round_to_nearest(percent, 16)
				image = breaking_dict.get(str(num)+'.png')
				if image:
					self.image = self.original_image.copy()
					self.image.blit(image, (0,0))

			if mined_time >= self.mine_cooldown:
				self.on_left_release()
				self.kill()

				if on_break:
					on_break()

				x, y = self.rect.x//TILE_SIZE, self.rect.y//TILE_SIZE
				self.level.chunk_list.set_at(None, self.rect.x, self.rect.y, convert=True)

class FallingBlock:
	def __init__(self, groups):
		super().__init__(groups)

		self.direction = pygame.math.Vector2(0, .5)
		self.falling = False

	def collision(self):
		for sprite in self.level.player.obstacles_sprites:
			if sprite != self and sprite.rect.colliderect(self.rect):
				self.direction.y = .5
				self.rect.bottom = sprite.rect.top
				self.falling = False
				return
		self.falling = True

	def apply_gravity(self):
		self.collision()

		if self.direction.y < 15:
			self.direction.y += .1

	def move(self):
		self.rect.y += self.direction.y
		self.collision()

		if self.falling:
			x, y = self.rect.x // TILE_SIZE, self.rect.y // TILE_SIZE
			self.level.chunk_list.set_at(None, y, x)
		else:

			x, y = self.rect.x // TILE_SIZE, self.rect.y // TILE_SIZE
			self.level.chunk_list.set_at(self, y, x)


class Dirt(BreakableBlock, pygame.sprite.Sprite):
	name = 'dirt'

	slot_image = get_item_image('dirt')

	hardness = .5
	best_tool = 'shovel'
	min_harvest = None
	data = {'type':'block'}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('dirt', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)
		
		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		self.level.drop(self, self.slot_image, rect)
	
	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)


class Grass(BreakableBlock, pygame.sprite.Sprite):
	name = 'grass block'

	slot_image = get_item_image('grass_block')

	hardness = .6
	best_tool = 'shovel'
	min_harvest = None
	data = {'type':'block'}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('grass_block', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		obj = Dirt((0,0), [], level=self.level)
		rect = obj.slot_image.get_rect(center=self.rect.center)
		self.level.drop(obj, obj.slot_image, rect)

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)

	def random_tick(self):
		x,y = self.rect.topleft
		blocks = []
		for x_ in range(x-TILE_SIZE, x+TILE_SIZE, TILE_SIZE):
			for y_ in range(y-TILE_SIZE*2, y+TILE_SIZE*2, TILE_SIZE):
				blocks.append(self.level.chunk_list.get_at(x=x_, y=y_, convert=True))

		for _ in range(4):
			block = random.choice(blocks)
			if block:
				block_above = self.level.chunk_list.get_at(x=block.left, y=block.top-64, convert=True)
				if not block_above and block.name == 'dirt':
					block.kill()
					b = Grass(block.rect.topleft, self.groups(), level=block.level)
					self.level.chunk_list.set_at(b, *block.rect.topleft, convert=True)

class Sand(FallingBlock, BreakableBlock, pygame.sprite.Sprite):
	name = 'sand'
	fall = True

	slot_image = get_item_image('sand')

	hardness = .5
	best_tool = 'shovel'
	min_harvest = None
	data = {'type':'block'}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('sand', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.apply_gravity()
		self.move()
		self.break_tick(self.on_break)

	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		self.level.drop(self, self.slot_image, rect)

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites,self.level.falling_sprites]
		return default_on_right_click(self, mouse_pos, groups)


class OakLog(BreakableBlock, pygame.sprite.Sprite):
	name = 'oak log'

	slot_image = get_item_image('oak_log')

	hardness = 2
	best_tool = 'axe'
	min_harvest = None
	data = {'type':'block', 'fuel':True, 'smeltable': True}


	def __init__(self, pos, groups, *, level):
		self.original_image = get_block_image('oak_log', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		self.level.drop(self, self.slot_image, rect)

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)


class OakPlank(BreakableBlock, pygame.sprite.Sprite):
	name = 'oak plank'

	slot_image = get_item_image('oak_plank')

	hardness = 2
	best_tool = 'axe'
	min_harvest = None
	data = {'type':'block', 'two slabs':False, 'fuel':True}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('oak_plank', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		if self.data['two slabs']:
			obj1 = OakSlab(rect.center, [], level=self.level)
			# obj2 = OakSlab(rect.center, [], level=self.level)

			self.level.drop(obj1, obj1.slot_image, rect)
			self.level.drop(obj1, obj1.slot_image, rect)
			# self.level.drop(obj2, obj2.slot_image, rect)
		else:
			self.level.drop(self, self.slot_image, rect)

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)

class OakStairs(BreakableBlock, pygame.sprite.Sprite):
	name = 'oak stairs'

	slot_image = get_item_image('oak_stairs')

	hardness = 2
	best_tool = 'axe'
	min_harvest = None
	data = {'type':['block','stairs'], 'upside-down':False, 'looking-right':True, 'fuel':True}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('oak_stairs', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		self.level.drop(self, self.slot_image, rect)

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		x = mouse_pos[0]/TILE_SIZE
		y, _y = divmod(mouse_pos[1], TILE_SIZE)
		x, y = int(x), int(y)

		player_left = self.level.player.rect.left

		self.data['looking-right'] = player_left < mouse_pos[0]
		self.data['upside-down']   = _y < 32

		original_image = pygame.transform.flip(self.original_image, self.data['looking-right'], self.data['upside-down'])

		try:
			if not self.level.chunk_list.get_at(y, x):
				can_build = False
				for x_, y_ in self.level.get_neighbours(x, y):
					if self.level.chunk_list.get_at(y_, x_):
						can_build = True
						break
				if not can_build:
					return False

				x_, y_ = x*TILE_SIZE, y*TILE_SIZE
				block = self.__class__((x_, y_), groups, level=self.level)
				change_block_image(block, original_image)

				self.level.chunk_list.set_at(block, y, x)
				return True
			return False
		except IndexError:
			return False


class OakSlab(BreakableBlock, pygame.sprite.Sprite):
	name = 'oak slab'

	slot_image = get_item_image('oak_slab')

	hardness = 2
	best_tool = 'axe'
	min_harvest = None
	data = {'type':['block', 'slab'], 'stair_like':True, 'on_top':False, 'fuel':True}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('oak_slab', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		self.level.drop(self, self.slot_image, rect)

	def on_right_click(self, mouse_pos):
		x = mouse_pos[0]//TILE_SIZE
		y, _y = divmod(mouse_pos[1], TILE_SIZE)
		x, y = int(x), int(y)

		is_on_bottom = _y > 32
		# if _y > 32:
		# 	is_on_bottom = True
		# else:
		# 	is_on_bottom = False
		try:
			# 	original_image = get_block_image('down_oak_slab', convert_alpha=True)
			block = self.level.chunk_list.get_at(y, x)
			if not block:
			# 	original_image = get_block_image('up_oak_slab', convert_alpha=True)
				can_build = False
				for x_, y_ in self.level.get_neighbours(x, y):
					if self.level.chunk_list.get_at(y_, x_):
						can_build = True
						break
				if not can_build:
					return False

				x_, y_ = x*TILE_SIZE, y*TILE_SIZE
				groups = [self.level.obstacles_sprites,self.level.visible_sprites]
				# groups = [self.level.obstacles_sprites,self.level.visible_sprites]
				block = self.__class__((x_, y_+(32 if is_on_bottom else 0)), groups, level=self.level)
				block.data['on_top'] = not is_on_bottom
				# change_block_image(block, original_image)
				# for group in groups:
				# 	group.add(self)

				self.level.chunk_list.set_at(block, y, x)
				return True
			elif block.name == self.name:
				on_top = not (block.rect.top%64)
				if is_on_bottom == on_top:
					block.kill()
					self.kill()
					self.level.chunk_list.set_at(None, y, x)
					block.on_left_release()

					x_, y_ = x*TILE_SIZE, y*TILE_SIZE
					groups = [self.level.obstacles_sprites,self.level.visible_sprites]

					block = OakPlank((x_, y_), groups, level=self.level)
					block.data['two slabs'] = True

					self.level.chunk_list.set_at(block, y, x)

					return True
			return False
		except IndexError:
			return False

class OakLeaves(BreakableBlock, pygame.sprite.Sprite):
	name = 'oak leaves'

	slot_image = get_item_image('oak_leaves')

	hardness = .2
	best_tool = 'hoe'
	min_harvest = None
	data = {'type':'block'}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('oak_leaves', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		self.player_placed = False

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def search_around(self, center, num):
		if num == 4:
			return False
		x, y = center
		x //= 64
		y //= 64
		for x_, y_ in self.level.get_neighbours(x, y):
			block = self.level.chunk_list.get_at(y_, x_)
			if block and block.name == 'oak log':
				return True
			elif block and block.name == 'oak leaves':
				not_decay = self.search_around(block.rect.center, num+1)
				if not_decay:
					return True

	def random_tick(self):
		if self.player_placed:
			return
		decay = not self.search_around(self.rect.center, 1)
		x, y = self.rect.center
		x //= 64
		y //= 64
		if decay:
			self.level.chunk_list.set_at(None, y, x)
			self.on_break()
			self.kill()

	def on_break(self):
		# Drop sapling 5%
		# Drop sticks  2%
		# Drop apple  .5%

		return

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		leaves = default_on_right_click(self, mouse_pos, groups)
		if leaves:
			leaves.player_placed = True

class Stone(BreakableBlock, pygame.sprite.Sprite):
	name = 'stone'

	slot_image = get_item_image('stone')

	hardness = 1.5
	best_tool = 'pickaxe'
	min_harvest = 'wood'
	data = {'type':'block', 'smeltable':True}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('stone', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		tool = get_slot_player_holding(self.level.player)
		can_harvest = set(k for k, v in tool_mults.items() if v >= tool_mults[self.min_harvest])
		if can_harvest:
			rect = self.slot_image.get_rect(center=self.rect.center)
			self.level.drop(CobbleStone(rect.center, [], level=self.level), CobbleStone.slot_image, rect) # When adding enchantments, make sure to drop stone if silk touch
		return

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)

class CobbleStone(BreakableBlock, pygame.sprite.Sprite):
	name = 'cobble stone'

	slot_image = get_item_image('cobblestone')

	hardness = 2
	best_tool = 'pickaxe'
	min_harvest = 'wood'
	data = {'type':'block', 'smeltable':True}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('cobblestone', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		tool = get_slot_player_holding(self.level.player)
		can_harvest = set(k for k, v in tool_mults.items() if v >= tool_mults[self.min_harvest])
		if can_harvest:
			rect = self.slot_image.get_rect(center=self.rect.center)
			self.level.drop(CobbleStone(rect.center, [], level=self.level), self.slot_image, rect)
		return

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)

class CraftingTable(BreakableBlock, pygame.sprite.Sprite):
	name = 'crafting table'

	slot_image = get_item_image('crafting_table')

	hardness = 2
	best_tool = 'axe'
	min_harvest = None
	data = {'type':'block', 'fuel':True}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('crafting_table', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		self.inventory = [[Slot(level=self.level, player=self) for _ in range(3)] for _ in range(3)]

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		self.level.drop(CraftingTable(rect.center, [], level=self.level), self.slot_image, rect)
		return

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)

	def use(self):
		player = self.level.player
		player.scene = self
		player.direction.x = 0

class Furnace(BreakableBlock, pygame.sprite.Sprite):
	name = 'furnace'

	slot_image = get_item_image('furnace')

	hardness = 	3.5
	best_tool = 'pickaxe'
	min_harvest = None
	data = {'type':'block', 'smelter':True}


	def __init__(self, pos, groups, *, level):

		self.original_image = get_block_image('furnace', convert_alpha=True)
		self.image = self.original_image.copy()
		self.mask = pygame.mask.from_surface(self.image)
		self.rect  = self.image.get_rect(topleft=pos)

		self.level = level

		self.fuel_slot = Slot(level=self.level, player=self)
		self.input_slot = Slot(level=self.level, player=self)
		self.output_slot = Slot(level=self.level, player=self)

		self.smelting_time = 0
		self.started_smelting = float('inf')

		with open("fuel_durations.json", "r") as f:
			self.duration_json = json.load(f)

		super().__init__(groups)

	def update(self):
		self.break_tick(self.on_break)

		if self.fuel_slot.obj and not self.smelting_time and self.input_slot.obj:
			self.smelting_time = self.duration_json[self.fuel_slot.slot_name]
			self.started_smelting = time.time()

			self.original_image = get_block_image('furnace_on', convert_alpha=True)
			self.image = self.original_image.copy()
			self.fuel_slot.amount -= 1
			if self.fuel_slot.amount <= 0:
				self.fuel_slot.change_item(None)
		elif self.smelting_time:
			if time.time() - self.started_smelting >= self.smelting_time:
				self.smelting_time = 0
				self.started_smelting = float('inf')
				self.original_image = get_block_image('furnace', convert_alpha=True)
				self.image = self.original_image.copy()



	def on_break(self):
		rect = self.slot_image.get_rect(center=self.rect.center)
		self.level.drop(Furnace(rect.center, [], level=self.level), self.slot_image, rect)
		return

	def on_right_click(self, mouse_pos):
		groups = [self.level.obstacles_sprites,self.level.visible_sprites]
		return default_on_right_click(self, mouse_pos, groups)

	def use(self):
		player = self.level.player
		player.scene = self
		player.direction.x = 0