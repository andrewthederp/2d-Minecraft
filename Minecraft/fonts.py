from settings import *
import pygame, os

font_path = os.path.join(asset_path, 'minecraft_font.ttf')

def get_font(size=30):
	font = pygame.font.Font(font_path, size)
	return font