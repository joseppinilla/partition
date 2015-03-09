
"""Based on the graphics.py module"""
class Block():

    stateDict = {'free':0,'ocp':-1}
    
    def __init__(self,canvas,p,index,rows,cols):
        
        self.index = index
        self.state = self.stateDict['free']
        self.cell = -1
        self.p1X = (p[0])
        self.p1Y = (p[1])
        self.p2X = (p[2])
        self.p2Y = (p[3])
        self.blockX = self.index%cols
        self.blockY = (self.index-self.blockX)//cols
        canvas.create_rectangle(*p, fill="white")
            
    def getBlockXY(self,cols,rows):
        """ Remainder and Floored Quotient return Cell coordinates """
        return self.blockX , self.blockY
    
    def getIndex(self):
        return self.index
    
    def setCell(self,cell):
        self.state = self.stateDict["ocp"]
        self.cell = cell
        
    def getCell(self):
        return self.cell

    def getCenter(self):
        return (self.p1X+self.p2X)/2.0, (self.p1Y+self.p2Y)/2.0
                
    def isFree(self):
        return (self.state == self.stateDict['free'])
    
    def isOcp(self):
        return (self.state == self.stateDict['ocp'])
        
    def free(self):
        self.state = self.stateDict['free']
        self.cell = -1
    