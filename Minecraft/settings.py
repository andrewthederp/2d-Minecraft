# from blocks import *
import os, copy

TILE_SIZE = 64
HEIGHT    = TILE_SIZE*9
WIDTH     = TILE_SIZE*11
FPS       = 60

HALF_WIDTH = WIDTH//2
HALF_HEIGHT = HEIGHT//2

a = None
d = 'd'
g = 'g'
f = 'f'
s = 's'
p = 'p'
l = 'l'
w = 'w'

S = 'S'
c = 'c'

WORLD_MAP = [
[g, a, a, a, a, a, s, a, a, a, a, a, a, a, a, a, a, a, a, a],
[d, d, d, d, d, d, d, a, a, d, d, d, d, d, d, a, a, a, a, a],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, d, d, a, a, a, a],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, d, d, a, a, a],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, d, d, a, a],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, d, d, a],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, d, d],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, d,d],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a,d,d],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a,a,d,d],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a,a,a,d,d],
[a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a, a,a,a,a,a,a,g,g],
[a, a, a, a, a, a, a, a, a, a, a, a, a, l, a, a, a, a, a, a,a,a,a,a,g,d],
[a, a, a, a, a, a, a, a, a, a, a, a, l, l, l, a, a, a, a, a,a,a,a,g,d],
[a, a, a, a, a, a, a, a, g, a, a, l, l, w, l, l, a, a, a, a,a,a,g,d],
[a, a, s, s, a, a, g, g, d, g, a, a, a, w, a, a, a, a, a, a,a,g,d],
[a, s, s, s, s, a, d, d, d, d, g, a, a, w, a, a, a, a, a, a,g,d],
[s, s, s, s, s, g, d, d, d, d, d, g, g, g, g, g, g, g, g, g,d],
[d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d],
[d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d],
[d, d, d, d, S, d, d, d, S, d, d, d, S, S, d, d, d, d, d, d],
[d, d, S, S, S, d, d, d, S, S, d, S, S, d, d, S, d, d, d, d],
[S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S],
[S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S],
[S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S],
[S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S, S],
[c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c],
[c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c],
[c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c],
[c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c],
[c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c, c],
[d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d],
[d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d],
[d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d, d]
]

WORLD_COPY = copy.deepcopy(WORLD_MAP)

player_starting_coor = (1,0)

asset_path = os.path.join(os.path.dirname(__file__), 'assets')

FULL_DAY = 60*20
HALF_DAY = 60*10