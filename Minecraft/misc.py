import pygame, math, os
from settings import *

pygame.init()

def get_break_time(*,
	block_hardness,
	is_best_tool=False,
	tool_multiplier=1,
	can_harvest=False,
	tool_efficiency=False,
	efficiency_level=1,
	haste_effect=False,
	haste_level=1,
	mining_fatigue=False,
	mining_fatigue_level=1,
	in_water=False,
	has_aqua_affinity=False,
	on_ground=True):

	speedMultiplier = 1
	if is_best_tool:
		speedMultiplier = tool_multiplier

		if not can_harvest:
			speedMultiplier = 1

		elif tool_efficiency:
			speedMultiplier += efficiency_level ** 2 + 1


	if haste_effect:
		speedMultiplier *= 0.2 * haste_level + 1

	if mining_fatigue:
		speedMultiplier *= 0.3 ** min(mining_fatigue_level, 4)

	if in_water and not has_aqua_affinity:
		speedMultiplier /= 5

	if not on_ground:
		speedMultiplier /= 5

	damage = speedMultiplier / block_hardness

	if can_harvest:
		damage /= 30
	else:
		damage /= 100

	# Instant breaking
	if damage > 1:
		return 0

	ticks = math.ceil(1 / damage)

	seconds = ticks / 20

	return seconds

def get_slot_player_holding(player):
	return player.inventory[0][player.holding_index-1]

def get_item_image(name, convert_alpha=False):
	item_path = os.path.join(asset_path, 'items', name + '_item.png')
	if os.path.isfile(item_path):
		img = pygame.image.load(item_path)
		if convert_alpha:
			return img.convert_alpha()
		return img
	else:
		item_path = os.path.join(asset_path, 'items', 'texture_not_found_item.png')
		return pygame.image.load(item_path)

def get_block_image(name, convert_alpha=False):
	item_path = os.path.join(asset_path, 'blocks', name + '.png')
	if os.path.isfile(item_path):
		img = pygame.image.load(item_path)
		if convert_alpha:
			return img.convert_alpha()
		return img
	else:
		item_path = os.path.join(asset_path, 'blocks', 'texture_not_found.png')
		return pygame.image.load(item_path)

def write_text(font, text, **kwargs):
	transparency = kwargs.pop('transparency', 255)
	top_color    = kwargs.pop('top_color', 'white')
	bottom_color = kwargs.pop('bottom_color', (64,64,64))
	surface      = kwargs.pop('surface', False)

	if surface:
		top_text_surf = font.render(str(text), True, top_color)
		bottom_text_surf = font.render(str(text), True, bottom_color)

		top_text_surf.set_alpha(transparency)
		bottom_text_surf.set_alpha(transparency)

		rect = top_text_surf.get_rect(**kwargs)
		x,y = rect.topleft

		surface.blit(bottom_text_surf, (x+2,y+2))
		surface.blit(top_text_surf, (x,y))
	else:
		top_text_surf = font.render(str(text), True, top_color)
		bottom_text_surf = font.render(str(text), True, bottom_color)

		top_text_surf.set_alpha(transparency)
		bottom_text_surf.set_alpha(transparency)

		return top_text_surf, bottom_text_surf
