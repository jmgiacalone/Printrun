"""
oozestep is a script to minimise ooze from a stepper based extruder.

The oozestep script has been written by Jean-Marc Giacalone.

In order to install the oozestep script within the skeinforge tool chain, put oozestep.py in the skeinforge_application/skeinforge_plugins/craft_plugins/ 
folder. Then edit  skeinforge_application/skeinforge_plugins/profile_plugins/extrusion.py and add the oozestep script to the tool chain sequence by 
inserting 'oozestep' into the tool sequence  in getCraftSequence(). The best place is at the end of the sequence, right before 'export'.

==Operation==
The default 'Activate oozestep' checkbox is off, enable it if using a stepper based extruder.

==Settings==
===some stuff in here===
details here
The following examples oozestep the file Screw Holder Bottom.stl.  The examples are run in a terminal in the folder which contains Screw Holder Bottom.stl and oozestep.py.


> python oozestep.py
This brings up the oozestep dialog.


> python oozestep.py Screw Holder Bottom.stl
The oozestep tool is parsing the file:
Screw Holder Bottom.stl
..
The oozestep tool has created the file:
Screw Holder Bottom_oozestep.gcode


> python
Python 2.5.1 (r251:54863, Sep 22 2007, 01:43:31)
[GCC 4.2.1 (SUSE Linux)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import oozestep
>>> oozestep.main()
This brings up the oozestep dialog.


>>> oozestep.writeOutput( 'Screw Holder Bottom.stl' )
Screw Holder Bottom.stl
The oozestep tool is parsing the file:
Screw Holder Bottom.stl
..
The oozestep tool has created the file:
Screw Holder Bottom_oozestep.gcode

"""


from __future__ import absolute_import
#Init has to be imported first because it has code to workaround the python bug where relative imports don't work if the module is imported as a main module.
import __init__

from skeinforge_application.skeinforge_utilities import skeinforge_profile
from skeinforge_application.skeinforge_utilities import skeinforge_polyfile
from fabmetheus_utilities import euclidean
from fabmetheus_utilities import gcodec
from fabmetheus_utilities import archive
from fabmetheus_utilities.fabmetheus_tools import fabmetheus_interpret
from fabmetheus_utilities import settings
from skeinforge_application.skeinforge_utilities import skeinforge_craft
from fabmetheus_utilities.vector3 import Vector3
import sys
from math import *

__author__ = "Jean-Marc Giacalone (jmgiacalone@hotmail.com)"
__date__ = "$Date: 2011/03/08 $"
__license__ = "GPL 3.0"

X = 0
Y = 1
E = 2

def getCraftedText( fileName, text = '', repository = None ):
	"oozestep the file or text."
	return getCraftedTextFromText( archive.getTextIfEmpty( fileName, text ), repository )

def getCraftedTextFromText( gcodeText, repository = None ):
	"oozestep a gcode linear move text."
	if gcodec.isProcedureDoneOrFileIsEmpty( gcodeText, 'oozestep' ):
		return gcodeText
	if repository == None:
		repository = settings.getReadRepository( oozestepRepository() )
	if not repository.activateoozestep.value:
		return gcodeText
	return oozestepSkein().getCraftedGcode( gcodeText, repository )

def getStringFromCharacterSplitLine( character, splitLine):
	"Get the string after the first occurence of the character in the split line."
	indexOfCharacter = gcodec.getIndexOfStartingWithSecond(character, splitLine)
	if indexOfCharacter < 0:
		return None
	return splitLine[indexOfCharacter][1 :]

def myformat(x, dp = 2):
	if dp == 0:
	    return ('%.0f' % x)
	elif dp == 1:
	    return ('%.1f' % x).rstrip('0').rstrip('.')
	elif dp == 2:
	    return ('%.2f' % x).rstrip('0').rstrip('.')
	elif dp == 3:
	    return ('%.3f' % x).rstrip('0').rstrip('.')
	#endif    

#def getRepositoryConstructor():
#	"Get the repository constructor."
#	return oozestepRepository()

def getNewRepository():
	"Get the repository constructor."
	return oozestepRepository()

def writeOutput( fileName = ''):
	"oozestep a gcode linear move file."
	fileName = fabmetheus_interpret.getFirstTranslatorFileNameUnmodified(fileName)
	if fileName == '':
		return
	skeinforge_craft.writeChainTextWithNounMessage( fileName, 'oozestep')

class oozestepRepository:
	"A class to handle the oozestep settings."
	def __init__( self ):
		"Set the default settings, execute title & settings fileName."
		skeinforge_profile.addListsToCraftTypeRepository( 'skeinforge_tools.craft_plugins.oozestep.html', self )
		self.fileNameInput = settings.FileNameInput().getFromFileName( fabmetheus_interpret.getGNUTranslatorGcodeFileTypeTuples(), 'Open File for oozestep', self, '' )
		self.activateoozestep = settings.BooleanSetting().getFromValue( 'Activate oozestep', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Feedrates -', self )
		#zFeed
		self.zFeed = settings.FloatSpin().getFromValue( 4.0, 'Z feed (mm/s):', self, 34.0, 8.3 )
		#first layer feed
		self.firstLayerFeed = settings.FloatSpin().getFromValue( 4.0, 'First layer feed (mm/s):', self, 34.0, 25 )
		#join paths - NOT USED
		#self.joinPaths = settings.FloatSpin().getFromValue( 4.0, 'Join paths (mm):', self, 34.0, 2.0 )
		#output G1
		self.g_one = settings.BooleanSetting().getFromValue( 'Output G1 for linear feed moves', self, False )
		settings.LabelSeparator().getFromRepository(self)
		settings.LabelDisplay().getFromName('- Extruder control -', self )
		#first path press dist
		self.firstPathPressDist = settings.FloatSpin().getFromValue( 4.0, 'First path press dist (mm):', self, 34.0, 30.0 )
		#first path press feed
		self.firstPathPressFeed = settings.FloatSpin().getFromValue( 4.0, 'First path press feed (mm/s):', self, 34.0, 30.0 )
		#first path each layer press dist
		self.firstLayerPathPressDist = settings.FloatSpin().getFromValue( 4.0, 'First layer path press dist (mm):', self, 34.0, 30.0 )
		#next path press xy
		self.nextPathPressXY = settings.FloatSpin().getFromValue( 4.0, 'Next path press XY (mm):', self, 34.0, 0.4 )
		#extruder early stop xy
		self.extruderEarlyStopXY = settings.FloatSpin().getFromValue( 4.0, 'Extruder early stop XY (mm):', self, 34.0, 0.4 )
		#extruder oozestep feed
		#set in Dimension plugin
		#extrusion multiplier - NOT USED
		#self.extrusionMultiplier = settings.FloatSpin().getFromValue( 0, 'Extrusion multiplier:', self, 255, 1.0 )
		self.tempAtLayer = settings.StringSetting().getFromValue('Bed T at layer, (Layer,Temp;Layer,Temp;...):', self, '4,120;7,110;10,100' )
		#Create the archive, title of the execute button, title of the dialog & settings fileName.
		self.executeTitle = 'oozestep'

	def execute( self ):
		"oozestep button has been clicked."
		fileNames = skeinforge_polyfile.getFileOrDirectoryTypesUnmodifiedGcode( self.fileNameInput.value, fabmetheus_interpret.getImportPluginFilenames(), self.fileNameInput.wasCancelled )
		for fileName in fileNames:
			writeOutput( fileName )

class oozestepSkein:
	"A class to oozestep a skein of extrusions."
	def __init__( self ):
		self.distanceFeedRate = gcodec.DistanceFeedRate()
		self.lineIndex = 0
		self.lines = None
		self.extruderActive = False
		self.currPath = []
		self.pathDist = 0
		self.currFeed = 0
		self.oldLocation = None
		self.currFeed = 0
		self.lastFeedRateString = ''
		self.lastXString = '0'
		self.lastYString = '0'
		self.lastEString = '0'
		self.lastZString = '0'
		self.extruderReverseFeed = 0
		self.nextPathPressDist = 0
		self.extruderoozestepDist = 0
		self.currLayer = -1
		self.currPos = [0,0]
		self.feed = 0
		self.isFirstPath = True
		self.M101Line = "M101"
		self.M103Line = "M103"
		self.isNewLayer = False
		self.cTatL = 0
		self.TatL_ = []

	def getCraftedGcode( self, gcodeText, repository ):
		"Parse gcode text and store the oozestep gcode."
		self.repository = repository
		self.lines = archive.getTextLines( gcodeText )
		self.TatL = self.repository.tempAtLayer.value.split(";")
		for i in range( len( self.TatL)):
			x,y = self.TatL[i].split(",")
			self.TatL_.append([int(x),int(y)])
		#end for
		print self.TatL_
		self.parseInitialization()
		for line in self.lines[ self.lineIndex : ]:
			#print line
			self.parseLine( line )
		return self.distanceFeedRate.output.getvalue()

	def parseInitialization(self):
		'Parse gcode initialization and store the parameters.'
		for self.lineIndex in xrange(len(self.lines)):
			line = self.lines[self.lineIndex]
			splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
			firstWord = gcodec.getFirstWord(splitLine)
			self.distanceFeedRate.parseSplitLine(firstWord, splitLine)
			if firstWord == '(</extruderInitialization>)':
				self.distanceFeedRate.addLine('(<procedureName> oozestep </procedureName>)')
				return
			elif firstWord == '(<operatingFeedRatePerSecond>':
				self.feed = 60.0 * float(splitLine[1])
			self.distanceFeedRate.addLine(line)
	
	def parseLine( self, line ):
		"Parse a gcode line and add it to the stretch skein."
		#print line
		splitLine = gcodec.getSplitLineBeforeBracketSemicolon(line)
		if len(splitLine) < 1:
			return
		firstWord = splitLine[0]
		if line.find( 'crafting' ) >= 0:
			#print 'started'
			self.currLayer = 0
		#endif
		if line.find( 'layer' ) >= 0:
			#self.currLayer += 1
			if self.cTatL<len(self.TatL_):
				#print "self.cTatL=%s" + str(self.cTatL)
				#print "self.currLayer=%s" + str(self.currLayer)
				#print "self.TatL_[self.cTatL][0]=%s" + str(self.TatL_[self.cTatL][0])
				if self.currLayer == self.TatL_[self.cTatL][0] - 1:
					cline = "M140 S" + str(self.TatL_[self.cTatL][1]) + "\n"
					#print cline
					self.distanceFeedRate.addLine(cline)
					self.cTatL += 1
				#endif
			#endif
		#endif
		if self.currLayer >= 0:
			#check for F word and save as current feed if changed
			feedRateString = getStringFromCharacterSplitLine('F', splitLine )
			#print feedRateString
			if feedRateString != None and feedRateString != self.lastFeedRateString:
				self.feed = feedRateString
				#print 'feed = ' + self.feed
			self.lastFeedRateString = feedRateString
			if firstWord == 'G1':
				#deal with a move line
				if splitLine[1][0] == 'E':
					if self.extruderActive == False:
						#we see an E word but extruderActive = False, store value as press dist
						if not self.isFirstPath:
							if not self.isNewLayer:
								self.nextPathPressDist = float(getStringFromCharacterSplitLine('E', splitLine ))
							else:
								self.nextPathPressDist = self.repository.firstLayerPathPressDist.value
								self.isNewLayer = False
							#endif
						else:
							self.nextPathPressDist = self.repository.firstPathPressDist.value
							#self.isFirstPath = False
						#endif
						#print 'nextPathPressDist=' + self.nextPathPressDist
						self.extruderReverseFeed = self.feed
					else:
						#we see an E word but extruderActive = True, store value as oozestep dist
						self.extruderoozestepDist = float(getStringFromCharacterSplitLine('E', splitLine ))
					#endif
				elif self.extruderActive and (splitLine[1][0] == 'X' or splitLine[1][0] == 'Y'):
					location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
					if self.oldLocation != None:
						self.pathDist += abs(location - self.oldLocation)
					self.currPath.append ( [location.x,location.y,float(self.Edist( splitLine ))] )
					self.oldLocation = location
				else:
					#extruderActive = False and no E word
					line = self.getTravelLine( splitLine )
					location = gcodec.getLocationFromSplitLine(self.oldLocation, splitLine)
					self.oldLocation = location
				#endif
			elif firstWord == 'M101':
				self.extruderActive = True
				self.M101Line=line
			elif firstWord == 'M103':
				self.extruderActive = False
				self.M103Line=line
				if self.currLayer > 1:
					self.xyFeed = self.feed
				else:
					self.xyFeed = float(self.repository.firstLayerFeed.value) * 60
				#endif
				#print "currLayer %s" % self.currLayer
				#print "xyFeed %s" % self.xyFeed
				#write path
				self.distanceFeedRate.addLine(self.M101Line)
				line = self.getCleanExtrudePath( self.pathDist , self.currPath )
				self.distanceFeedRate.addLine(self.M103Line)
				self.pathDist = 0
				del self.currPath[:]
				#self.distanceFeedRate.addLine(line)
			else:
				#any other type of line, so just write it to the output
				self.distanceFeedRate.addLine(line)
			#endif
		else:
			self.distanceFeedRate.addLine(line)
		#endif

	"""
	Function: getCleanExtrudePath( self , dist , path)
	Arguments: path distance, path([xpos,ypos,edist],...)
	"""
	def getCleanExtrudePath( self , dist , path ):
		#print "path %s" % path
		#print "dist " + str(dist)
		#r=0
		#deal with one segment path
		if len(path) == 1:
			path.append([ path[0][X], path[0][Y], path[0][E] / 2 ])
			### TODO set intermediate position so only 3 segments to complete the move ###
			#MoveDist = sqrt((path[0][X] - self.currPos[X])**2 + (path[0][Y] - self.currPos[Y])**2)
			#dX = path[0][X] - self.currPos[X]
			#dY = path[0][Y] - self.currPos[Y]
			path[0][X] = (self.currPos[X] + path[0][X]) / 2
			path[0][Y] = (self.currPos[Y] + path[0][Y]) / 2
			path[0][E] = path[0][E] / 2
		#endif
		if dist < (self.repository.nextPathPressXY.value + self.repository.extruderEarlyStopXY.value):
			return
		#endif
		currDist = 0
		if self.isFirstPath:
			#feed = self.feed
			feed = self.repository.firstPathPressFeed.value * 60
			self.isFirstPath = False
		else:
			feed = self.extruderReverseFeed
		#endif
		### navigate current path ###
		DonePressurise = False
		Reversing = False
		for Segment in path:
			#calc cumul move dist to end of current segment
			MoveDist = sqrt((Segment[X] - self.currPos[X])**2 + (Segment[Y] - self.currPos[Y])**2)
			if MoveDist:
				#print "MoveDist %s" % MoveDist 
				currDist += MoveDist
				### pressurise melt zone ###
				if not DonePressurise:
					if currDist >= self.repository.nextPathPressXY.value:
						#i = (Segment[X] - self.currPos[X]) / MoveDist
						#j = (Segment[Y] - self.currPos[Y]) / MoveDist
						mXY = MoveDist + self.repository.nextPathPressXY.value - currDist
						dXY = mXY / MoveDist
						#print 'b'
						mX = self.currPos[X] + ((Segment[X] - self.currPos[X]) * dXY)
						mY = self.currPos[Y] + ((Segment[Y] - self.currPos[Y]) * dXY)
						self.move_XY( [mX , mY , self.nextPathPressDist * mXY / self.repository.nextPathPressXY.value ] , feed )
						feed = self.xyFeed
						#print 'c'
						self.move_XY( [Segment[X] , Segment[Y] , Segment[E] * (1 - dXY)] , feed )
						DonePressurise = True
					else:
						#print 'a'
						self.move_XY([Segment[X], Segment[Y], self.nextPathPressDist * MoveDist / self.repository.nextPathPressXY.value] , feed)
					#endif
				elif self.repository.extruderEarlyStopXY.value and not Reversing:
					DistToGo = dist - currDist
					#print "currDist " + str(currDist)
					#print "DistToGo " + str(DistToGo)
					###deal with extruder early stop and oozestep###
					if (dist -  self.repository.nextPathPressXY.value) >= self.repository.extruderEarlyStopXY.value:
						distE = self.repository.extruderEarlyStopXY.value
					else:
						distE = (dist -  self.repository.nextPathPressXY.value)
					#endif
					if DistToGo < distE:
						#first oozestep segment
						#i = (Segment[X] - self.currPos[X]) / MoveDist
						#j = (Segment[Y] - self.currPos[Y]) / MoveDist
						mXY = self.repository.extruderEarlyStopXY.value - DistToGo
						#print "mXY " + str(mXY)
						dXY = 1 - ( mXY / MoveDist )
						#print "dXY " + str(dXY)
						mX = self.currPos[X] + (Segment[X] - self.currPos[X]) * dXY
						mY = self.currPos[Y] + (Segment[Y] - self.currPos[Y]) * dXY
						#print "X from " + str(Segment[X]) + " to " + str(self.currPos[X])
						#print "Y from " + str(Segment[Y]) + " to " + str(self.currPos[Y])
						#print "mX " + str(mX)
						#print "mY " + str(mY)
						#print 'B'
						self.move_XY([mX , mY , Segment[E] * dXY] , feed)
						#print 'C'
						feed = self.extruderReverseFeed
						self.move_XY( [Segment[X] , Segment[Y] , self.extruderoozestepDist * mXY / self.repository.extruderEarlyStopXY.value] , feed )
						Reversing = True
					else:
						#not reversing
						#print 'A'
						self.move_XY([Segment[X],Segment[Y],Segment[E]], feed)
					#endif
				else:
					#reversing
					self.move_XY([Segment[X], Segment[Y], self.extruderoozestepDist * MoveDist / self.repository.extruderEarlyStopXY.value], feed)
				#endif
			#endif MoveDist
		#endfor Segments

	def Edist( self , splitLine ):
		return splitLine[gcodec.getIndexOfStartingWithSecond('E', splitLine)][1:]
		
	def getTravelLine( self , splitLine ):
		outputLine = ''
	    #if x y and z present, split into 2 lines
		eString = getStringFromCharacterSplitLine('E', splitLine )
		xString = getStringFromCharacterSplitLine('X', splitLine )
		yString = getStringFromCharacterSplitLine('Y', splitLine )
		zString = getStringFromCharacterSplitLine('Z', splitLine )
		self.feed = getStringFromCharacterSplitLine('F', splitLine )
		if zString != None and zString != self.lastZString:
			#oldfeed = self.feed
			zoutputLine = 'Z' + myformat(float(zString)) + ' F' + str(myformat(float( self.repository.zFeed.value * 60 ),0))
			if self.repository.g_one.value:
				zoutputLine = "G1 " + zoutputLine
			#endif
			self.distanceFeedRate.addLine(zoutputLine)
			#self.feed = oldfeed
			self.currFeed = self.repository.zFeed.value * 60
			if float(zString) > float(self.lastZString):
				#print "layer %s" % self.currLayer
				self.currLayer += 1
				if self.currLayer >1:
					self.isNewLayer = True
				#endif
			#endif
			self.lastZString = zString
		if xString != None:
			outputLine += 'X' + myformat(float(xString)) + ' '
			self.currPos[X] = float(xString)
		if yString != None:
			outputLine += 'Y' + myformat(float(yString)) + ' '
			self.currPos[Y] = float(yString)
		if eString != None:
			outputLine += 'E' + myformat(float(eString)) + ' '
		if self.feed != None and self.feed != self.currFeed:
			if len(outputLine) > 0:
				#outputLine += 'F%s' % self.feed
				outputLine += 'F' + str(myformat(float(self.feed),0))
				self.currFeed = self.feed
			#endif
		if self.repository.g_one.value and outputLine != '':
			outputLine = "G1 " + outputLine
		#endif
		self.distanceFeedRate.addLine(outputLine)

	def move_E( self , dE ):
		move = ""

		if self.currFeed != self.xyFeed:
			eFeed = " F" + str(myformat(float(self.xyFeed),0))
		else:
			eFeed = ""
		    
		move += "E" + myformat(dE, 2) + eFeed + "\n"
		
		self.currFeed = self.xyFeed
		self.distanceFeedRate.addLine(move)
	#end move_E

	"""
	Function: move_XY(pos, moveE)
	Arguments: To position - pos[(x,y,e)]
	"""
	def move_XY( self , pos , feed):
		move = ""
		
		#print pos
		dX = (pos[X] - self.currPos[X])
		dY = (pos[Y] - self.currPos[Y])
		dE = pos[E]
		MoveDist = sqrt(dX**2 + dY**2 + dE**2)

		#no move so return nothing
		if MoveDist == 0:
		    return ''
		#endif

		i = dX / MoveDist if MoveDist != 0 else 0
		j = dY / MoveDist if MoveDist != 0 else 0
		k = dE / MoveDist if MoveDist != 0 else 0
		
		### only output initial feed if needed ###
		if self.currFeed != feed:
		    xyFeed = "F" + str(myformat(float(feed),0))
		    self.currFeed = feed
		else:
		    xyFeed = ""
		#endif    
		
		eX = "X" + myformat(pos[X]) + " " if dX != 0 else ""
		eY = "Y" + myformat(pos[Y]) + " " if dY != 0 else ""
		eE = "E" + myformat(dE, 3) + " " if dE and MoveDist else ""

		move += eX + eY + eE + xyFeed + "\n"

		if self.repository.g_one.value:
			move = "G1 " + move
		#endif

		self.currPos[X] = pos[X]
		self.currPos[Y] = pos[Y]
		self.distanceFeedRate.addLine(move)
	#end move_to_pos

def main():
	"Display the oozestep dialog."
	if len( sys.argv ) > 1:
		writeOutput( ' '.join( sys.argv[ 1 : ] ) )
	else:
		settings.startMainLoopFromConstructor( getRepositoryConstructor() )

if __name__ == "__main__":
	main()
