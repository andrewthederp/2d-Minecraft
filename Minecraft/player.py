import pygame, os, random, copy, time, json
from blocks import *
from items import *
from settings import *
from misc import *
from slots import Slot
from fonts import get_font

class Player(pygame.sprite.Sprite):
	def __init__(self, pos, groups, sprite_groups, *, level):
		super().__init__(groups)

		for key, value in sprite_groups.items():
			setattr(self, key, value)

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

		self.jumping = False
		self.falling = False

		# INV/ITEMS
		self.inventory = [[Slot(level=self.level, player=self) for _ in range(9)] for _ in range(4)]
		self.inventory[0][0] = Slot(level=self.level, player=self, obj=CraftingTable((0,0), [], level=self.level))
		self.inventory[0][1] = Slot(level=self.level, player=self, obj=WoodenPickaxe(level=self.level))
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

		self.crafting_output = Slot(level=self.level, player=self)


		# RANGES
		self.reach = 64*3
		self.pickup_range = 64*1.5


	def input(self):
		# getting the mouse position relative to the player position
		mouse_pos = get_mouse_pos(self)

		for event in self.level.events:
			# hot bar scrolling
			if event.type == pygame.MOUSEWHEEL and self.scene == 'game':
				self.holding_index += event.y*-1

				if self.holding_index <= 0:
					self.holding_index = 9
				elif self.holding_index >= 10:
					self.holding_index = 1
			# opening inventory
			if event.type == pygame.KEYDOWN:
				if event.key == pygame.K_e:
					self.scene = 'inventory'
					self.direction.x = 0
				if event.key == pygame.K_q:
					holding = get_slot_player_holding(self)
					if holding.obj: # sometimes I wish I used pymunk
						img = holding.image
						rect = img.get_rect(center=self.rect.center)
						entity = self.level.drop(holding.obj, img, rect, thrown=True, pickup_cooldown=60)


						entity.jump(-15)
						holding.amount -= 1
						if holding.amount == 0:
							holding.change_item(None)
			# placing/using blocks
			if event.type == pygame.MOUSEBUTTONDOWN:
				if event.button and not self.rect.collidepoint(mouse_pos) and event.button == 3:
					success = get_slot_player_holding(self).on_right_click(mouse_pos) # this system will need to be changed in the future for things such as food
					if not success:
						block = self.level.chunk_list.get_at(x=mouse_pos[0], y=mouse_pos[1], convert=True)
						func = getattr(block, 'use', False)
						if func:
							func()
					else:
						self.level.player_draw.item_used()


		if self.scene == 'game': # just as a precaution
			keys_pressed = pygame.key.get_pressed()

			# movement
			if keys_pressed[pygame.K_a]:
				self.direction.x = -1
			elif keys_pressed[pygame.K_d]:
				self.direction.x = 1
			else:
				self.direction.x = 0

			# jumping
			if keys_pressed[pygame.K_SPACE]:
				self.jump(-13)

			# changing holding slot
			for num in range(1, 10):
				key = getattr(pygame, f"K_{num}")
				if keys_pressed[key]:
					self.holding_index = num

			# breaking blocks
			pressed = pygame.mouse.get_pressed()

			if self.pressing_block:
				if not self.pressing_block.rect.collidepoint(mouse_pos):
					self.pressing_block.on_left_release()
					self.pressing_block = None

			for sprite in self.obstacles_sprites:
				if sprite.rect.collidepoint(mouse_pos) and in_circle(mouse_pos, self.rect.center, self.reach):

					block = self.level.chunk_list.get_at(mouse_pos[0], mouse_pos[1], convert=True)

					if block:
						if pressed[0] and block != self.pressing_block:
							self.pressing_block = block
							self.pressing_block.on_left_click()
						if not pressed[0] and self.pressing_block:
							self.pressing_block.on_left_release()
							self.pressing_block = None
					if pressed[1] and get_slot_player_holding(self).obj != block: # pick block
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
				if self.stopped_pressing: # The player will release the mouse button twice so we have to make sure to only do stuff on the second button up
					for slot in self.inventory_sprites:
						rect = slot.rect
						spot = self.crafting_inv if slot.location == 'crafting box' else self.inventory
						if self.holding and rect.collidepoint(event.pos):
							if slot.obj is None: # Put the item we're holding into the empty spot
								x, y = slot.xy
								if event.button == 1: # pick up the entire stack
									spot[x][y] = self.holding
									slot.change_item(self.holding.obj)
									self.holding = None
								else: # pick up a single item
									slt = self.holding.copy()
									slt.amount = 1
									spot[x][y] = slt
									slot.change_item(slt.obj)
									self.holding.amount -= 1
								self.selected = []
							elif slot.obj.name == self.holding.obj.name: # the item we're holding and the slot item are the same
								if slot.amount < 64: # if the slot is already at 64 let's not bother
									can_get = 64-slot.amount if event.button == 1 else 1 # if left click place the entire stack otherwise only place a single item
									if can_get >= self.holding.amount: # after placing we won't have a surplus 
										slot.amount += self.holding.amount
										self.holding = None
										self.selected = []
									else: # we have a surplus
										slot.amount += can_get
										self.holding.amount -= can_get
							else: # the item we're holding and the slot item are not the same, swap places
								x, y = slot.xy
								old_slot = slot.copy()
								spot[x][y] = self.holding
								slot.change_item(self.holding.obj)
								self.holding = old_slot
					self.crafting_output = self.craft(self.crafting_inv) # updating the crafting result for display
				else: # the first time we release the mouse button
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
						if self.holding.slot_name == self.crafting_output.slot_name and rect.collidepoint(event.pos): # if the item we're holding is the same as the crafting output
							self.holding.amount += self.crafting_output.amount
							self.crafting_output = Slot(obj=None, level=self.level, player=self) 

							if (self.holding.amount + self.crafting_output.amount) <= 64: # we have reached the stack limit
								for row in self.crafting_inv: # reduce the items, in the future this should be slightly changed for items such as milk buckets
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


							for row in self.crafting_inv: # reduce the items, in the future this should be slightly changed for items such as milk buckets
								for slot in row:
									if slot.obj:
										if slot.amount == 1:
											x, y = slot.xy
											self.crafting_inv[x][y] = Slot(obj=None, level=self.level, player=self)
										else:
											slot.amount -= 1
							return

				if self.holding and event.button == 1: # double click on an item to gather it all
					t = time.time() - self.last_button_pressed
					if t < .2:
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
				for slot in self.inventory_sprites: # I have no idea what any of this is, go in there with a hazmat suit
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
			if event.type == pygame.KEYDOWN: # go out of the inventory
				if event.key in [pygame.K_e, pygame.K_ESCAPE]:
					self.scene = 'game'
					return
				for num in range(1, 10): # tp slot items using numbers
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
							if not self.inventory[0][num].obj: # this should be changed in case the slot item is the same as the crafting output
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


		pressed = pygame.mouse.get_pressed() # hold right/left click and hover over other items
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


	def crafting_table_input(self): # same as `inventory_input` not gonna document it twice
		inv = self.scene.inventory
		for event in self.level.events:
			if event.type == pygame.MOUSEBUTTONUP:
				if self.stopped_pressing:
					for slot in self.inventory_sprites:
						rect = slot.rect
						spot = inv if slot.location == 'crafting box' else self.inventory
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
					self.crafting_output = self.craft(inv)
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
								for row in inv:
									for slot in row:
										if slot.obj:
											if slot.amount == 1:
												x, y = slot.xy
												inv[x][y] = Slot(obj=None, level=self.level, player=self)
											else:
												slot.amount -= 1
					else:
						if rect.collidepoint(event.pos):
							self.holding = self.crafting_output.copy()
							self.crafting_output = Slot(obj=None, level=self.level, player=self) 


							for row in inv:
								for slot in row:
									if slot.obj:
										if slot.amount == 1:
											x, y = slot.xy
											inv[x][y] = Slot(obj=None, level=self.level, player=self)
										else:
											slot.amount -= 1
							return

				if self.holding:
					t = time.time() - self.last_button_pressed
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
					spot = inv if slot.location == 'crafting box' else self.inventory
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
										if slot.location == 'crafting box': # Tp the item from the crafting box to the inventory
											for x_, y_ in sorted(self.find(slot.obj), key = lambda i: i[0]):
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
										else: # Do the opposite
											for x_, y_ in sorted(self.find(slot.obj, inventory=inv), key = lambda i: i[0]):
												slt = inv[x_][y_]
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
												if slot.location == 'crafting box': # Tp the item from the crafting box to the inventory
													for x_, y_ in sorted(self.find(), key = lambda i: i[0]):
														slt = self.inventory[x_][y_]
														self.inventory[x_][y_] = slot
														inv[x][y] = slt
														is_satisfied = True
														break
												else: # Do the opposite
													for x_, y_ in sorted(self.find(inventory=inv), key = lambda i: i[0]):
														slt = inv[x_][y_]
														inv[x_][y_] = slot
														self.inventory[x][y] = slt
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

				self.crafting_output = self.craft(inv)
			if event.type == pygame.KEYDOWN:
				if event.key in [pygame.K_e, pygame.K_ESCAPE]:
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

								for row in inv:
									for slot in row:
										if slot.obj:
											if slot.amount == 1:
												x, y = slot.xy
												inv[x][y] = Slot(obj=None, level=self.level, player=self)
											else:
												slot.amount -= 1
				self.crafting_output = self.craft(inv)


		pressed = pygame.mouse.get_pressed()
		if (self.stopped_pressing or len(self.selected) > 1) and (pressed[0] or pressed[2]) and self.holding:
			pos = pygame.mouse.get_pos()
			self.crafting_output = self.craft(inv)
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
								spot = inv if location == 'crafting box' else self.inventory
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


	def move(self): # make sure the player is moving correctly
		for _ in range(self.speed):
			self.rect.x += self.direction.x
			self.collision('horizontal')
		self.rect.y += self.direction.y
		self.collision('vertical')
		self.coor = [self.rect.x, self.rect.y]

	def jump(self, power): # the lower the power the higher the jump
		if not self.jumping and not self.falling: # no double jumping in my game >:(
			self.direction.y = power
			self.jumping = True


	def collision(self, direction): # make sure the player is not doing wall hacks
		if direction == 'horizontal': # right-left
			for sp in self.obstacles_sprites:
				if sp.rect.colliderect(self.rect):
					if self.falling or self.jumping: # if the player is in the air simply do normal collisions 
						if self.direction.x > 0:
							self.rect.right = sp.rect.left
							return 0

						if self.direction.x < 0:
							self.rect.left = sp.rect.right
							return 1
					else:
						sp.rect.y += 33 # move the block down 33 pixels, if the player no longer collides with it then we don't do collision
						group = pygame.sprite.GroupSingle(sp)
						sprite = pygame.sprite.spritecollideany(self, group, pygame.sprite.collide_mask)
						sp.rect.y -= 33 # reset the block's position

						if sprite: # the block still collides, let's do collision
							# TODO: check if the player goes to the top of this block if it will collide with any other blocks
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
		if direction == 'vertical': # up-down
			for sprite in self.obstacles_sprites:
				if sprite.rect.colliderect(self.rect):
					group = pygame.sprite.GroupSingle(sprite)
					if self.direction.y > 0: # the player is jumping, this is in case the player attempts to jump into an upper half of a slab for example
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

					if self.direction.y < 0: # the player is falling, this is in case the player falls into the bottom half of a slab for example
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
		else: # if we're not jumping then we're falling
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

	def add_item(self, obj): # give the player an item
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

	# def pickup(self): # pick up fallen items around the player
	# 	for sprite in self.dropped_entities:
	# 		if self.pickup_range.colliderect(sprite.rect):
	# 			sprite.kill()
	# 			self.add_item(sprite.obj)


	def swap(self, xy1, xy2): # swap to items in the inventory
		x, y = xy1
		x_, y_ = xy2

		slot1 = self.inventory[x][y]
		slot2 = self.inventory[x_][y_]

		self.inventory[x][y] = slot2
		self.inventory[x_][y_] = slot1

	def find(self, obj=None, *, inventory=None): # find any item in `inventory` or the player's inventory 
		name = obj.name if obj else ''
		found = False
		for x, row in enumerate(inventory or self.inventory):
			for y, slot in enumerate(row):
				if slot.slot_name == name and slot.amount < 64:
					found = True
					yield x, y
		if not found:
			raise ValueError("item not in the list")

	def tick(self): # we will do stuff here, some day
		# print(self.holding_index)
		return

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
				name_ = name.strip('_')
				break
		slot = Slot.from_name(name_, level=self.level, player=self)
		if name_:
			slot.amount = amount
		return slot

	def update(self):
		if isinstance(self.scene, str):
			if self.scene == 'game':
				self.input()
			elif self.scene == 'inventory':
				self.inventory_input()
		else:
			if self.scene.name == 'crafting table':
				self.crafting_table_input()
		# self.pickup()
		self.apply_gravity()
		self.move()

class PlayerDraw:
	def __init__(self, player):
		# misc
		self.player = player

		self.screen = pygame.display.get_surface()

		self.font_20 = get_font(20)

		# gui
		path = os.path.join(asset_path, 'inventory_ui.png')
		self.inventory_img = pygame.image.load(path).convert_alpha()

		path = os.path.join(asset_path, 'crafting_table_ui.png')
		self.crafting_table_img = pygame.image.load(path).convert_alpha()

		path = os.path.join(asset_path, 'hotbar_ui.png')
		self.hotbar_img = pygame.image.load(path).convert_alpha()

		path = os.path.join(asset_path, 'big_box.png')
		self.big_box = pygame.image.load(path).convert_alpha()

		# .
		self.holding_slot = Slot(obj=None, player=self.player, level=self.player.level)
		self.hotbar_text = ''
		self.hotbar_text_transparency = 255

		# Item holding

		self.rotation = 0
		self.rotating_back = True
		self.last_direction = 0

	def draw(self):
		self.draw_hotbar() # the hotbar is always being drawn which is kinda weird
		self.draw_item_holding()
		if isinstance(self.player.scene, str): # 'game'/'inventory'
			if self.player.scene == 'inventory':
				self.draw_inventory()
			elif self.player.scene == 'game': # draw outlines
				# highlighting

				mouse_pos = get_mouse_pos(self.player)

				outline_surf = pygame.Surface((TILE_SIZE, TILE_SIZE)).convert_alpha()
				outline_surf.fill((0,0,0,0))
				rect = None
				for sprite in self.player.obstacles_sprites:
					if sprite.rect.collidepoint(mouse_pos) and in_circle(mouse_pos, self.player.rect.center, self.player.reach):

						rect = copy.deepcopy(sprite.rect)
						for point in sprite.mask.outline():
							pygame.draw.circle(outline_surf, (15,15,15), point, 2)
						break

				# remove the last highlight
				for sprite in self.player.visible_sprites.sprites():
					if getattr(sprite, 'appear', False):
						self.player.visible_sprites.remove(sprite)
						break

				if rect:
					sprite = pygame.sprite.Sprite()
					sprite.appear = True
					sprite.image = outline_surf
					sprite.rect = rect
					self.player.visible_sprites.add(sprite)
		else:
			if self.player.scene.name == 'crafting table':
				self.draw_crafting_table()
			# FIX THIS # What's broken? #

			# slot = get_slot_player_holding(self.player)
			# if not collide and ('block' in slot.slot_data.get('type')):
			# 	x,y = pygame.mouse.get_pos()
			# 	x //= 64
			# 	y //= 64
			# 	img = slot.obj.image.copy()
			# 	img.set_alpha(128)
			# 	self.screen.blit(img, (x*64, y*64))

		if self.hotbar_text_transparency <= 0: # if the player picked up a new item/switched to a new item we add a fading text
			self.hotbar_text = ''

	def draw_transparent(self, rect, color, width=0, **kwargs): # A useful function that draws transparent rects
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


	def draw_item_holding(self):
		self.last_direction = self.player.direction.x or self.last_direction
		item = get_slot_player_holding(self.player).obj
		if item:
			image = item.image

			image = pygame.transform.scale(image, (16, 16))

			if self.last_direction == 1:
				rect = image.get_rect(centerx=self.player.rect.centerx, right=self.player.rect.right)
			else:
				rect = image.get_rect(centerx=self.player.rect.centerx, left=self.player.rect.left)

			if self.rotating_back:
				self.rotation -= 10
				if self.rotation > 0:
					image = pygame.transform.rotate(image, self.rotation)
			else:
				self.rotation += 10
				if self.rotation > 90:
					self.rotating_back = True
				image = pygame.transform.rotate(image, self.rotation)

			self.screen.blit(image, (HALF_WIDTH+(16 if self.last_direction>0 else -32), HALF_HEIGHT+16))

	def item_used(self):
		if get_slot_player_holding(self.player).obj:
			self.rotating_back = False
			self.rotation = 0

	def draw_hotbar(self):
		width, height = self.hotbar_img.get_size()
		hotbar_rect = self.hotbar_img.get_rect(bottom=HEIGHT, centerx=HALF_WIDTH)
		self.screen.blit(self.hotbar_img, hotbar_rect)

		box = pygame.Rect((0, HEIGHT-height), (42, 42))


		for num in range(9):
			box = box.copy()
			box.x = hotbar_rect.x+(39*num)
			if num == self.player.holding_index-1:
				self.screen.blit(self.big_box, box)

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
			write_text(self.font_20, self.hotbar_text.title(), centery=hotbar_rect.y - 30, centerx=HALF_WIDTH, transparency=self.hotbar_text_transparency, surface=self.screen)
			self.hotbar_text_transparency -= 2

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

		for row in (0,1):
			box = pygame.Rect((336, 158+(36*row)), (33, 33))

			for num in (0,1):
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

	def draw_crafting_table(self):
		highlight = None
		inventory_sprites = []

		full_screen = pygame.Rect((0,0), (WIDTH, HEIGHT))
		self.draw_transparent(full_screen, (0,0,0,128))

		width = 398
		height = 198

		inventory_rect = self.crafting_table_img.get_rect(center = (WIDTH*.5, HEIGHT*.5))
		self.screen.blit(self.crafting_table_img, inventory_rect)

		mouse_pos = pygame.mouse.get_pos()
		# print(mouse_pos)

		# Hotbar
		box = pygame.Rect((159, 406), (34, 33))
		for num in range(9):
			box.x += 36
			slot = self.player.inventory[0][num]
			img = slot.image
			img_rect = img.get_rect(centerx=box.centerx-3, centery=box.centery)
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
			box = pygame.Rect((155, 254), (34, 33))
			box.y = 254+(36*row)

			for num in range(9):
				box.x += 36
				slot = self.player.inventory[row][num]
				img = slot.image
				img_rect = img.get_rect(centerx=box.centerx+1, centery=box.centery)
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


		# Crafting info
		for row in (0,1,2):
			box = pygame.Rect((202, 157+(36*row)), (33, 33))

			for num in (0,1,2):
				box.x += 36

				slot = self.player.scene.inventory[row][num]
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

		box = pygame.Rect((0, 0), (33, 33))
		box.center = (440, 209)
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
