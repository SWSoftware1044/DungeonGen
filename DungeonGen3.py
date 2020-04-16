import random
import math
from PIL import Image,ImageDraw
from collections import namedtuple
from bresenham import bresenham

WIDTH = 200
HEIGHT = 200
Tile = namedtuple('Tile','y x')

random.seed('***REMOVED***')

class AutomaticCell:
    def __init__(self,h,w):
        self.h = h
        self.w = w
        self.level = [[False for _ in range(self.w)] for _ in range(self.h)]
        self.caves = []
        self.cavesWalls = []

        self.sims = 8           #Number of times to run the celular automata model
        self.initLive = 0.40    #Initial amout of live cells.
        self.death = 4          #Cells with below this amount of neighbors will die
        self.birth = 4          #Cells with more than, or equal to this amount of neigbors will spontaneously resurect.
        self.minCave = 50       #Minimum size of a valid cave in cells
        self.minNei = 2         #Minimum number of neighbors for a valid wall.

    def GENERATE(self):
        '''Performs level generation.'''
        self.setUpInitial()
        for _ in range(self.sims):
            self.level = self.stepSimulate()
        self.cleanup()
        self.connect()
        return self.level

    def neighbors(self,y,x):
        '''Counts up neighboring live cells, treating Out Of Bounds as alive.'''
        count = 0
        for j in range(-1,2):
            for i in range(-1,2):
                if j==0 and i==0: continue
                Ny,Nx = y+j,x+i
                if Ny < 0 or Ny == self.h or Nx == 0 or Nx == self.w:
                    count += 1
                elif self.level[Ny][Nx]:
                    count += 1
        return count

    def orthNeighbors(self,y,x):
        '''Counts up orthagonal neighboring live cells.'''
        return len([(j,i) for j,i in ((y-1,x), (y+1,x), (y,x-1), (y,x+1)) if 0<=j<self.h and 0<=i<self.w and self.level[j][i]])

    def floodFill(self,y,x):
        '''Floods cave areas from a point (y,x), ignoring walls.'''
        cave = set()
        toBeFilled = set([Tile(y,x)])
        while toBeFilled:
            tile = toBeFilled.pop()
            if tile not in cave:
                cave.add(tile)
                self.level[tile.y][tile.x] = True
                for adj in [Tile(j,i) for j,i in ((tile.y-1,tile.x), (tile.y+1,tile.x), (tile.y,tile.x-1), (tile.y,tile.x+1)) if 0<=j<self.h and 0<=i<self.w and not self.level[j][i]]:
                    if self.level[adj.y][adj.x] == 0:
                        if adj not in toBeFilled and adj not in cave:
                            toBeFilled.add(adj)
        if len(cave) >= self.minCave:
            self.caves.append(list(cave))

    def calcWalls(self,cave):
            caveNeighbors = dict()
            for tile in cave:
                caveNeighbors[tile] = self.neighbors(tile.y,tile.x)
            return [k for k,v in caveNeighbors.items() if v >= self.minNei]

    def setUpInitial(self):
        '''Sets up initial map, before cell simulation is applied. Percent of living cells is controlled by 'self.initLive' parameter.'''
        for y,row in enumerate(self.level):
            for x,_ in enumerate(row):
                if random.random() < self.initLive:
                    self.level[y][x] = True

    def stepSimulate(self):
        '''Simulates one step in the cell simulation process.'''
        levelChanged = [[False for _ in range(self.w)] for _ in range(self.h)]
        for y,row in enumerate(self.level):
            for x,wall in enumerate(row):
                surrounding = self.neighbors(y,x)
                if wall:
                    if surrounding < self.death: levelChanged[y][x] = False
                    else: levelChanged[y][x] = True
                else:
                    if surrounding >= self.birth: levelChanged[y][x] = True
                    else: levelChanged[y][x] = False
        return levelChanged

    def cleanup(self):
        '''Removes caves below the minmum cell requirement and live cells with only one neighbor.'''
        for y,row in enumerate(self.level):
            for x,wall in enumerate(row):
                if wall and self.orthNeighbors(y,x) <= 1:
                    self.level[y][x] = False
        for y,row in enumerate(self.level):
            for x,wall in enumerate(row):
                if not wall: self.floodFill(y,x)
        for cave in self.caves:
            for tile in cave:
                self.level[tile.y][tile.x] = False
        for cave in self.caves:
            self.cavesWalls.append(self.calcWalls(cave))

    def connect(self):
        d = lambda a,b: (b.x-a.x)**2 + (b.y-a.y)**2
        t = lambda a: Tile(a[1],a[0])
        while len(self.caves) > 1:
            zeroCave = 0
            zeroCaveWalls = self.cavesWalls.pop(0)
            closeCave = None
            zeroWall = None
            closeWall = None
            minDist = 100000000000000000000000000000
            for wall in zeroCaveWalls:
                for i,otherCave in enumerate(self.cavesWalls):
                    for otherWall in otherCave:
                        dist = d(wall,otherWall)
                        if dist < minDist:
                            minDist = dist
                            zeroWall = wall
                            closeWall = otherWall
                            closeCave = i
            if closeCave >= len(self.caves): #TODO: Figure out this issue. Temporary patch applied.
                self.caves.pop(zeroCave)
                print("!WARN: Cave Skipped.")
                continue
            bresen=list(bresenham(zeroWall.x,zeroWall.y,closeWall.x,closeWall.y))
            bresen=list(map(t,bresen))
            print(f"Length Before Pop: {len(self.caves)}")
            print(f"-\nClose: {closeCave}:")
            print(f"{self.caves[closeCave][0]}\n-")
            closeCave = self.caves.pop(closeCave)
            zeroCave = self.caves.pop(zeroCave)
            self.caves.append(list(set.union(set(zeroCave),set(closeCave),set(bresen))))
            for tile in bresen:
                self.level[tile.y][tile.x]=False
            self.cavesWalls.append(self.calcWalls(self.caves[-1]))


AutoCell = AutomaticCell(HEIGHT,WIDTH)
level = AutoCell.GENERATE()
I = Image.new('RGB',(WIDTH,HEIGHT),(255,255,255))
iD = ImageDraw.Draw(I)

walls = []
for y,row in enumerate(level):
    for x,wall in enumerate(row):
        if wall:
            walls.append((x,y))

iD.point(walls,(0,0,0))
I.show()