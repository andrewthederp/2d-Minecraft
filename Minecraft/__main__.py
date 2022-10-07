import pygame, sys
from settings import *
from debug import debug
import traceback

class Game:
	def __init__(self):
		pygame.init()

		self.screen = pygame.display.set_mode((WIDTH,HEIGHT))
		pygame.display.set_caption('Minecraft')
		self.clock = pygame.time.Clock()

		from level import Level
		self.level = Level()

	def run(self):
		while True:
			events = pygame.event.get()
			for event in events:
				if event.type == pygame.QUIT:
					pygame.quit()
					sys.exit()

			self.screen.fill((135, 206, 250))
			try:
				self.level.run(events)
			except Exception:
				print(traceback.format_exc())
				pygame.quit()
				sys.exit()
			debug(f"FPS: {self.clock.get_fps():.2f}")
			pygame.display.update()
			self.clock.tick(FPS)

if __name__ == '__main__':
	game = Game()
	game.run()