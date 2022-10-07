import pygame, os, random, copy, time, json
from blocks import *
from settings import *
from misc import *
from slots import Slot
from fonts import get_font

class Player(pygame.sprite.Sprite):
	def __init__(self, pos, groups, obstacles_sprites, *, level):
		super().__init__(groups)

		# DRAWING
		current_path = os.path.join(os.path.dirname(__file__), 'assets', 'player.png')

		self.image = pygame.image.load(current_path).convert_alpha()
		self.rect  = self.image.get_rect(topleft=pos)

		self.scene = 'game'

		# MISC
		self.coor = [pos[0]//TILE_SIZE, pos[1]//TILE_SIZE]
		self.display_surface = pygame.display.get_surface()
		self.level = level
		self.data = {'type':'player'}

		# MOVEMENT
		self.direction = pygame.math.Vector2(0, 1)
		self.speed = 7

		self.obstacles_sprites = obstacles_sprites

		self.jumping = False
		self.falling = False

		# INV/ITEMS
		self.inventory = [[Slot(level=self.level, player=self) for _ in range(9)] for _ in range(4)]
		self.pressing_block = None

		self.holding_index = 1
		self.holding = None
		self.selected = []
		self.stopped_pressing = False
		self.last_button_pressed = float('inf')

		# CRAFTING
		with open("crafting.json", "r") as f:
			self.crafting_json = json.load(f)

		self.crafting_inv = [[Slot(level=self.level, player=self) for _ in range(2)] for _ in range(2)]
		self.crafting_table = [[Slot(level=self.level, player=self) for _ in range(3)] for _ in range(3)]

		self.crafting_output = Slot(level=self.level, player=self)


		# RANGES
		self.reach = pygame.Rect(0,0,64*8,64*7)
		self.pickup_range = pygame.Rect(0,0,64*3,64*2)


	def input(self):
		for event in self.level.events:
			if event.type == pygame.MOUSEWHEEL and self.scene == 'game':
				self.holding_index += event.y*-1

				if self.holding_index <= 0:
					self.holding_index = 9
				elif self.holding_index >= 10:
					self.holding_index = 1
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_e:
					self.scene = 'inventory'
					self.direction.x = 0


		if self.scene == 'game':
			keys_pressed = pygame.key.get_pressed()

			# movement
			if keys_pressed[pygame.K_a]:
				self.direction.x = -1
			elif keys_pressed[pygame.K_d]:
				self.direction.x = 1
			else:
				self.direction.x = 0

			# jumping
			if keys_pressed[pygame.K_SPACE] and not self.jumping and not self.falling:
				self.direction.y = -13
				self.jumping = True

			# changing holding slot
			for num in range(1, 10):
				key = getattr(pygame, f"K_{num}")
				if keys_pressed[key]:
					self.holding_index = num

			# Idk
			offset = pygame.math.Vector2()

			offset.x = self.rect.centerx - HALF_WIDTH
			offset.y = self.rect.centery - HALF_HEIGHT

			mouse_pos = pygame.mouse.get_pos()
			mouse_pos += offset

			pressed = pygame.mouse.get_pressed()
			if pressed[2] and not self.rect.collidepoint(mouse_pos):
				self.inventory[0][int(self.holding_index)-1].on_right_click(mouse_pos)

			if self.pressing_block:
				if not self.pressing_block.rect.collidepoint(mouse_pos):
					self.pressing_block.on_left_release()
					self.pressing_block = None

			for sprite in self.obstacles_sprites:
				if sprite.rect.collidepoint(mouse_pos) and sprite.rect.colliderect(self.reach):
					rect = copy.deepcopy(sprite.rect)
					rect.topleft -= offset

					x, y = int(mouse_pos[0]//TILE_SIZE), int(mouse_pos[1]//TILE_SIZE)
					block = WORLD_MAP[y][x]

					if block:
						if pressed[0] and block != self.pressing_block:
							self.pressing_block = block
							self.pressing_block.on_left_click()
						if not pressed[0] and self.pressing_block:
							self.pressing_block.on_left_release()
							self.pressing_block = None
					if pressed[1] and self.inventory[0][self.holding_index].obj != block:
						for x, y in self.find(block):
							if x == 0:
								self.holding_index = y+1
								break
							else:
								self.swap((0, self.holding_index-1), (x,y))
								break

	def inventory_input(self):
		for event in self.level.events:
			if event.type == pygame.MOUSEBUTTONUP:
				if self.stopped_pressing:
					for slot in self.inventory_sprites:
						rect = slot.rect
						spot = self.crafting_inv if slot.location == 'crafting box' else self.inventory
						if self.holding and rect.collidepoint(event.pos):
							if slot.obj is None:
								x, y = slot.xy
								if event.button == 1:
									spot[x][y] = self.holding
									slot.change_item(self.holding.obj)
									self.holding = None
								else:
									slt = self.holding.copy()
									slt.amount = 1
									spot[x][y] = slt
									slot.change_item(slt.obj)
									self.holding.amount -= 1
								self.selected = []
							elif slot.obj.name == self.holding.obj.name:
								if slot.amount < 64:
									can_get = 64-slot.amount if event.button == 1 else 1
									if can_get >= self.holding.amount:
										slot.amount += self.holding.amount
										self.holding = None
										self.selected = []
									else:
										slot.amount += can_get
										self.holding.amount -= can_get
							else:
								x, y = slot.xy
								old_slot = slot.copy()
								spot[x][y] = self.holding
								slot.change_item(self.holding.obj)
								self.holding = old_slot
					self.crafting_output = self.craft(self.crafting_inv)
				else:
					if self.selected:
						self.selected = []
						if not self.holding.display_amount:
							self.holding = None
						else:
							self.holding.amount = self.holding.display_amount
					self.stopped_pressing = True
			if event.type == pygame.MOUSEBUTTONDOWN:

				if self.crafting_output.obj:
					rect = self.crafting_output.rect
					if self.holding:
						if self.holding.slot_name == self.crafting_output.slot_name and rect.collidepoint(event.pos):
							self.holding.amount += self.crafting_output.amount
							self.crafting_output = Slot(obj=None, level=self.level, player=self) 

							if (self.holding.amount + self.crafting_output.amount) <= 64:
								for row in self.crafting_inv:
									for slot in row:
										if slot.obj:
											if slot.amount == 1:
												x, y = slot.xy
												self.crafting_inv[x][y] = Slot(obj=None, level=self.level, player=self)
											else:
												slot.amount -= 1
					else:
						if rect.collidepoint(event.pos):
							self.holding = self.crafting_output.copy()
							self.crafting_output = Slot(obj=None, level=self.level, player=self) 


							for row in self.crafting_inv:
								for slot in row:
									if slot.obj:
										if slot.amount == 1:
											x, y = slot.xy
											self.crafting_inv[x][y] = Slot(obj=None, level=self.level, player=self)
										else:
											slot.amount -= 1
							return

				if self.holding:
					t = time.time() - self.last_button_pressed
					# print(t, t < .5)
					if t < .3:
						self.stopped_pressing = False
						for slot in self.inventory_sprites:
							if slot.slot_name == self.holding.slot_name:
								if (self.holding.amount + slot.amount) <= 64:
									self.holding.amount += slot.amount
									slot.change_item(None)
								else:
									can_get = 64-self.holding.amount
									self.holding.amount += can_get
									slot.amount -= can_get
						return

				self.last_button_pressed = time.time()
				"""
				CHECK IF LEFT SHIFT CLICK ON CRAFTING OUTPUT
				"""
				for slot in self.inventory_sprites:
					rect = slot.rect
					spot = self.crafting_inv if slot.location == 'crafting box' else self.inventory
					if rect.collidepoint(event.pos):
						if not self.holding:
							keys_pressed = pygame.key.get_pressed()
							if keys_pressed[pygame.K_LSHIFT]:
								x, y = slot.xy
								slot = spot[x][y]
								check = x == 0
								is_satisfied = False
								tries = 0
								while (not is_satisfied) and (tries < 50):
									tries += 1
									try:
										for x_, y_ in sorted(self.find(slot.obj), key = lambda i: i[0]):
											if slot.location == 'crafting box' or check == (x_ != 0):
												slt = self.inventory[x_][y_]
												if slt.amount < 64:
													can_get = 64-slt.amount
													if can_get >= slot.amount:
														slt.amount += slot.amount
														slot.change_item(None)
														is_satisfied = True
														break
													else:
														slt.amount += can_get
														slot.amount -= can_get
														continue
										if not is_satisfied:
											raise ValueError
									except ValueError:
										try:
											if not is_satisfied:
												for x_, y_ in sorted(self.find(), key = lambda i: i[0]):
													if slot.location == 'crafting box':
														slt = self.inventory[x_][y_]
														self.inventory[x_][y_] = slot
														self.crafting_inv[x][y] = slt
														is_satisfied = True
														break
													elif check == (x_ != 0):
														self.swap((x,y), (x_, y_))
														is_satisfied = True
														break
										except ValueError:
											pass
							elif slot.amount > 0:
								if event.button == 1 or slot.amount <= 1:
									self.stopped_pressing = False
									self.holding = slot
									self.inventory_sprites.remove(slot)
									x, y = slot.xy
									spot[x][y] = Slot(level=self.level, player=self)
								elif event.button == 3:
									self.stopped_pressing = False
									s = slot.copy()
									amt = (slot.amount // 2) + 1 if slot.amount % 2 else slot.amount // 2
									s.amount = amt
									slot.amount -= amt
									self.holding = s

				self.crafting_output = self.craft(self.crafting_inv)
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_e:
					self.scene = 'game'
					return
				for num in range(1, 10):
					key = getattr(pygame, f"K_{num}")
					if event.key == key:
						mouse_pos = pygame.mouse.get_pos()

						for slot in self.inventory_sprites:
							rect = slot.rect
							if rect.collidepoint(mouse_pos):
								num -= 1
								x,y = slot.xy
								self.swap((x,y), (0,num))
						if self.crafting_output.rect.collidepoint(mouse_pos):
							num -= 1
							if not self.inventory[0][num].obj:
								self.inventory[0][num] = self.crafting_output.copy()

								for row in self.crafting_inv:
									for slot in row:
										if slot.obj:
											if slot.amount == 1:
												x, y = slot.xy
												self.crafting_inv[x][y] = Slot(obj=None, level=self.level, player=self)
											else:
												slot.amount -= 1
				self.crafting_output = self.craft(self.crafting_inv)


		pressed = pygame.mouse.get_pressed()
		if (self.stopped_pressing or len(self.selected) > 1) and (pressed[0] or pressed[2]) and self.holding:
			pos = pygame.mouse.get_pos()
			self.crafting_output = self.craft(self.crafting_inv)
			for slot in self.inventory_sprites:
				rect = slot.rect
				if slot.obj:
					continue

				continue_ = False
				for dct in self.selected:
					if slot.xy == dct['xy'] and slot.location == dct['location']:
						continue_ = True
						break
				if continue_:
					continue
				if rect.collidepoint(pos):
					self.selected.append({'xy':slot.xy, 'location':slot.location})
					length = len(self.selected)
					if length >= 2:
						self.stopped_pressing = False
						if pressed[0]:
							num, remainder = divmod(self.holding.amount, length)
						else:
							num = 1 if length <= self.holding.amount else 0
							remainder = self.holding.amount-length
						if num >= 1:
							self.holding.display_amount = remainder
							for dct in self.selected:
								xy, location = dct.values()
								spot = self.crafting_inv if location == 'crafting box' else self.inventory
								x,y=xy
								slt = spot[x][y]
								if not slt.obj:
									slot_copy = self.holding.copy()
									slot_copy.amount = num
									spot[x][y] = slot_copy
								else:
									slt.amount = num
						else:
							self.selected.pop()



		# if self.holding and pygame.mouse.get_pressed()[0]:
		# 	pos = pygame.mouse.get_pos()
		# 	for slot in self.inventory_sprites:
		# 		rect = slot.rect
		# 		if rect.collidepoint(pos):


	def move(self, speed):
		# for _ in range(self.speed):
		self.rect.x += self.direction.x*self.speed
		self.collision('horizontal')
		self.rect.y += self.direction.y
		self.collision('vertical')
		self.coor = [self.rect.x, self.rect.y]

	def collision(self, direction):
		if direction == 'horizontal':
			for sp in self.obstacles_sprites:
				if sp.rect.colliderect(self.rect):
					if self.falling or self.jumping:
						if self.direction.x > 0:
							self.rect.right = sp.rect.left
							return 0

						if self.direction.x < 0:
							self.rect.left = sp.rect.right
							return 1
					else:
						sp.rect.y += 32
						group = pygame.sprite.GroupSingle(sp)
						sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask)
						sp.rect.y -= 32

						if sprite:
							if self.direction.x > 0:
								self.rect.right = sprite.rect.left
								group.empty()
								return 0

							if self.direction.x < 0:
								self.rect.left = sprite.rect.right
								group.empty()
								return 1
		# if direction == 'horizontal':
		# 	for sprite in self.obstacles_sprites:
		# 		if sprite.rect.colliderect(self.rect):
		# 			if not (not (self.jumping or self.falling) and (self.rect.bottom-sprite.rect.top) <= 32):
		# 				if self.direction.x > 0:
		# 					self.rect.right = sprite.rect.left
		# 					return 0

		# 				if self.direction.x < 0:
		# 					self.rect.left = sprite.rect.right
		# 					return 1
		# if direction == 'horizontal':
		# 	for sprite in self.obstacles_sprites:
		# 		if sprite.rect.colliderect(self.rect):
		# 			if self.falling or self.jumping:
		# 				if self.direction.x > 0:
		# 					self.rect.right = sprite.rect.left
		# 					return 0

		# 				if self.direction.x < 0:
		# 					self.rect.left = sprite.rect.right
		# 					return 1
		# 			else:
		# 				try:
		# 					y_ = (self.rect.bottom % 64) + 33
		# 					if self.direction.x > 0 and sprite.image.get_at((self.rect.left % 64, y_))[3] != 0:
		# 						self.rect.right = sprite.rect.left
		# 						return 0

		# 					if self.direction.x < 0 and sprite.image.get_at((self.rect.right % 64, y_))[3] != 0:
		# 						self.rect.left = sprite.rect.right
		# 						return 1
		# 				except IndexError:
		# 					pass
		# if direction == 'horizontal':
		# 	for sprite in self.obstacles_sprites:
		# 		if sprite.rect.colliderect(self.rect):
		# 			if self.direction.x > 0:
		# 				self.rect.right = sprite.rect.left
		# 				return 0

		# 			if self.direction.x < 0:
		# 				self.rect.left = sprite.rect.right
		# 				return 1

		# if direction == 'vertical':
		# 	for sprite in self.obstacles_sprites:
		# 		if sprite.rect.colliderect(self.rect):
		# 			if self.direction.y > 0:
		# 				self.rect.bottom = sprite.rect.top
		# 				return 0

		# 			if self.direction.y < 0:
		# 				self.rect.top = sprite.rect.bottom
		# 				return 1
		if direction == 'vertical':
			for sprite in self.obstacles_sprites:
				if sprite.rect.colliderect(self.rect):
					group = pygame.sprite.GroupSingle(sprite)
					if self.direction.y > 0:
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

					if self.direction.y < 0:
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

	def apply_gravity(self):
		if self.jumping:
			if self.direction.y < 0:
				self.direction.y += .6

				self.collision('vertical')
				collide = False
				for sprite in self.obstacles_sprites:
					if sprite.rect.bottom == self.rect.top and self.rect.right > sprite.rect.left and self.rect.left < sprite.rect.right:
						collide = True
						break
				if collide:
					self.direction.y = 1
					self.falling = True
					self.jumping = False
			else:
				self.direction.y = 1
				self.jumping = False
				self.falling = True
		else:
			self.collision('vertical')
			collide = False
			for sprite in self.obstacles_sprites:
				if sprite.rect.top == self.rect.bottom and self.rect.right > sprite.rect.left and self.rect.left < sprite.rect.right:
					collide = True
					break

			if collide:
				self.direction.y = 1
				self.falling = False
			else:
				self.falling = True
				if self.direction.y < 30:
					self.direction.y += .6

	def add_item(self, obj):
		try:
			x, y = list(self.find(obj))[0]
			self.inventory[x][y].amount += 1
		except ValueError:
			try:
				x, y = list(self.find())[0]
				slot = self.inventory[x][y]
				slot.change_item(obj)
			except ValueError:
				pass

	def swap(self, xy1, xy2):
		x, y = xy1
		x_, y_ = xy2

		slot1 = self.inventory[x][y]
		slot2 = self.inventory[x_][y_]

		self.inventory[x][y] = slot2
		self.inventory[x_][y_] = slot1

	def find(self, obj=None):
		name = obj.name if obj else ''
		found = False
		for x, row in enumerate(self.inventory):
			for y, slot in enumerate(row):
				if slot.slot_name == name and slot.amount < 64:
					found = True
					yield x, y
		if not found:
			raise ValueError("item not in the list")

	def tick(self):
		# print(self.holding_index)
		return

	def update_rects(self):
		player_center = self.rect.center

		self.reach.center = self.rect.center
		self.pickup_range.center = self.rect.center

	def craft(self, crafting, return_recipe=False):
		crafting = [[slot.slot_name or None for slot in lst] for lst in crafting]

		if len(crafting) == 2:
			crafting.append([None,None,None])
			crafting[0].append(None)
			crafting[1].append(None)

		for _ in range(2):
			# Move up
			if all(not i for i in crafting[0]):
				crafting.append(crafting.pop(0))

			# Move left
			if all(not crafting[i][0] for i in range(len(crafting))):
				for lst in crafting:
					lst.append(lst.pop(0))

		name_ = None
		for name, dct in self.crafting_json.items():
			crafting_recipe = dct['recipe']
			amount = dct['amount']
			if crafting_recipe == crafting:
				if return_recipe:
					return crafting_recipe
				name_ = name
				break
		slot = Slot.from_name(name_, level=self.level, player=self)
		if name_:
			slot.amount = amount
		return slot

	def update(self):
		self.update_rects()
		if self.scene == 'game':
			self.input()
		elif self.scene == 'inventory':
			self.inventory_input()
		self.apply_gravity()
		self.move(self.speed)

class PlayerDraw:
	def __init__(self, player):
		self.player = player

		self.screen = pygame.display.get_surface()

		self.font_20 = get_font(20)

		path = os.path.join(asset_path, 'inventory.png')
		self.inventory_img = pygame.image.load(path).convert_alpha()

		self.holding_slot = Slot(obj=None, player=self.player, level=self.player.level)
		self.hotbar_text = ''
		self.hotbar_text_transparency = 255

	def draw(self):
		self.draw_hotbar()
		if self.player.scene == 'inventory':
			self.draw_inventory()
		elif self.player.scene == 'game':
			offset = pygame.math.Vector2()

			offset.x = self.player.rect.centerx - HALF_WIDTH
			offset.y = self.player.rect.centery - HALF_HEIGHT

			mouse_pos = pygame.mouse.get_pos()
			mouse_pos += offset

			collide = False
			for sprite in self.player.obstacles_sprites:
				if sprite.rect.collidepoint(mouse_pos) and sprite.rect.colliderect(self.player.reach):
					collide = True
					rect = copy.deepcopy(sprite.rect)
					rect.topleft -= offset
					for point in sprite.mask.outline():
						x, y = point
						pygame.draw.circle(self.screen, (15,15,15), (x+rect.left,y+rect.top), 2)
					break
			# FIX THIS #

			# slot = get_slot_player_holding(self.player)
			# if not collide and ('block' in slot.slot_data.get('type')):
			# 	x,y = pygame.mouse.get_pos()
			# 	x //= 64
			# 	y //= 64
			# 	img = slot.obj.image.copy()
			# 	img.set_alpha(128)
			# 	self.screen.blit(img, (x*64, y*64))

		if self.hotbar_text_transparency <= 0:
			self.hotbar_text = ''

	def draw_transparent(self, rect, color, width=0, **kwargs):
		strategy=kwargs.pop('strategy', pygame.draw.rect)
		rect = rect.copy()
		topleft = tuple(rect.topleft)
		rect.x = 0
		rect.y = 0

		temp_surf = pygame.Surface(rect.size, pygame.SRCALPHA)

		strategy(temp_surf, color, rect, width=width, **kwargs)

		self.screen.blit(temp_surf, topleft)

	# def draw_lines(self, rect, hor_lines, ver_lines):
	# 	for x_ in range(rect.x, rect.right, rect.w//hor_lines):
	# 		pygame.draw.line(self.screen, (81, 81, 81), (x_+2, rect.y), (x_+2, rect.bottom-1), width=3)
	# 		pygame.draw.line(self.screen, (197, 197, 197), (x_, rect.y), (x_, rect.bottom-1), width=3)

	# 	for y_ in range(rect.y, rect.bottom, rect.h//ver_lines):
	# 		if y_+2 < rect.bottom:
	# 			pygame.draw.line(self.screen, (81, 81, 81), (rect.x+2, y_+2), (rect.right-1, y_+2), width=3)
	# 		pygame.draw.line(self.screen, (197, 197, 197), (rect.x+2, y_), (rect.right-1, y_), width=3)



	def draw_hotbar(self):
		height = 42
		width = 378

		hotbar_rect = pygame.Rect(0, HEIGHT-(height+7), width, height)
		hotbar_rect.centerx = WIDTH*.5

		box = pygame.Rect((0, HEIGHT-(height+7)), (42, 42))

		self.draw_transparent(hotbar_rect, (0,128,0,127))
		hotbar_outline = hotbar_rect.copy()
		hotbar_outline.x -= 4
		hotbar_outline.y -= 4
		hotbar_outline.w += 7
		hotbar_outline.h += 7
		pygame.draw.rect(self.screen, (0,0,0), hotbar_outline, 2)


		for num in range(9):
			box = box.copy()
			box.x = hotbar_rect.x+(42*num)
			if num != (int(self.player.holding_index)-1):
				pygame.draw.rect(self.screen, (99,99,99), box, 5)

			slot = self.player.inventory[0][num]
			img = slot.image
			img_rect = img.get_rect(center=box.center)
			self.screen.blit(img, img_rect)

			if slot.amount > 1:
				write_text(self.font_20, slot.amount, centery=box.centery+3, centerx=box.centerx+5, surface=self.screen)

			if num == (int(self.player.holding_index)-1) and slot.slot_name != self.holding_slot.slot_name:
				self.holding_slot = slot.copy()
				self.hotbar_text = slot.slot_name
				self.hotbar_text_transparency = 255

		if self.hotbar_text:
			write_text(self.font_20, self.hotbar_text.title(), centery=hotbar_outline.y - 30, centerx=HALF_WIDTH, transparency=self.hotbar_text_transparency, surface=self.screen)
			self.hotbar_text_transparency -= 2


		big_box = pygame.Rect(hotbar_rect.x+((int(self.player.holding_index)-1)*42),HEIGHT-(height+10),45,45)
		pygame.draw.rect(self.screen, (200,200,200), big_box, 9)

	def draw_inventory(self):
		highlight = None
		inventory_sprites = []

		full_screen = pygame.Rect((0,0), (WIDTH, HEIGHT))
		self.draw_transparent(full_screen, (0,0,0,128))

		width = 398
		height = 198

		inventory_rect = self.inventory_img.get_rect(center = (WIDTH*.5, HEIGHT*.5))
		self.screen.blit(self.inventory_img, inventory_rect)

		mouse_pos = pygame.mouse.get_pos()
		# print(mouse_pos)

		# Hotbar
		box = pygame.Rect((155, 405), (33, 33))
		for num in range(9):
			box.x += 36
			slot = self.player.inventory[0][num]
			img = slot.image
			img_rect = img.get_rect(center=box.center)
			slot.change_coor(0, num)
			slot.change_rect(img_rect)
			slot.change_location('hotbar')
			inventory_sprites.append(slot)

			self.screen.blit(img, img_rect)

			if slot.amount > 1:
				write_text(self.font_20, slot.amount, centery=box.centery+3, centerx=box.centerx+3, surface=self.screen)

			if (len(self.player.selected) > 1 and slot.xy in self.player.selected):
				self.draw_transparent(box, (255,255,255,128))
			elif img_rect.collidepoint(mouse_pos):
				highlight = slot
				self.draw_transparent(box, (255,255,255,128))

		# Rest of the inventory
		for row in range(1, 4):
			box = pygame.Rect((155, 254), (33, 33))
			box.y = 254+(36*row)

			for num in range(9):
				box.x += 36
				slot = self.player.inventory[row][num]
				img = slot.image
				img_rect = img.get_rect(center=box.center)
				slot.change_coor(row, num)
				slot.change_rect(img_rect)
				slot.change_location('inventory')
				inventory_sprites.append(slot)
				self.screen.blit(img, img_rect)

				if slot.amount > 1:
					write_text(self.font_20, slot.amount, centery=box.centery+3, centerx=box.centerx+3, surface=self.screen)

				if (len(self.player.selected) > 1 and slot.xy in self.player.selected):
					self.draw_transparent(box, (255,255,255,128))
				elif img_rect.collidepoint(mouse_pos):
					self.draw_transparent(box, (255,255,255,128))

					highlight = slot

		for row in [0,1]:
			box = pygame.Rect((336, 158+(36*row)), (33, 33))

			for num in [0,1]:
				box.x += 36

				slot = self.player.crafting_inv[row][num]
				img = slot.image
				img_rect = img.get_rect(center=box.center)
				slot.change_coor(row, num)
				slot.change_rect(img_rect)
				slot.change_location('crafting box')
				inventory_sprites.append(slot)
				self.screen.blit(img, img_rect)

				if slot.display_amount > 1:
					write_text(self.font_20, slot.display_amount, centery=img_rect.centery+3, centerx=img_rect.centerx+3, surface=self.screen)

				if (len(self.player.selected) > 1 and slot.xy in self.player.selected):
					self.draw_transparent(box, (255,255,255,128))
				elif img_rect.collidepoint(mouse_pos):
					self.draw_transparent(box, (255,255,255,128))

					highlight = slot




		# CRAFTING OUTPUT

		box = pygame.Rect((484, 178), (33, 33))
		slot = self.player.crafting_output
		img = slot.image
		img_rect = img.get_rect(center=box.center)
		slot.change_rect(box)
		if img_rect.collidepoint(mouse_pos):
			self.draw_transparent(box, (255,255,255,128))
			highlight = slot
		self.screen.blit(img, img_rect)

		if slot.amount > 1:
			write_text(self.font_20, slot.amount, centery=box.centery+3, centerx=box.centerx+3, surface=self.screen)

		# Holding
		if self.player.holding and self.player.holding.display_amount > 0:
			slot = self.player.holding
			img = slot.image
			img_rect = img.get_rect(center=mouse_pos)
			self.screen.blit(img, img_rect)

			if slot.display_amount > 1:
				write_text(self.font_20, slot.display_amount, centery=img_rect.centery+3, centerx=img_rect.centerx+3, surface=self.screen)

		if highlight and highlight.slot_name:
			w, h = self.font_20.size(highlight.slot_name.title())
			rect = pygame.Rect(0, 0, w+6, h+6)
			rect.centery = mouse_pos[1] - 2
			rect.left    = mouse_pos[0] + 11
			self.draw_transparent(rect, (48,25,52, 200), border_radius=3)
			pygame.draw.rect(self.screen, (75,0,130), rect, 2, border_radius=3)

			write_text(self.font_20, highlight.slot_name.title(), centery = mouse_pos[1]-3, left=mouse_pos[0]+16, surface=self.screen)

		self.player.inventory_sprites = inventory_sprites