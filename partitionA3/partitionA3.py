import time
import sys
import getopt
import partitionGUI
import random
import math
import bisect
import numpy as np
import Tkinter as tk
import networkx as nx
import matplotlib.pyplot as plt
from operator import itemgetter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from _bisect import bisect_left
from time import sleep


class Partition():
    """ Circuit Cell partitioning using Fiduccia-Matheyses
        Circuit: A representation of a circuit by Cells to be partitioned in two sites
        Cell: Circuit component represented as a Graph node with connections to other Cells as edges
        Node: Graph representation of a Cell
        Site: Possible location for a Cell (Is Free or is occupied by a Cell)
        Block: Graphic representation and data of a Site
     """  
    def __init__(self,master,seed,inputfile,quietMode):
        
        #=============Parse file to create cells graph===============#
        # Create Directed Graph and fill with input file
        self.G=nx.DiGraph()
        fin = open(inputfile,'r')
        self.getGraph(fin)
        fin.close() 
                
        #================Create Data Structures================# 
        # Array of Line objects to draw connections
        self.connLines = []
        # Array of Block objects drawing the rectangles for each site on the circuit, tracks occupancy.
        # One per partition 
        self.sitesA = []
        self.blocksA = []
        self.sitesB = []
        self.blocksB = []
        
        # List of Nodes sorted by gains
        self.gainOrder = []
        
        # Array of Text objects noting the name of the node assigned to a cell site 
        self.tags = []
        # Assign Initial Seed
        self.seed = seed
        #================Draw Buttons and plots================#
        self.master = master
        self.initialize_buttons()
        self.initialize_plots()
        
        # Quite Mode to run without graphics
        if quietMode:
            self.running = True
            # FM Partitioning Algorithm
            self._startpartition(True)
            sys.exit()

    def getGraph(self, fin):
        """ Parse Input File to fill up Graph structure """
        tmpList = fin.readline().split()
        # Number of Cells to be partitioned
        self.cells = int(tmpList[0])
        # Number of Connections or Nets
        self.conns = int(tmpList[1])
        # Number of Circuit Rows
        self.rows =  int(tmpList[2])
        # Number of Circuit Columns
        self.cols =  int(tmpList[3])
        # Number of available sites in the Circuit
        self.sitesNum = self.rows*self.cols
        
        
        self.winX = self.cols/4
        self.winY = self.rows/4
        
        # Add nodes from 0 to number of Cells to graph structure and initialize net array and net cost        
        self.G.add_nodes_from(range(0,self.cells))
        for node in self.G.nodes():
            self.G.node[node]["nets"]=[]
            self.G.node[node]["cost"]=0
            self.G.node[node]["cutCost"]=0
            self.G.node[node]["locked"]=False
            
        # For every Net, add edges between corresponding nodes
        for net in range(0,self.conns):
            tmpList = fin.readline().split()
            numNodes = int(tmpList[0])
            srcNode = int(tmpList[1])
            #self.G.node[srcNode]["nets"].append(srcNode)
            for conn in range(2,numNodes+1):
                self.G.add_edge(srcNode, int(tmpList[conn]))
                self.G.node[int(tmpList[conn])]["nets"].append(srcNode)

    def initialize_buttons(self):
        """ Draw User Buttons on top of interface 
            Start: Begin placement process
            Pause: Pause process. Allows continuing.
            Graph: Show Graph nodes to visualize connections
            Plot: Show Cost plot to see SA progress
            Draw: Show Circuit Cells
        """
        self.start_button = tk.Button(self.master, text='Start', command = self.startRunning)
        self.start_button.grid(row=0, column=0)

        self.pause_button = tk.Button(self.master, text='Pause', command = self.pauseRunning)
        self.pause_button.grid(row=0, column=1)

        self.graph_button = tk.Button(self.master, text='Graph', command = self.showGraph)
        self.graph_button.grid(row=0, column=2)
        
        self.plot_button = tk.Button(self.master, text='Plot', command = self.showPlot)
        self.plot_button.grid(row=0, column=3)
        
        self.draw_button = tk.Button(self.master, text='Draw', command = self.drawCells)
        self.draw_button.grid(row=0, column=4)
        
        # Initialize Button States and Actions
        self.pause_button['state'] = 'disabled'
        # Boolean switch to control flow of placement process
        self.running = False
        # Boolean switch to plot placement connections and tags, turn off for faster processing
        self.plot = False
        self.drawing = False
        self.graph = False
        # Boolean switch to specify first run and allow stop/continue behavior that doesn't initialize program
        self.firstRun = True

    def initialize_plots(self):
        """ Draw all graphic components as Canvases
            Circuit Canvas: Drawing of the Circuit Sites Rows and Columns to overlay Cell Placement and Connections
            Graph Canvas: Drawing of the Graph structure used for the representation of the Cells
            Cost Plot Canvas: Plotting of the Cost Function used in the Annealing Process
            Plot Toolbar: Toolbar options to explore the Graph and Cost Canvases (Zoom, Save, Move...)
         """
        #============================Draw circuit canvas=================================#
        # Draw Canvas with hardcoded width 600 and adjustable height to circuit input
        ckt_max_x = 600
        ckt_max_y = (ckt_max_x*(self.rows))/self.cols
        scale_x = round(ckt_max_x / self.cols)
        scale_y = round(ckt_max_y / self.rows)
        self.canvasCirkt = tk.Canvas(self.master,width=ckt_max_x+scale_x,height=(ckt_max_y*2)+int(scale_y))
        self.canvasCirkt.grid(row=1,column=1,columnspan=4)

        # Draw border
        self.canvasCirkt.create_rectangle(1, 1, (ckt_max_x+2)/2, (ckt_max_y*2)+int(scale_y))
        self.canvasCirkt.create_rectangle(((ckt_max_x+2)/2)+scale_x, 1, ckt_max_x+scale_x, (ckt_max_y*2)+int(scale_y))
        
        # Draw cell rows and columns in two groups
        blockIndex=0
        for cut in range(int(scale_y), int(ckt_max_y*2), int(scale_y)*2):
            for cut2 in range(1, int(ckt_max_x), int(scale_x)):
                if (cut2>ckt_max_x/2):
                    cut2+=scale_x
                # Coordinates for top and bottom points of rectangle
                points = (cut2, cut, cut2+scale_x-1, cut+scale_y)
                blockObj = partitionGUI.Block(self.canvasCirkt,points,blockIndex,self.rows,self.cols)
                blockIndex+=1
                if (cut2>ckt_max_x/2):
                    self.blocksB.append(blockObj)
                else:
                    self.blocksA.append(blockObj)
                    
                
        #===================================Draw Plots================================#
        # Draw Figure for 2 subplots (Connections Graph and Cost Function)        
        self.figure, self.axes = plt.subplots(2, facecolor="white")
        self.figure.set_figwidth(4)
        self.axGraph = self.axes[0]
        self.axCost = self.axes[1]
        
        # Initial condition for connection Graph
        self.axGraph.set_visible(False)
        
        # Select Cost Plot as current Axis. Get lines to use for plot updates
        plt.sca(self.axCost)       
        self.lines, = self.axCost.plot([],[])
        self.axCost.set_xlabel("Time")
        self.axCost.set_title("Cost")

        # Draw Cost function Plot
        self.canvasPlot = FigureCanvasTkAgg(self.figure, master=self.master)
        self.canvasPlot.get_tk_widget().grid(row=1,column=0)
        
        # Draw Tool Bar
        self.toolbarFrame = tk.Frame(self.master)
        self.toolbarFrame.grid(row=2,column=0,columnspan=3,sticky="W")
        self.toolbarPlot = NavigationToolbar2TkAgg(self.canvasPlot,self.toolbarFrame)
           
    def showGraph(self):
        """ User selection to display graph """
        self.graph_button['state'] = 'disabled'
        # Draw connection Graph
        self.axGraph.set_visible(True)
        nx.draw(self.G, ax=self.axGraph, with_labels=True)
        self.canvasPlot.draw()
        self.canvasPlot.flush_events()
        
    def showPlot(self):
        """ User selection to display Cost """
        self.plot = not self.plot
        if self.plot:
            self.plot_button['text'] = "No Plot"
        else:
            self.plot_button['text'] = "Plot"
    
    def drawCells(self):
        """ User selection to display Circuit Cells """
        self.drawing = not self.drawing
        if self.drawing:
            self.draw_button['text'] = "No Draw"
        else:
            self.draw_button['text'] = "Draw"

    def startRunning(self):
        """ User control for placement process """
        self.start_button['state'] = 'disabled'
        self.pause_button['state'] = 'normal'
        self.running = True
        
        # If first run and not continuation from pause
        if (self.firstRun):
            self.start_timer = time.clock()
        # Simulated Annelaing Function
        self._startpartition(False)
        # Always display result at the end of the process
        self.updateDraw()
        #self.updatePlot() #TODO: What to plot
        # Disable Buttons when finished
        self.pause_button['state'] = 'disabled'
        self.plot_button['state'] = 'disabled'
        self.draw_button['state'] = 'disabled'

    def pauseRunning(self):
        """ Pause process of SA by exiting loop """
        self.start_button['state'] = 'normal'
        self.pause_button['state'] = 'disabled'
        self.running = False
        
    def _startpartition(self,quietMode):
        """ Start Partitioning Process """
        
        # On first run to random placement. This allows pausing and continuing the process
        if (self.firstRun == True):
            self.splitPlace()
            self.gain()
            self.firstRun=False
            self.cutCost()
        
        startTimer = time.clock()
        
               
        self.totalCutCost = self.FMPartition(quietMode)
        
        timeDif = time.clock() - startTimer
        
        print self.totalCutCost, " ",
        print timeDif

            
        
        
    def FMPartition(self,quietMode):
        
        bestCutCost = self.totalCutCost
        
        for loop in range(0,6):        
            difParts = -1
            i=1            
            self.cntLocked = 0
    
    
            while self.cntLocked<self.cells:
                            
                # While difference means the move will unbalance partitions        
                while not (2>=difParts>=0):
                                   
                    moveNode = self.gainOrder[self.cells-i][1]
                    moveNodePart = self.G.node[moveNode]["part"]
                    
                    if self.G.node[moveNode]["locked"]:
                        i+=1
                        continue
                                
                    if moveNodePart == 'A':
                        movePartSites = self.sitesA
                        tgtPartSites = self.sitesB
                        tgtPart = 'B'
                    else: 
                        movePartSites = self.sitesB
                        tgtPartSites = self.sitesA
                        tgtPart = 'A'
                
                    
                    
                    # Difference on the number of cells on each site
                    difParts = len(movePartSites)-len(tgtPartSites) #TODO: Change for incremental size for performance 
                    i+=1
                
                           
                i=1
                self.G.node[moveNode]["locked"]=True
                self.cntLocked+=1
                movePartSites.remove(moveNode)
                tgtPartSites.append(moveNode)
                self.G.node[moveNode]["part"] = tgtPart
                self.incrGain(moveNode)
                difParts = -1
            
                self.cutCost()
                if not quietMode:
                    self.axCost.set_title("Best Cost=" + str(bestCutCost))
                    self.updatePlot(self.totalCutCost)
                
                # Store best result
                if (self.totalCutCost<=bestCutCost):
                    self.sitesABkp = self.sitesA
                    self.sitesBBkp = self.sitesB
                    self.gainOrderBkp = self.gainOrder
                    self.GBkp = self.G
                    bestCutCost=self.totalCutCost
            
            self.cntLocked=0
            for node in self.G.nodes():
                self.G.node[node]["locked"]=False
            

            self.sitesA = self.sitesABkp 
            self.sitesB = self.sitesBBkp
            self.gainOrder = self.gainOrderBkp
            self.G = self.GBkp
        
        return bestCutCost
        
    def cutCost(self):
        
        self.totalCutCost = 0 
        
        for node in self.G.nodes():
            
            nodePart = self.G.node[node]["part"]
            
            for nb in self.G.neighbors(node):
                if self.G.node[nb]["part"]!=nodePart:
                    self.totalCutCost+=1
                    self.G.node[node]["cutCost"] = 1
                    break



    def cutIncrCost(self):
        pass #TODO:
           

    def updateDraw(self):
        """ Draw circuit Connections and Cell Tags """
        self.delConns()
        self.delTags()
        self.drawConns()
        self.drawTags()
    
    def updatePlot(self,cost):
        """ Cost plot gets updated on every new cost value """
        timer = time.clock() - self.start_timer
        # Add new values to plot data set        
        self.lines.set_xdata(np.append(self.lines.get_xdata(), timer))
        self.lines.set_ydata(np.append(self.lines.get_ydata(), cost))
        # Re-scale
        self.axCost.relim()
        self.axCost.autoscale_view()
        # Update plot
        self.canvasPlot.draw()
        self.canvasPlot.flush_events()


    def splitPlace(self):
        """ SPlit placement, for every node a Partition is assigned """
        
        
        
        nodeSortedIter = sorted(self.G.degree_iter(),key=itemgetter(1),reverse=True)
        
        placeCnt = 0
        
        for node in nodeSortedIter:
            if placeCnt>self.cells/2:
                self.sitesA.append(node[0])
                self.G.node[node[0]]["part"] = 'A'
            else:
                self.sitesB.append(node[0])
                self.G.node[node[0]]["part"] = 'B'
            placeCnt+=1
            

        

    def randPlace(self):
        """ Random placement, for every node a Site is assigned """
        random.seed(self.seed)
        
        # Start placement on Partition A
        partA = True
        for node in self.G.nodes():
            
            randSite = random.randint(0,int(self.sitesNum/2)-1)
            
            if partA:
                partSite = self.sitesA
                self.G.node[node]["part"] = 'A'
                
            else:
                partSite = self.sitesB
                self.G.node[node]["part"] = 'B'
                       
            while (partSite[randSite].isOcp()):
                randSite = random.randint(0,int(self.sitesNum/2)-1)    

            partSite[randSite].setCell(node)
            self.G.node[node]["site"] = partSite[randSite]
            
            # Toggle partition for next placement
            partA = not partA
                
            
    def drawConns(self):
        """ Extract center point from each node and draw connection to other nodes """
        for node in self.G.nodes():
            pX,pY = self.G.node[node]["site"].getCenter()
            for nb in self.G.neighbors(node):
                nbX,nbY = self.G.node[nb]["site"].getCenter()
                self.connLines.append(self.canvasCirkt.create_line(pX,pY,nbX,nbY))
            self.canvasCirkt.update()

    def drawTags(self):
        """ Extract center point from each node and draw node Tag """
        for node in self.G.nodes():
            pX,pY = self.G.node[node]["site"].getCenter()
            self.tags.append(self.canvasCirkt.create_text(pX, pY, text=node))            
        self.canvasCirkt.update()
    
    def delConns(self):
        """ Delete Connections on Circuit using array of Line objects """
        for line in self.connLines:
            self.canvasCirkt.delete(line)
        self.canvasCirkt.update()    
            
    def delTags(self):
        """ Delete Tags on Circuit using array of Text objects """
        for tag in self.tags:
            self.canvasCirkt.delete(tag)
        self.canvasCirkt.update()
        
    def gain(self):
        """ Find the gain of every node by finding the difference between the number of nodes connected to that node on the same partition (retention force)
        and the number of nodes connected that are on the other partition (moving force)"""
               
        for node in self.G.nodes():
            # Get number of nodes connected on same and other partition
            movForce, retForce = self.nodeForces(node)
            nodeGain =  movForce-retForce

            #Fill list of Nodes with gains
            self.gainOrder.append((nodeGain,node))
       
        self.gainOrder.sort(key=lambda r: r[0])
        self.keys = [r[1] for r in self.gainOrder]        
        
        
    def incrGain(self,movedNode):
        
        movedNets = set([movedNode])
        movedNets.update(self.G.neighbors(movedNode))
        movedNets.update(self.G.node[movedNode]["nets"])
                
        for movedNet in movedNets:
            movForce, retForce = self.nodeForces(movedNet)
            nodeGain =  movForce-retForce
            del self.gainOrder[self.keys.index(movedNet)]
            bisect.insort(self.gainOrder, (nodeGain,movedNet))
            self.keys = [r[1] for r in self.gainOrder]

            
    def nodeForces(self,node):
        
        nodePart = self.G.node[node]["part"]              
        movForce = 0
        retForce = 0
        
        
        for nb in set(self.G.neighbors(node)):
            if nodePart != self.G.node[nb]["part"]:
                movForce+=1
            else:
                retForce+=1

        connNodes = set(self.G.node[node]["nets"])
               
        for connNode in connNodes:           
            if nodePart != self.G.node[connNode]["part"]:
                movForce+=1
            else:
                retForce+=1

        return movForce, retForce
    

       
    def quitApp(self):
        """ Exit """
        self.master.destroy()
        self.master.quit()


def main(argv):
    #==============Initialize Graphics============#
    root = tk.Tk()   
    #=================Options=================#
    # Default Values
    inputfile = None
    quietMode = False
    seed = 30
    
    
    try:
        opts, args = getopt.getopt(argv, "hqs:t:i:", ["ifile="])
    except getopt.GetoptError:
        print 'test.py -i <inputfile>'
        sys.exit(2)
    
    for opt, arg in opts:
        if opt == '-h':
            print 'test.py -i <inputfile> [-q] [-s <Seed>]'
            print "-q : Quiet Mode"
            print "-t <Temperature>: Initial temperature for SA"
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt == '-s':
            seed = int(arg)
        elif opt == "-q":
            quietMode = True
    
    if (not inputfile):
        print 'test.py -i <inputfile>'
        sys.exit(2)
    
    partition = Partition(root,seed,inputfile,quietMode)
    root.wm_title("FM Partitioning Tool. EECE583: Jose Pinilla")
    root.protocol('WM_DELETE_WINDOW', partition.quitApp)
    root.resizable(False, False)
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv[1:])
