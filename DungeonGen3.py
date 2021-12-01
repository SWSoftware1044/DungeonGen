import random
from PIL import Image,ImageDraw
from collections import namedtuple
from bresenham import bresenham
import time

DEBUG = False
WIDTH = 200
HEIGHT = 200
Tile = namedtuple('Tile','y x')

SQ_DIST = lambda a,b: (b.x-a.x)**2 + (b.y-a.y)**2
TRANSPOSE = lambda a: Tile(a[1],a[0])
ADD = lambda a,b: Tile(a.y+b.y,a.x+b.x)
FLATTEN = lambda l: [item for sublist in l for item in sublist]

#random.seed('DOG')

class AutomaticCell:
    def __init__(self,h,w):
        self.h = h
        self.w = w
        self.center = Tile(self.h//2,self.w//2)
        self.level = [[False for _ in range(self.w)] for _ in range(self.h)]
        self.caves = []
        self.cavesReferences = {}
        self.cavesWalls = []

        self.sims = 8           #Number of times to run the celular automata model
        self.initLive = 0.40    #Initial amout of live cells.
        self.death = 4          #Cells with below this amount of neighbors will die
        self.birth = 4          #Cells with more than, or equal to this amount of neigbors will spontaneously resurect.
        self.minCave = 50       #Minimum size of a valid cave in cells
        self.minNei = 4         #Minimum number of neighbors for a valid wall.

    def GENERATE(self):
        '''Performs level generation.'''
        self.setUpInitial()
        for _ in range(self.sims-2):
            self.level = self.stepSimulate()
        self.cleanup()
        self.connect()
        for _ in range(2):
            self.level = self.stepSimulate()
        self.cleanup()
        self.finalize()
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

    def orthSpecific(self,y,x):
        '''Counts up orthagonal neighboring live cells, returning the cells themcellves. Up, Down, Left, Right.'''
        returner = []
        for j,i in ((y-1,x), (y+1,x), (y,x-1), (y,x+1)):
            if 0<=j<self.h and 0<=i<self.w:
                returner.append(self.level[j][i])
            else:
                returner.append(True)
        return returner

    def floodFill(self,y,x):
        '''Floods cave areas from a point (y,x), ignoring walls.'''
        cave = set()
        toBeFilled = set([Tile(y,x)])
        while toBeFilled:
            tile = toBeFilled.pop()
            if tile not in cave:
                cave.add(tile)
                self.level[tile.y][tile.x] = True
                neighboringTiles = FLATTEN([[ADD(tile,Tile(i,j)) for i in range(-1,2) if not (i==0 and j==0)] for j in range(-1,2)])
                for adj in [Tile(j,i) for j,i in neighboringTiles if 0<=j<self.h and 0<=i<self.w and not self.level[j][i]]:
                    if self.level[adj.y][adj.x] == 0:
                        if adj not in toBeFilled and adj not in cave:
                            toBeFilled.add(adj)
        if len(cave) >= self.minCave:
            self.caves.append(list(cave))
            self.cavesReferences.update({k:len(self.caves)-1 for k in cave})

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
        # if self.level[self.center.y][self.center.x]:
        #     neighboringTiles = FLATTEN([[ADD(self.center,Tile(i,j)) for i in range(-1,2) if not (i==0 and j==0)] for j in range(-1,2)])
        #     for tile in neighboringTiles:
        #         if not self.level[tile.y][tile.x]:
        #             self.center = tile
        #             return
        #     raise RuntimeError("Center not found. Map invalid.")

    def connect(self):
        '''Connects caves using bresenham lines.'''
        cavesWalls = self.cavesWalls
        while len(cavesWalls) > 0:
            currentCaveWalls = cavesWalls.pop()
            for wall in currentCaveWalls:
                if len(cavesWalls) > 1:
                    randCave = random.randint(0,len(cavesWalls)-1)
                    randWall = cavesWalls[randCave][random.randint(0,len(cavesWalls[randCave])-1)]
                else:
                    randWall = self.center
                bresen = list(map(TRANSPOSE,list(bresenham(wall.x,wall.y,randWall.x,randWall.y))))
                active = False
                for i,point in enumerate(bresen[1:]):
                    if self.cavesReferences.get(point,-1) == self.cavesReferences[wall]:
                        break
                    elif point in self.cavesReferences and self.cavesReferences[point] != self.cavesReferences[wall]:
                        bresen = bresen[:i+1]
                        active = True
                        break
                if active:
                    for point in bresen:
                        for neighbor in FLATTEN([[ADD(point,Tile(i,j)) for i in range(-1,2)] for j in range(-1,2)]):
                            if self.level[neighbor.y][neighbor.x]: self.level[neighbor.y][neighbor.x] = False
                    break

    def finalize(self):
        for y,row in enumerate(self.level):
            for x,_ in enumerate(row):
                neighbors = self.orthSpecific(y,x)
                if not (neighbors[0] or neighbors[1]) or not (neighbors[2] or neighbors[3]):
                    self.level[y][x] = False


if __name__ == "__main__":
    AutoCell = AutomaticCell(HEIGHT,WIDTH)
    start = time.perf_counter()
    level = AutoCell.GENERATE()
    print(time.perf_counter() - start)
    
    I = Image.new('RGB',(WIDTH,HEIGHT),(255,255,255))
    iD = ImageDraw.Draw(I)

    walls = []
    for y,row in enumerate(level):
        for x,wall in enumerate(row):
            if wall:
                walls.append((x,y))
    iD.point(walls,(0,0,0))

    if DEBUG:
        cavesWalls = []
        for cave in AutoCell.cavesWalls:
            for tile in cave:
                cavesWalls.append((tile.x,tile.y))
        AutoCell.caves = []
        for y,row in enumerate(AutoCell.level):
            for x,wall in enumerate(row):
                if not wall: AutoCell.floodFill(y,x)
        Caves = []
        for cave in AutoCell.caves:
            Cave = []
            for tile in cave:
                Cave.append((tile.x,tile.y))
        iD.point(cavesWalls,(255,0,0))
        for Cave in Caves:
            iD.point(Cave,(random.randint(0,255),random.randint(0,255),random.randint(0,255)))
        iD.point((AutoCell.center.x,AutoCell.center.y),(0,0,255))
        print(f"Center Cave: {AutoCell.cavesReferences.get(AutoCell.center,'NONE')}")
    I.show()