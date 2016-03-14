#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Create projects from a json description file
# for XCode, Visual Studio, CodeBlocks and
# other IDEs
#

# Copyright 1995-2016 by Rebecca Ann Heineman becky@burgerbecky.com

# It is released under an MIT Open Source license. Please see LICENSE
# for license details. Yes, you can use it in a
# commercial title without paying anything, just give me a credit.
# Please? It's not like I'm asking you for money!

import os
import json
import glob
import shutil
import sys
import platform
import uuid
import hashlib
import subprocess
import copy
import burger
import argparse
from enum import Enum
import visualstudio
import xcode

#
## \package makeprojects.core
# Core contains the master dispatchers to generate
# a project file for many popular IDEs
#

#
## Enumeration of supported file types for input
#

class FileTypes(Enum):
	## User file type (Unknown)
	user = 1
	## Non compiling file type
	generic = 2
	## Compile as C++ 
	cpp = 3
	## C/C++ header
	h = 4
	## Object-C
	m = 5
	## XML text file
	xml = 6
	## Windows resource file
	rc = 7
	## Mac OS resource file
	r = 8
	## HLSL DirectX Shader
	hlsl = 9
	## GLSL OpenGL Shader
	glsl = 10
	## Xbox 360 DirectX Shader
	x360sl = 11
	## Playstation Vita CG Shader
	vitacg = 12
	## Mac OSX Framework
	frameworks = 13
	## Library
	library = 14
	## Exe
	exe = 15
	## XCode config file
	xcconfig = 16
	## X86 assembly
	x86 = 17
	## 6502/65812 assembly
	a65 = 18
	## Image files
	image = 19
	## Windows icon files
	ico = 20
	## MacOSX icon files
	icns = 21
	
#
## List of default file extensions and mapped types
#
# When the directory is scanned for input files,
# the files will be tested against this list
# with a forced lowercase filename 
# and determine the type
# of compiler to assign to an input file
#
# This list can be appended or modified to allow
# other file types to be processed
#

defaultcodeextensions = [
	['.c',FileTypes.cpp],			# C/C++ source code
	['.cc',FileTypes.cpp],
	['.cpp',FileTypes.cpp],
	['.c++',FileTypes.cpp],
	['.hpp',FileTypes.h],			# C/C++ header files
	['.h',FileTypes.h],
	['.hh',FileTypes.h],
	['.i',FileTypes.h],
	['.inc',FileTypes.h],
	['.m',FileTypes.m],				# MacOSX / iOS Objective-C
	['.plist',FileTypes.xml],		# MacOSX / iOS plist files
	['.rc',FileTypes.rc],			# Windows resources
	['.r',FileTypes.r],				# MacOS classic resources
	['.rsrc',FileTypes.r],
	['.hlsl',FileTypes.hlsl],		# DirectX shader files
	['.vsh',FileTypes.glsl],		# OpenGL shader files
	['.fsh',FileTypes.glsl],
	['.glsl',FileTypes.glsl],
	['.x360sl',FileTypes.x360sl],	# Xbox 360 shader files
	['.vitacg',FileTypes.vitacg],	# PS Vita shader files
	['.xml',FileTypes.xml],			# XML data files
	['.a65',FileTypes.a65],			# 6502/65816 source code
	['.x86',FileTypes.x86],			# Intel ASM 80x86 source code
	['.ico',FileTypes.ico],			# Windows icon file
	['.icns',FileTypes.icns],		# Mac OSX Icon file
	['.png',FileTypes.image],		# Art files
	['.jpg',FileTypes.image],
	['.bmp',FileTypes.image]
]

#
## Save the default json file
#
# If the -default option is parsed from the command line, 
# this function is called to output a sample .json file
#
# \param solutionpathname Filename for the .json file to output
#

def savedefault(solutionpathname):
	fp = open(solutionpathname,'w')
	fp.write(
		'# Json file to create a project file\n' 
		'\n'
		'# Copyright 1995-2015 by Rebecca Ann Heineman becky@burgerbecky.com\n'
		'\n'
		'# It is released under an MIT Open Source license. Please see LICENSE\n'
		'# for license details. Yes, you can use it in a\n'
		'# commercial title without paying anything, just give me a credit.\n'
		'# Please? It\'s not like I\'m asking you for money!\n'
		'\n'
		'[\n'
		'\t// Initial settings\n'
		'\t{\n'
		'\t\t// Name of the project (And output filename)\n'
		'\t\t"projectname": "greatapp",\n'
		'\t\t// Kind of project (library,game,screensaver,tool)\n'
		'\t\t"kind": "tool",\n'
		'\t\t// Configurations to generate (Debug,Internal,Release,Profile)\n'
		'\t\t"configurations": ["Debug","Internal","Release"],\n'
		'\t\t// List of filenames to exclude from parsing\n'
		'\t\t"exclude": [],\n'
		'\t\t// List of additional defines\n'
		'\t\t"defines": [],\n'
		'\t\t// Folder to store the final binary that\'s checked into Perforce\n'
		'\t\t"finalfolder": "",\n'
		'\t\t// Operating system target to build for (windows,macosx,linux,ps3,ps4,xbox,\n'
		'\t\t// xbox360,xboxone,shield,ios,mac,msdos,beos,ouya,vita)\n'
		'\t\t"platform" : "windows",\n'
		'\t\t// Folders to scan for source code (Append with /*.* for recursive search)\n'
		'\t\t"sourcefolders": ["./*.*"],\n'
		'\t\t// Folders to add for include files (No file scanning is performed)\n'
		'\t\t"includefolders" : []\n'
		'\t},\n'
		'\t// Windows -> Visual Studio 2010\n'
		'\t// (xcode3,xcode4,xcode5,vs2003,vs2005,vs2008,vs2010,vs2012,vs2015,codeblocks,watcom,codewarrior)\n'
		'\t"vs2010"\n'
		']\n'
		)
	fp.close()

#
## Object for each input file to insert to a solution
#
# For every file that could be included into a project file
# one of these objects is created and attached to a solution object
# for processing
#

class SourceFile:

	#
	## Default constructor
	#
	# \param self The 'this' reference
	# \param filename Filename of the input file (relative to the root)
	# \param directory Pathname of the root directory
	# \param type Compiler to apply
	# \sa defaultcodeextensions
	#

	def __init__(self,filename,directory,type):
	
		## File base name with extension (Converted to use windows style slashes on creation)
		self.filename = burger.converttowindowsslashes(filename)

		## Directory the file is found in (Full path)
		self.directory = directory

		## File type enumeration, see: \ref FileTypes
		self.type = type
	
	#
	## Given a filename with a directory, extract the filename, leaving only the directory
	#
	# To determine if the file should be in a sub group in the project, scan
	# the filename to find if it's a base filename or part of a directory
	# If it's a basename, return an empty string.
	# If it's in a folder, remove any ..\\ prefixes and .\\ prefixes
	# and return the filename with the basename removed
	#
	# \param self The 'this' reference
	#

	def extractgroupname(self):
		index = self.filename.rfind('\\')
		if index==-1:
			return ''

		#
		# Remove the basename
		#
		
		newname = self.filename[0:index]
	
		#
		# If there are ..\\ at the beginning, remove them
		#
	
		while newname.startswith('..\\'):
			newname = newname[3:len(newname)]
	
		#
		# If there is a .\\, remove the single prefix
		#
	
		if newname.startswith('.\\'):
			newname = newname[2:len(newname)]

		return newname
		
		
		
	

#
## Object for processing a solution file
#
# This object contains all of the items needed to
# create a solution
#

class SolutionData:
	def __init__(self):
	
		## True if verbose output is requested (Default False)
		self.verbose = False

		## Root directory (Default None)
		self.workingDir = None
	
		## Type of project, tool is default ('tool', 'game', 'library')
		self.kind = 'tool'
	
		## Generic name for the project, 'project' is default
		self.projectname = 'project'
	
		## Type of ide
		# 'vs2015', 'vs2013', 'vs2012', 'vs2010', 'vs2008', 'vs2005',
		# 'xcode3', 'xcode4', 'xcode5', 'codewarrior', 'codeblocks',
		# 'watcom'
		self.ide = 'vs2010'
	
		## Generate a windows project as a default
		self.platform = 'windows'
	
		## Generate the three default configurations
		self.configurations = ['Debug','Internal','Release']
	
		## No special folder for the final binary
		self.finalfolder = None
	
		## Don't exclude any files
		self.exclude = []
	
		## No special #define for C/C++ code
		self.defines = []
	
		## Scan at the current folder
		self.sourcefolders = ['.']
	
		## No extra folders for include files
		self.includefolders = []
	
		## Initial array of SourceFile in the solution
		self.codefiles = []

		## Create default XCode object
		self.xcode = xcode.Defaults()
		
		## Create default Visual Studio object
		self.visualstudio = visualstudio.Defaults()

	#
	## Given a json record, process all the sub sections
	#
	# Given a dictionary created by a json file or
	# manually, update the solution to the new data
	#
	# \param self The 'this' reference	
	# \param myjson Dictionary with key value pairs
	#
	# Acceptable keys
	# \li 'finalfolder' = pathname to store final release binary
	# \li 'kind' = 'tool', 'library', 'game'
	# \li 'projectname' = Name of the project's filename (basename only)
	# \li 'platform' = 'windows', 'macosx', 'linux', 'ps3', 'ps4', 'vita',
	# 'xbox', 'xbox360', 'xboxone', 'shield', 'ios', 'mac', 'msdos',
	# 'beos', 'ouya', 'wiiu'
	# \li 'configurations' = ['Debug', 'Release', 'Internal']
	# \li 'sourcefolders' = ['.','source']
	# \li 'exclude' = [] (List of files to exclude from processing)
	# \li 'defines' = [] (List of #define to add to the project)
	# \li 'includefolders' = [] (List of folders to add for #include )
	# \li 'xcode' = dir() (Keys and values for special cases for xcode projects)
	# \li 'visualstudio' = dir() (Keys and values for special cases for visual studio projects)
	#
	# \sa makeprojects.xcode or makeprojects.visualstudio
	#

	def processjson(self,myjson):
		error = 0
		for key in myjson.keys():
			if key=='finalfolder':
				if myjson[key]=="":
					self.finalfolder = None
				else:
					self.finalfolder = myjson[key]
					
			elif key=='kind':
				self.kind = myjson[key]
			elif key=='projectname':
				self.projectname = myjson[key]
			elif key=='platform':
				self.platform = myjson[key]
				
			elif key=='configurations':
				self.configurations = burger.converttoarray(myjson[key])
			elif key=='sourcefolders':
				self.sourcefolders = burger.converttoarray(myjson[key])
			elif key=='exclude':
				self.exclude = burger.converttoarray(myjson[key])
			elif key=='defines':
				self.defines = burger.converttoarray(myjson[key])
			elif key=='includefolders':
				self.includefolders = burger.converttoarray(myjson[key])

			#
			# Handle IDE specific data
			#
			
			elif key=='xcode':
				error = self.xcode.loadjson(myjson[key])
			elif key=='visualstudio':
				error = self.visualstudio.loadjson(myjson[key])
			else:
				print 'Unknown keyword "' + str(key) + '" with data "' + str(myjson[key]) + '" found in json file'
				error = 1
				
			if error!=0:
				break

		return error
	

	#
	# The script is an array of objects containing solution settings
	# and a list of IDEs to output scripts
	#

	def process(self,myjson):
		error = 0
		for item in myjson:
			if type(item) is dict:
				error = self.processjson(item)
			elif item=='vs2015':
				self.ide = item
				error = visualstudio.generate(self)
			elif item=='vs2013':
				self.ide = item
				error = visualstudio.generate(self)
			elif item=='vs2012':
				self.ide = item
				error = visualstudio.generate(self)
			elif item=='vs2010':
				self.ide = item
				error = visualstudio.generate(self)
			elif item=='vs2008':
				self.ide = item
				error = createvs2008solution(self)
			elif item=='vs2005':
				self.ide = item
				error = createvs2005solution(self)
			elif item=='xcode3':
				self.ide = item
				error = xcode.generate(self)
			elif item=='xcode4':
				self.ide = item
				error = xcode.generate(self)
			elif item=='xcode5':
				self.ide = item
				error = xcode.generate(self)
			elif item=='codewarrior':
				self.ide = item
				error = createcodewarriorsolution(self)
			elif item=='codeblocks':
				self.ide = item
				error = createcodeblockssolution(self)
			elif item=='watcom':
				self.ide = item
				error = createwatcomsolution(self)
			else:
				print 'Saving ' + item + ' not implemented yet'
				error = 0
			if error!=0:
				break
		return error

	#
	# Handle the command line case
	# by creating a phony json file and passing it
	# in for processing
	#

	def processcommandline(self,args):

		#
		# Fake json file and initialization record
		#
			
		dictrecord = dict()
		
		#
		# Use the work folder name as the project name
		#
		
		dictrecord['projectname'] = os.path.basename(self.workingDir)
		
		configurations = []
		if args.debug==True:
			configurations.append('Debug')
		if args.internal==True:
			configurations.append('Internal')
		if args.release==True:
			configurations.append('Release')
		if len(configurations)==0:
			configurations = ['Debug','Internal','Release']

		#
		# Only allow finalfolder when release builds are made
		#
		
		if not 'Release' in configurations:
			args.finalfolder==False

		dictrecord['configurations'] = configurations

		#
		# Lib, game or tool?
		#
		
		if args.app==True:
			kind = 'game'
		elif args.library==True:
			kind = 'library'
		else:
			kind = 'tool'
		dictrecord['kind'] = kind

		#
		# Where to find the source
		#
		
		dictrecord['sourcefolders'] = ['.','source/*.*']
		
		#
		# Save the initializer in a fake json record
		# list
		#

		myjson = [dictrecord]
		
		#
		# Xcode projects assume a macosx platform
		# unless directed otherwise
		#
		
		if args.xcode3==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'macosx'
			if args.finalfolder==True:
				initializationrecord['finalfolder'] = xcode.defaultfinalfolder
			myjson.append(initializationrecord)
			myjson.append('xcode3')

		if args.xcode4==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'macosx'
			if args.finalfolder==True:
				initializationrecord['finalfolder'] = xcode.defaultfinalfolder
			myjson.append(initializationrecord)
			myjson.append('xcode4')
			
		if args.xcode5==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'macosx'
			if args.finalfolder==True:
				initializationrecord['finalfolder'] = xcode.defaultfinalfolder
			myjson.append(initializationrecord)
			myjson.append('xcode5')

		#
		# These are windows only
		#
				
		if args.vs2005==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'windows'
			myjson.append(initializationrecord)
			myjson.append('vs2005')

		if args.vs2008==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'windows'
			myjson.append(initializationrecord)
			myjson.append('vs2008')

		if args.vs2010==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'windows'
			if args.finalfolder==True:
				initializationrecord['finalfolder'] = visualstudio.defaultfinalfolder
			myjson.append(initializationrecord)
			myjson.append('vs2010')

		if args.vs2015==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'windows'
			if args.finalfolder==True:
				initializationrecord['finalfolder'] = visualstudio.defaultfinalfolder
			myjson.append(initializationrecord)
			myjson.append('vs2015')

		if args.codeblocks==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'windows'
			myjson.append(initializationrecord)
			myjson.append('codeblocks')

		if args.codewarrior==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'windows'
			myjson.append(initializationrecord)
			myjson.append('codewarrior')

		if args.watcom==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'windows'
			myjson.append(initializationrecord)
			myjson.append('watcom')

		#
		# These are platform specific, and as such are
		# tied to specific IDEs that are tailored to
		# the specific platforms
		#
		
		if args.xbox360==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'xbox360'
			myjson.append(initializationrecord)
			myjson.append('vs2010')

		if args.ios==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'ios'
			myjson.append(initializationrecord)
			myjson.append('xcode5')

		if args.vita==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'vita'
			myjson.append(initializationrecord)
			myjson.append('vs2010')

		if args.wiiu==True:
			initializationrecord = dict()
			initializationrecord['platform'] = 'wiiu'
			myjson.append(initializationrecord)
			myjson.append('vs2013')

		if len(myjson)<2:
			print 'No default "projects.json" file found nor any project type specified'
			return 2 
	
		return self.process(myjson)
		
#
# Create the ide code from the ide type
#

	def getidecode(self):
		if self.ide=='xcode3':
			return 'xc3'
		if self.ide=='xcode4':
			return 'xc4'
		if self.ide=='xcode5':
			return 'xc5'
		if self.ide=='vs2003':
			return 'vc7'
		if self.ide=='vs2005':
			return 'vc8'
		if self.ide=='vs2008':
			return 'vc9'
		if self.ide=='vs2010':
			return 'v10'
		if self.ide=='vs2012':
			return 'v11'
		if self.ide=='vs2013':
			return 'v13'
		if self.ide=='vs2015':
			return 'v14'
		if self.ide=='codeblocks':
			return 'cdb'
		if self.ide=='watcom':
			return 'wat'
		if self.ide=='codewarrior' and self.platform=='windows':
			return 'cw9'
		if self.ide=='codewarrior' and self.platform=='mac':
			return 'c10'
		return None

#
# Create the platform code from the platform type
#

	def getplatformcode(self):
		if self.platform=='windows':
			return 'win'
		if self.platform=='macosx':
			return 'osx'
		if self.platform=='linux':
			return 'lnx'
		if self.platform=='ps3':
			return 'ps3'
		if self.platform=='ps4':
			return 'ps4'
		if self.platform=='vita':
			return 'vit'
		if self.platform=='xbox':
			return 'xbx'
		if self.platform=='xbox360':
			return 'x36'
		if self.platform=='xboxone':
			return 'one'
		if self.platform=='shield':
			return 'shi'
		if self.platform=='ios':
			return 'ios'
		if self.platform=='mac':
			return 'mac'
		if self.platform=='msdos':
			return 'dos'
		if self.platform=='beos':
			return 'bos'
		if self.platform=='ouya':
			return 'oya'
		if self.platform=='wiiu':
			return 'wiu'
		return None

#
# Create the platform codes from the platform type for Visual Studio
#

	def getvsplatform(self):
		if self.platform=='windows':
			return ['Win32','x64']
		if self.platform=='ps3':
			return ['PS3']
		if self.platform=='ps4':
			return ['ORBIS']
		if self.platform=='vita':
			return ['PSVita']
		if self.platform=='xbox':
			return ['Xbox']
		if self.platform=='xbox360':
			return ['Xbox 360']
		if self.platform=='xboxone':
			return ['Xbox ONE']
		if self.platform=='shield':
			return ['Tegra-Android']
		if self.platform=='android':
			return ['Android']
		if self.platform=='wiiu':
			return ['Cafe']
		return []
	
	
#
# Given a base directory and a relative directory
# scan for all the files that are to be included in the project
#

	def scandirectory(self,directory,codefiles,includedirectories,recurse,acceptable):

		#
		# Root directory is a special case
		#
		
		if directory=='.':
			searchDir = self.workingDir
		else:
			searchDir = os.path.join(self.workingDir,directory)

		#
		# Is this a valid directory?
		#
		if os.path.isdir(searchDir):

			#
			# Scan the directory
			#

			nameList = os.listdir(searchDir)
	
			#
			# No files added, yet (Flag for adding directory to the search tree)
			#
	
			found = False
		
			for baseName in nameList:

				#
				# Is this file in the exclusion list?
				#

				testName = baseName.lower()
				skip = False
				for item in self.exclude:
					if testName==item.lower():
						skip = True
						break

				if skip==True:
					continue

				#
				# Is it a file? (Skip links and folders)
				#
			
				fileName = os.path.join(searchDir,baseName)
				if os.path.isfile(fileName):
				
					#
					# Check against the extension list (Skip if not on the list)
					#
				
					for item in defaultcodeextensions:
						if testName.endswith(item[0]):
							
							#
							# Found a match, test if the type is in 
							# the acceptable list
							#
							
							abort = True
							for item2 in acceptable:
								if item[1]==item2:
									abort = False
									break
									
							if abort==True:
								break
									
							#
							# If the directory is the root, then don't prepend a directory
							#
							if directory=='.':
								newfilename = baseName
							else:
								newfilename = directory + os.sep + baseName
						
							#
							# Create a new entry (Using windows style slashes for consistency)
							#
							
							fileentry = SourceFile(newfilename,searchDir,item[1])
							codefiles.append(fileentry)
							if found==False:
								found = True
								includedirectories.append(directory)
							break
			
				#			
				# Process folders only if in recursion mode
				#
			
				elif recurse==True:
					if os.path.isdir(fileName):
						codefiles,includedirectories = self.scandirectory(directory + os.sep + baseName,codefiles,includedirectories,recurse,acceptable)
						
		return codefiles,includedirectories

#
# Obtain the list of source files
#

	def getfilelist(self,acceptable):

		#
		# Get the files that were manually parsed by the json
		# record
		#
	
		codefiles = list(self.codefiles)
		includedirectories = []
		for item in self.sourcefolders:
		
			#
			# Is it a recursive test?
			#
		
			recurse = False
			if item.endswith('/*.*'):
				# Remove the trailing /*.*
				item = item[0:len(item)-4]
				recurse = True
			
			#
			# Scan the folder for files
			#
			
			codefiles,includedirectories = self.scandirectory(item,codefiles,includedirectories,recurse,acceptable)

		#
		# Since the slashes are all windows (No matter what
		# host this script is running on, the sort will yield consistent
		# results so it doesn't matter what platform generated the 
		# file list, it's the same output.
		#
		
		codefiles = sorted(codefiles,cmp=lambda x,y: cmp(x.filename,y.filename))
		return codefiles,includedirectories

#
# Create the platform codes from the platform type for Visual Studio
#

def getconfigurationcode(configuration):
	if configuration=='Debug':
		return 'dbg'
	if configuration=='Release':
		return 'rel'
	if configuration=='Internal':
		return 'int'
	if configuration=='Profile':
		return 'pro'
	# The fallback is the configuration in lower case
	return configuration.lower()

#
# Prune the file list for a specific type
#

def pickfromfilelist(codefiles,itemtype):
	filelist = []
	for item in codefiles:
		if item.type == itemtype:
			filelist.append(item)
	return filelist
	
###################################
#                                 #
# Visual Studio 2003-2013 support #
#                                 #
###################################
	
#
# Dump out a recursive tree of files to reconstruct a
# directory hiearchy for a file list
#
# Used by Visual Studio 2003, 2005 and 2008
#

def dumptreevs2005(indent,string,entry,fp,groups):
	for item in entry:
		if item!='':
			fp.write('\t'*indent + '<Filter Name="' + item + '">\n')
		if string=='':
			merged = item
		else:
			merged = string + '\\' + item
		if merged in groups:
			if item!='':
				tabs = '\t'*(indent+1)
			else:
				tabs = '\t'*indent
			sortlist = sorted(groups[merged],cmp=lambda x,y: cmp(x,y))
			for file in sortlist:
				fp.write(tabs + '<File RelativePath="' + file + '" />\n')					
		key = entry[item]
		# Recurse down the tree
		if type(key) is dict:
			dumptreevs2005(indent+1,merged,key,fp,groups)
		if item!='':
			fp.write('\t'*indent + '</Filter>\n')
	
#
# Create the solution and project file for visual studio 2005
#

def createvs2005solution(solution):
	error = visualstudio.generate(solution)
	if error!=0:
		return error
		
	#
	# Now, let's create the project file
	#
	
	acceptable = [FileTypes.h,FileTypes.cpp,FileTypes.rc,FileTypes.ico]
	codefiles,includedirectories = solution.getfilelist(acceptable)
	listh = pickfromfilelist(codefiles,FileTypes.h)
	listcpp = pickfromfilelist(codefiles,FileTypes.cpp)
	listwindowsresource = pickfromfilelist(codefiles,FileTypes.rc)

	platformcode = solution.getplatformcode()
	solutionuuid = str(uuid.uuid3(uuid.NAMESPACE_DNS,str(solution.visualstudio.projectfilename))).upper()
	projectpathname = os.path.join(solution.workingDir,solution.visualstudio.projectfilename + '.vcproj')
	burger.perforceedit(projectpathname)
	fp = open(projectpathname,'w')
	
	#
	# Save off the xml header
	#
	
	fp.write('<?xml version="1.0" encoding="utf-8"?>\n')
	fp.write('<VisualStudioProject\n')
	fp.write('\tProjectType="Visual C++"\n')
	fp.write('\tVersion="8.00"\n')
	fp.write('\tName="' + solution.projectname + '"\n')
	fp.write('\tProjectGUID="{' + solutionuuid + '}"\n')
	fp.write('\t>\n')

	#
	# Write the project platforms
	#

	fp.write('\t<Platforms>\n')
	for vsplatform in solution.getvsplatform():
		fp.write('\t\t<Platform Name="' + vsplatform + '" />\n')
	fp.write('\t</Platforms>\n')

	#
	# Write the project configurations
	#
	
	fp.write('\t<Configurations>\n')
	for target in solution.configurations:
		for vsplatform in solution.getvsplatform():
			token = target + '|' + vsplatform
			fp.write('\t\t<Configuration\n')
			fp.write('\t\t\tName="' + token + '"\n')
			fp.write('\t\t\tOutputDirectory="bin\\"\n')
			if vsplatform=='x64':
				platformcode2 = 'w64'
			elif vsplatform=='Win32':
				platformcode2 = 'w32'
			else:
				platformcode2 = platformcode
			intdirectory = solution.projectname + solution.getidecode() + platformcode2 + getconfigurationcode(target)
			fp.write('\t\t\tIntermediateDirectory="temp\\' + intdirectory + '"\n')
			if solution.kind=='library':
				# Library
				fp.write('\t\t\tConfigurationType="4"\n')
			else:
				# Application
				fp.write('\t\t\tConfigurationType="1"\n')
			fp.write('\t\t\tUseOfMFC="0"\n')
			fp.write('\t\t\tATLMinimizesCRunTimeLibraryUsage="false"\n')
			# Unicode
			fp.write('\t\t\tCharacterSet="1"\n')
			fp.write('\t\t\t>\n')

			fp.write('\t\t\t<Tool\n')
			fp.write('\t\t\t\tName="VCCLCompilerTool"\n')
			fp.write('\t\t\t\tPreprocessorDefinitions="')
			if target=='Release':
				fp.write('NDEBUG')
			else:
				fp.write('_DEBUG')
			if vsplatform=='x64':
				fp.write(';WIN64;_WINDOWS')
			elif vsplatform=='Win32':
				fp.write(';WIN32;_WINDOWS')
			for item in solution.defines:
				fp.write(';' + item)
			fp.write('"\n')

			fp.write('\t\t\t\tStringPooling="true"\n')
			fp.write('\t\t\t\tExceptionHandling="0"\n')
			fp.write('\t\t\t\tStructMemberAlignment="4"\n')
			fp.write('\t\t\t\tEnableFunctionLevelLinking="true"\n')
			fp.write('\t\t\t\tFloatingPointModel="2"\n')
			fp.write('\t\t\t\tRuntimeTypeInfo="false"\n')
			fp.write('\t\t\t\tPrecompiledHeaderFile=""\n')
			# 8 byte alignment
			fp.write('\t\t\t\tWarningLevel="4"\n')
			fp.write('\t\t\t\tSuppressStartupBanner="true"\n')
			if solution.kind=='library' or target!='Release':
				fp.write('\t\t\t\tDebugInformationFormat="3"\n')
				fp.write('\t\t\t\tProgramDataBaseFileName="$(OutDir)\$(TargetName).pdb"\n')
			else:
				fp.write('\t\t\t\tDebugInformationFormat="0"\n')
			
			fp.write('\t\t\t\tCallingConvention="1"\n')
			fp.write('\t\t\t\tCompileAs="2"\n')
			fp.write('\t\t\t\tFavorSizeOrSpeed="1"\n')
			# Disable annoying nameless struct warnings since windows headers trigger this
			fp.write('\t\t\t\tDisableSpecificWarnings="4201"\n')

			if target=='Debug':
				fp.write('\t\t\t\tOptimization="0"\n')
			else:
				fp.write('\t\t\t\tOptimization="2"\n')
				fp.write('\t\t\t\tInlineFunctionExpansion="2"\n')
				fp.write('\t\t\t\tEnableIntrinsicFunctions="true"\n')
				fp.write('\t\t\t\tOmitFramePointers="true"\n')
			if target=='Release':
				fp.write('\t\t\t\tBufferSecurityCheck="false"\n')
				fp.write('\t\t\t\tRuntimeLibrary="0"\n')
			else:
				fp.write('\t\t\t\tBufferSecurityCheck="true"\n')
				fp.write('\t\t\t\tRuntimeLibrary="1"\n')
				
			#
			# Include directories
			#
			fp.write('\t\t\t\tAdditionalIncludeDirectories="')
			addcolon = False
			included = includedirectories + solution.includefolders
			if len(included):
				for dir in included:
					if addcolon==True:
						fp.write(';')
					fp.write(burger.converttowindowsslashes(dir))
					addcolon = True
			if platformcode=='win':
				if addcolon==True:
					fp.write(';')
				if solution.kind!='library' or solution.projectname!='burgerlib':
					fp.write('$(BURGER_SDKS)\\windows\\burgerlib;')
				fp.write('$(BURGER_SDKS)\\windows\\directx9;$(BURGER_SDKS)\\windows\\opengl')
				addcolon = True
			fp.write('"\n')
			fp.write('\t\t\t/>\n')
			
			fp.write('\t\t\t<Tool\n')
			fp.write('\t\t\t\tName="VCResourceCompilerTool"\n')
			fp.write('\t\t\t\tCulture="1033"\n')
			fp.write('\t\t\t/>\n')
			
			if solution.kind=='library':
				fp.write('\t\t\t<Tool\n')
				fp.write('\t\t\t\tName="VCLibrarianTool"\n')
				fp.write('\t\t\t\tOutputFile="&quot;$(OutDir)' + intdirectory + '.lib&quot;"\n')
				fp.write('\t\t\t\tSuppressStartupBanner="true"\n')
				fp.write('\t\t\t/>\n')
				if solution.finalfolder!=None:
					finalfolder = burger.converttowindowsslasheswithendslash(solution.finalfolder)
					fp.write('\t\t\t<Tool\n')
					fp.write('\t\t\t\tName="VCPostBuildEventTool"\n')
					fp.write('\t\t\t\tDescription="Copying $(TargetName)$(TargetExt) to ' + finalfolder + '"\n')
					fp.write('\t\t\t\tCommandLine="&quot;$(perforce)\p4&quot; edit &quot;' + finalfolder + '$(TargetName)$(TargetExt)&quot;&#x0D;&#x0A;')
					fp.write('&quot;$(perforce)\p4&quot; edit &quot;' + finalfolder + '$(TargetName).pdb&quot;&#x0D;&#x0A;')
					fp.write('copy /Y &quot;$(OutDir)$(TargetName)$(TargetExt)&quot; &quot;' + finalfolder + '$(TargetName)$(TargetExt)&quot;&#x0D;&#x0A;')
					fp.write('copy /Y &quot;$(OutDir)$(TargetName).pdb&quot; &quot;' + finalfolder + '$(TargetName).pdb&quot;&#x0D;&#x0A;')
					fp.write('&quot;$(perforce)\p4&quot; revert -a &quot;' + finalfolder + '$(TargetName)$(TargetExt)&quot;&#x0D;&#x0A;')
					fp.write('&quot;$(perforce)\p4&quot; revert -a &quot;' + finalfolder + '$(TargetName).pdb&quot;&#x0D;&#x0A;"\n')
					fp.write('\t\t\t/>\n')
			else:
				fp.write('\t\t\t<Tool\n')
				fp.write('\t\t\t\tName="VCLinkerTool"\n')
				fp.write('\t\t\t\tAdditionalDependencies="burgerlib' + solution.getidecode() + platformcode2 + getconfigurationcode(target) + '.lib"\n')
				fp.write('\t\t\t\tOutputFile="&quot;$(OutDir)' + intdirectory + '.exe&quot;"\n')
				fp.write('\t\t\t\tAdditionalLibraryDirectories="')
				addcolon = False
				for item in solution.includefolders:
					if addcolon==True:
						fp.write(';')
					fp.write(burger.converttowindowsslashes(item))
					addcolon = True
					
				if addcolon==True:
					fp.write(';')
				if solution.kind!='library':
					fp.write('$(BURGER_SDKS)\\windows\\burgerlib;')
				fp.write('$(BURGER_SDKS)\\windows\\opengl"\n')
				if solution.kind=='tool':
					# main()
					fp.write('\t\t\t\tSubSystem="1"\n')
				else:
					# WinMain()
					fp.write('\t\t\t\tSubSystem="2"\n')
				fp.write('\t\t\t/>\n')
			fp.write('\t\t</Configuration>\n')

	fp.write('\t</Configurations>\n')	
		
	#
	# Save out the filenames
	#
	
	alllists = listh + listcpp + listwindowsresource
	if len(alllists):

		#	
		# Create groups first since Visual Studio uses a nested tree structure
		# for file groupings
		#
		
		groups = dict()
		for item in alllists:
			groupname = item.extractgroupname()
			# Put each filename in its proper group
			if groupname in groups:
				groups[groupname].append(burger.converttowindowsslashes(item.filename))
			else:
				# New group!
				groups[groupname] = [burger.converttowindowsslashes(item.filename)]
		
		#
		# Create a recursive tree in order to store out the file list
		#

		fp.write('\t<Files>\n')
		tree = dict()
		for group in groups:
			#
			# Get the depth of the tree needed
			#
			
			parts = group.split('\\')
			next = tree
			#
			# Iterate over every part
			#
			for x in xrange(len(parts)):
				# Already declared?
				if not parts[x] in next:
					next[parts[x]] = dict()
				# Step into the tree
				next = next[parts[x]]

		# Use this tree to play back all the data
		dumptreevs2005(2,'',tree,fp,groups)
		fp.write('\t</Files>\n')
		
	fp.write('</VisualStudioProject>\n')
	fp.close()

	return 0

			
#
# Create the solution and project file for visual studio 2008
#

def createvs2008solution(solution):
	error = visualstudio.generate(solution)
	if error!=0:
		return error
	#
	# Now, let's create the project file
	#
	
	acceptable = [FileTypes.h,FileTypes.cpp,FileTypes.rc,FileTypes.ico]
	codefiles,includedirectories = solution.getfilelist(acceptable)
	listh = pickfromfilelist(codefiles,FileTypes.h)
	listcpp = pickfromfilelist(codefiles,FileTypes.cpp)
	listwindowsresource = pickfromfilelist(codefiles,FileTypes.rc)

	platformcode = solution.getplatformcode()
	solutionuuid = str(uuid.uuid3(uuid.NAMESPACE_DNS,str(solution.visualstudio.projectfilename))).upper()
	projectpathname = os.path.join(solution.workingDir,solution.visualstudio.projectfilename + '.vcproj')
	burger.perforceedit(projectpathname)
	fp = open(projectpathname,'w')
	
	#
	# Save off the xml header
	#
	
	fp.write('<?xml version="1.0" encoding="utf-8"?>\n')
	fp.write('<VisualStudioProject\n')
	fp.write('\tProjectType="Visual C++"\n')
	fp.write('\tVersion="9.00"\n')
	fp.write('\tName="' + solution.projectname + '"\n')
	fp.write('\tProjectGUID="{' + solutionuuid + '}"\n')
	fp.write('\t>\n')

	#
	# Write the project platforms
	#

	fp.write('\t<Platforms>\n')
	for vsplatform in solution.getvsplatform():
		fp.write('\t\t<Platform Name="' + vsplatform + '" />\n')
	fp.write('\t</Platforms>\n')

	#
	# Write the project configurations
	#
	
	fp.write('\t<Configurations>\n')
	for target in solution.configurations:
		for vsplatform in solution.getvsplatform():
			token = target + '|' + vsplatform
			fp.write('\t\t<Configuration\n')
			fp.write('\t\t\tName="' + token + '"\n')
			fp.write('\t\t\tOutputDirectory="bin\\"\n')
			if vsplatform=='x64':
				platformcode2 = 'w64'
			elif vsplatform=='Win32':
				platformcode2 = 'w32'
			else:
				platformcode2 = platformcode
			intdirectory = solution.projectname + solution.getidecode() + platformcode2 + getconfigurationcode(target)
			fp.write('\t\t\tIntermediateDirectory="temp\\' + intdirectory + '\\"\n')
			if solution.kind=='library':
				# Library
				fp.write('\t\t\tConfigurationType="4"\n')
			else:
				# Application
				fp.write('\t\t\tConfigurationType="1"\n')
			fp.write('\t\t\tUseOfMFC="0"\n')
			fp.write('\t\t\tATLMinimizesCRunTimeLibraryUsage="false"\n')
			# Unicode
			fp.write('\t\t\tCharacterSet="1"\n')
			fp.write('\t\t\t>\n')

			fp.write('\t\t\t<Tool\n')
			fp.write('\t\t\t\tName="VCCLCompilerTool"\n')
			fp.write('\t\t\t\tPreprocessorDefinitions="')
			if target=='Release':
				fp.write('NDEBUG')
			else:
				fp.write('_DEBUG')
			if vsplatform=='x64':
				fp.write(';WIN64;_WINDOWS')
			elif vsplatform=='Win32':
				fp.write(';WIN32;_WINDOWS')
			for item in solution.defines:
				fp.write(';' + item)
			fp.write('"\n')

			fp.write('\t\t\t\tStringPooling="true"\n')
			fp.write('\t\t\t\tExceptionHandling="0"\n')
			fp.write('\t\t\t\tStructMemberAlignment="4"\n')
			fp.write('\t\t\t\tEnableFunctionLevelLinking="true"\n')
			fp.write('\t\t\t\tFloatingPointModel="2"\n')
			fp.write('\t\t\t\tRuntimeTypeInfo="false"\n')
			fp.write('\t\t\t\tPrecompiledHeaderFile=""\n')
			# 8 byte alignment
			fp.write('\t\t\t\tWarningLevel="4"\n')
			fp.write('\t\t\t\tSuppressStartupBanner="true"\n')
			if solution.kind=='library' or target!='Release':
				fp.write('\t\t\t\tDebugInformationFormat="3"\n')
				fp.write('\t\t\t\tProgramDataBaseFileName="$(OutDir)\$(TargetName).pdb"\n')
			else:
				fp.write('\t\t\t\tDebugInformationFormat="0"\n')
			
			fp.write('\t\t\t\tCallingConvention="1"\n')
			fp.write('\t\t\t\tCompileAs="2"\n')
			fp.write('\t\t\t\tFavorSizeOrSpeed="1"\n')
			# Disable annoying nameless struct warnings since windows headers trigger this
			fp.write('\t\t\t\tDisableSpecificWarnings="4201"\n')

			if target=='Debug':
				fp.write('\t\t\t\tOptimization="0"\n')
				# Necessary to quiet Visual Studio 2008 warnings
				fp.write('\t\t\t\tEnableIntrinsicFunctions="true"\n')
			else:
				fp.write('\t\t\t\tOptimization="2"\n')
				fp.write('\t\t\t\tInlineFunctionExpansion="2"\n')
				fp.write('\t\t\t\tEnableIntrinsicFunctions="true"\n')
				fp.write('\t\t\t\tOmitFramePointers="true"\n')
			if target=='Release':
				fp.write('\t\t\t\tBufferSecurityCheck="false"\n')
				fp.write('\t\t\t\tRuntimeLibrary="0"\n')
			else:
				fp.write('\t\t\t\tBufferSecurityCheck="true"\n')
				fp.write('\t\t\t\tRuntimeLibrary="1"\n')
				
			#
			# Include directories
			#
			fp.write('\t\t\t\tAdditionalIncludeDirectories="')
			addcolon = False
			included = includedirectories + solution.includefolders
			if len(included):
				for dir in included:
					if addcolon==True:
						fp.write(';')
					fp.write(burger.converttowindowsslashes(dir))
					addcolon = True
			if platformcode=='win':
				if addcolon==True:
					fp.write(';')
				if solution.kind!='library' or solution.projectname!='burgerlib':
					fp.write('$(BURGER_SDKS)\\windows\\burgerlib;')
				fp.write('$(BURGER_SDKS)\\windows\\directx9;$(BURGER_SDKS)\\windows\\opengl')
				addcolon = True
			fp.write('"\n')
			fp.write('\t\t\t/>\n')
			
			fp.write('\t\t\t<Tool\n')
			fp.write('\t\t\t\tName="VCResourceCompilerTool"\n')
			fp.write('\t\t\t\tCulture="1033"\n')
			fp.write('\t\t\t/>\n')
			
			if solution.kind=='library':
				fp.write('\t\t\t<Tool\n')
				fp.write('\t\t\t\tName="VCLibrarianTool"\n')
				fp.write('\t\t\t\tOutputFile="&quot;$(OutDir)' + intdirectory + '.lib&quot;"\n')
				fp.write('\t\t\t\tSuppressStartupBanner="true"\n')
				fp.write('\t\t\t/>\n')
				if solution.finalfolder!=None:
					finalfolder = burger.converttowindowsslasheswithendslash(solution.finalfolder)
					fp.write('\t\t\t<Tool\n')
					fp.write('\t\t\t\tName="VCPostBuildEventTool"\n')
					fp.write('\t\t\t\tDescription="Copying $(TargetName)$(TargetExt) to ' + finalfolder + '"\n')
					fp.write('\t\t\t\tCommandLine="&quot;$(perforce)\p4&quot; edit &quot;' + finalfolder + '$(TargetName)$(TargetExt)&quot;&#x0D;&#x0A;')
					fp.write('&quot;$(perforce)\p4&quot; edit &quot;' + finalfolder + '$(TargetName).pdb&quot;&#x0D;&#x0A;')
					fp.write('copy /Y &quot;$(OutDir)$(TargetName)$(TargetExt)&quot; &quot;' + finalfolder + '$(TargetName)$(TargetExt)&quot;&#x0D;&#x0A;')
					fp.write('copy /Y &quot;$(OutDir)$(TargetName).pdb&quot; &quot;' + finalfolder + '$(TargetName).pdb&quot;&#x0D;&#x0A;')
					fp.write('&quot;$(perforce)\p4&quot; revert -a &quot;' + finalfolder + '$(TargetName)$(TargetExt)&quot;&#x0D;&#x0A;')
					fp.write('&quot;$(perforce)\p4&quot; revert -a &quot;' + finalfolder + '$(TargetName).pdb&quot;&#x0D;&#x0A;"\n')
					fp.write('\t\t\t/>\n')
			else:
				fp.write('\t\t\t<Tool\n')
				fp.write('\t\t\t\tName="VCLinkerTool"\n')
				fp.write('\t\t\t\tAdditionalDependencies="burgerlib' + solution.getidecode() + platformcode2 + getconfigurationcode(target) + '.lib"\n')
				fp.write('\t\t\t\tOutputFile="&quot;$(OutDir)' + intdirectory + '.exe&quot;"\n')
				fp.write('\t\t\t\tAdditionalLibraryDirectories="')
				addcolon = False
				for item in solution.includefolders:
					if addcolon==True:
						fp.write(';')
					fp.write(burger.converttowindowsslashes(item))
					addcolon = True
					
				if addcolon==True:
					fp.write(';')
				if solution.kind!='library':
					fp.write('$(BURGER_SDKS)\\windows\\burgerlib;')
				fp.write('$(BURGER_SDKS)\\windows\\opengl"\n')
				if solution.kind=='tool':
					# main()
					fp.write('\t\t\t\tSubSystem="1"\n')
				else:
					# WinMain()
					fp.write('\t\t\t\tSubSystem="2"\n')
				fp.write('\t\t\t/>\n')
			fp.write('\t\t</Configuration>\n')

	fp.write('\t</Configurations>\n')	
		
	#
	# Save out the filenames
	#

	alllists = listh + listcpp + listwindowsresource
	if len(alllists):

		#	
		# Create groups first
		#
		
		groups = dict()
		for item in alllists:
			groupname = item.extractgroupname()
			# Put each filename in its proper group
			if groupname in groups:
				groups[groupname].append(burger.converttowindowsslashes(item.filename))
			else:
				# New group!
				groups[groupname] = [burger.converttowindowsslashes(item.filename)]
		
		#
		# Create a recursive tree in order to store out the file list
		#

		fp.write('\t<Files>\n')
		tree = dict()
		for group in groups:
			#
			# Get the depth of the tree needed
			#
			
			parts = group.split('\\')
			next = tree
			#
			# Iterate over every part
			#
			for x in xrange(len(parts)):
				# Already declared?
				if not parts[x] in next:
					next[parts[x]] = dict()
				# Step into the tree
				next = next[parts[x]]

		# Use this tree to play back all the data
		dumptreevs2005(2,'',tree,fp,groups)
		fp.write('\t</Files>\n')
		
	fp.write('</VisualStudioProject>\n')
	fp.close()
		
	return 0

#
# Dump out a recursive tree of files to reconstruct a
# directory hiearchy for codewarrior
#

def dumptreecodewarrior(indent,string,entry,fp,groups,solconfig):
	for item in entry:
		if item!='':
			fp.write('\t'*indent + '<GROUP><NAME>' + item + '</NAME>\n')
		if string=='':
			merged = item
		else:
			merged = string + '\\' + item
		if merged in groups:
			if item!='':
				tabs = '\t'*(indent+1)
			else:
				tabs = '\t'*indent
			sortlist = sorted(groups[merged],cmp=lambda x,y: cmp(x,y))
			if solconfig.startswith('Win'):
				pathformat = 'Windows'
			else:
				pathformat = 'Unix'
			for file in sortlist:
				if pathformat=='Unix':
					file2 = burger.converttolinuxslashes(file)
				else:
					file2 = file
				fp.write(tabs + '<FILEREF>\n')
				fp.write(tabs + '\t<TARGETNAME>' + solconfig + '</TARGETNAME>\n')
				fp.write(tabs + '\t<PATHTYPE>Name</PATHTYPE>\n')
				fp.write(tabs + '\t<PATH>' + os.path.basename(file2) + '</PATH>\n')
				fp.write(tabs + '\t<PATHFORMAT>' + pathformat + '</PATHFORMAT>\n')
				fp.write(tabs + '</FILEREF>\n')
				
		key = entry[item]
		if type(key) is dict:
			dumptreecodewarrior(indent+1,merged,key,fp,groups,solconfig)
		if item!='':
			fp.write('\t'*indent + '</GROUP>\n')
			
#
# Create a codewarrior 9.4 project
#

def createcodewarriorsolution(solution):
		
	#
	# Now, let's create the project file
	#
	
	codefiles,includedirectories = solution.getfilelist([FileTypes.h,FileTypes.cpp,FileTypes.rc,FileTypes.hlsl,FileTypes.glsl])
	platformcode = solution.getplatformcode()
	idecode = solution.getidecode()
	projectfilename = str(solution.projectname + idecode + platformcode)
	projectpathname = os.path.join(solution.workingDir,projectfilename + '.mcp.xml')

	#
	# Save out the filenames
	#
	
	listh = pickfromfilelist(codefiles,FileTypes.h)
	listcpp = pickfromfilelist(codefiles,FileTypes.cpp)
	listwindowsresource = []
	if platformcode=='win':
		listwindowsresource = pickfromfilelist(codefiles,FileTypes.rc)
	
	alllists = listh + listcpp + listwindowsresource

	fp = open(projectpathname,'w')
	
	#
	# Save the standard XML header for CodeWarrior
	#
	
	fp.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
	if platformcode=='mac':
		# Codewarrior 10 for Mac OS
		fp.write('<?codewarrior exportversion="2.0" ideversion="5.8" ?>\n')
	else:
		# Codewarrior 9 for Windows
		fp.write('<?codewarrior exportversion="1.0.1" ideversion="5.0" ?>\n')

	#
	# Begin the project object
	#
	
	fp.write('<PROJECT>\n')

	#
	# Create all of the project targets
	#
	
	fp.write('\t<TARGETLIST>\n')
		
	#
	# Begin with a fake project that will build all of the other projects
	#
	
	fp.write('\t\t<TARGET>\n')
	fp.write('\t\t\t<NAME>Everything</NAME>\n')
	fp.write('\t\t\t<SETTINGLIST>\n')
	fp.write('\t\t\t\t<SETTING><NAME>Linker</NAME><VALUE>None</VALUE></SETTING>\n')
	fp.write('\t\t\t\t<SETTING><NAME>Targetname</NAME><VALUE>Everything</VALUE></SETTING>\n')
	fp.write('\t\t\t</SETTINGLIST>\n')
	fp.write('\t\t\t<FILELIST>\n')
	fp.write('\t\t\t</FILELIST>\n')
	fp.write('\t\t\t<LINKORDER>\n')
	fp.write('\t\t\t</LINKORDER>\n')
	if len(solution.configurations)!=0:
		fp.write('\t\t\t<SUBTARGETLIST>\n')
		for target in solution.configurations:
			if solution.platform=='windows':
				platformcode2 = 'Win32'
			else:
				platformcode2 = solution.platform
			fp.write('\t\t\t\t<SUBTARGET>\n')
			fp.write('\t\t\t\t\t<TARGETNAME>' + platformcode2 + ' ' + target + '</TARGETNAME>\n')	
			fp.write('\t\t\t\t</SUBTARGET>\n')
		fp.write('\t\t\t</SUBTARGETLIST>\n')
	fp.write('\t\t</TARGET>\n')

	#
	# Output each target
	#
	
	for target in solution.configurations:
	
		# Create the target name
		
		if solution.platform=='windows':
			platformcode2 = 'Win32'
			pathformat = 'Windows'
		else:
			platformcode2 = solution.platform
			pathformat = 'Unix'
		fp.write('\t\t<TARGET>\n')
		fp.write('\t\t\t<NAME>' + platformcode2 + ' ' + target + '</NAME>\n')	
		
		#
		# Store the settings for the target
		#
		
		fp.write('\t\t\t<SETTINGLIST>\n')
		
		#
		# Choose the target platform via the linker
		#
		
		
		if solution.platform=='windows':
		
			#
			# Make sure that BURGER_SDKS are pointed to by the environment variable BURGER_SDKS on
			# windows hosts
			#
			
			fp.write('\t\t\t\t<SETTING><NAME>UserSourceTrees</NAME>\n')
			fp.write('\t\t\t\t\t<SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>Name</NAME><VALUE>BURGER_SDKS</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>Kind</NAME><VALUE>EnvironmentVariable</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>VariableName</NAME><VALUE>BURGER_SDKS</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t</SETTING>\n')
			fp.write('\t\t\t\t</SETTING>\n')
			
			fp.write('\t\t\t\t<SETTING><NAME>Linker</NAME><VALUE>Win32 x86 Linker</VALUE></SETTING>\n')
		else:
			fp.write('\t\t\t\t<SETTING><NAME>Linker</NAME><VALUE>MacOS PPC Linker</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>Targetname</NAME><VALUE>' + platformcode2 + ' ' + target + '</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>OutputDirectory</NAME>\n')
		fp.write('\t\t\t\t\t<SETTING><NAME>Path</NAME><VALUE>bin</VALUE></SETTING>\n')
		fp.write('\t\t\t\t\t<SETTING><NAME>PathFormat</NAME><VALUE>' + pathformat + '</VALUE></SETTING>\n')
		fp.write('\t\t\t\t\t<SETTING><NAME>PathRoot</NAME><VALUE>Project</VALUE></SETTING>\n')
		fp.write('\t\t\t\t</SETTING>\n')
		
		#
		# User include folders
		#
		
		if len(includedirectories)!=0:
			fp.write('\t\t\t\t<SETTING><NAME>UserSearchPaths</NAME>\n')
			for dirnameentry in includedirectories:
				fp.write('\t\t\t\t\t<SETTING>\n')
				fp.write('\t\t\t\t\t\t<SETTING><NAME>SearchPath</NAME>\n')
				if solution.platform=='windows':
					fp.write('\t\t\t\t\t\t\t<SETTING><NAME>Path</NAME><VALUE>' + burger.converttowindowsslashes(dirnameentry) + '</VALUE></SETTING>\n')
				else:
					fp.write('\t\t\t\t\t\t\t<SETTING><NAME>Path</NAME><VALUE>' + burger.converttolinuxslashes(dirnameentry) + '</VALUE></SETTING>\n')
				fp.write('\t\t\t\t\t\t\t<SETTING><NAME>PathFormat</NAME><VALUE>' + pathformat + '</VALUE></SETTING>\n')
				fp.write('\t\t\t\t\t\t\t<SETTING><NAME>PathRoot</NAME><VALUE>Project</VALUE></SETTING>\n')
				fp.write('\t\t\t\t\t\t</SETTING>\n')
				fp.write('\t\t\t\t\t\t<SETTING><NAME>Recursive</NAME><VALUE>false</VALUE></SETTING>\n')
				fp.write('\t\t\t\t\t\t<SETTING><NAME>FrameworkPath</NAME><VALUE>false</VALUE></SETTING>\n')
				fp.write('\t\t\t\t\t\t<SETTING><NAME>HostFlags</NAME><VALUE>All</VALUE></SETTING>\n')
				fp.write('\t\t\t\t\t</SETTING>\n')
			fp.write('\t\t\t\t</SETTING>\n')

		#
		# Operating system include folders
		#
		
		fp.write('\t\t\t\t<SETTING><NAME>SystemSearchPaths</NAME>\n')
		directoryfolders = []
		
		if solution.kind!='library' or solution.projectname!='burgerlib':
			directoryfolders.append('windows\\burgerlib')
			#directoryfolders.append('windows\\burgerlib4')
		
		directoryfolders.append('windows\\perforce')
		directoryfolders.append('windows\\opengl')
		directoryfolders.append('windows\\directx9')
		

		for dirnameentry in directoryfolders:
			fp.write('\t\t\t\t\t<SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>SearchPath</NAME>\n')
			fp.write('\t\t\t\t\t\t\t<SETTING><NAME>Path</NAME><VALUE>' + dirnameentry + '</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t\t<SETTING><NAME>PathFormat</NAME><VALUE>' + pathformat + '</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t\t<SETTING><NAME>PathRoot</NAME><VALUE>BURGER_SDKS</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t</SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>Recursive</NAME><VALUE>false</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>FrameworkPath</NAME><VALUE>false</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>HostFlags</NAME><VALUE>All</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t</SETTING>\n')

		for dirnameentry in ['MSL','Win32-x86 Support']:
			fp.write('\t\t\t\t\t<SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>SearchPath</NAME>\n')
			fp.write('\t\t\t\t\t\t\t<SETTING><NAME>Path</NAME><VALUE>' + dirnameentry + '</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t\t<SETTING><NAME>PathFormat</NAME><VALUE>' + pathformat + '</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t\t<SETTING><NAME>PathRoot</NAME><VALUE>CodeWarrior</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t</SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>Recursive</NAME><VALUE>true</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>FrameworkPath</NAME><VALUE>false</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t\t<SETTING><NAME>HostFlags</NAME><VALUE>All</VALUE></SETTING>\n')
			fp.write('\t\t\t\t\t</SETTING>\n')

		fp.write('\t\t\t\t</SETTING>\n')

		#
		# Library/Application?
		#
		
		if solution.platform=='windows':
			platformcode2 = 'w32'
		else:
			platformcode2 = solution.platform
		if solution.kind=='library':
			fp.write('\t\t\t\t<SETTING><NAME>MWProject_X86_type</NAME><VALUE>Library</VALUE></SETTING>\n')
			fp.write('\t\t\t\t<SETTING><NAME>MWProject_X86_outfile</NAME><VALUE>' + solution.projectname + idecode + platformcode2 + getconfigurationcode(target) + '.lib</VALUE></SETTING>\n')
		else:
			fp.write('\t\t\t\t<SETTING><NAME>MWProject_X86_type</NAME><VALUE>Application</VALUE></SETTING>\n')
			fp.write('\t\t\t\t<SETTING><NAME>MWProject_X86_outfile</NAME><VALUE>' + solution.projectname + idecode + platformcode2 + getconfigurationcode(target) + '.exe</VALUE></SETTING>\n')

		#
		# Compiler settings for the front end
		#
		
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_cplusplus</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_templateparser</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_instance_manager</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_enableexceptions</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_useRTTI</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_booltruefalse</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_wchar_type</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_ecplusplus</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_dontinline</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_inlinelevel</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_autoinline</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_defer_codegen</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_bottomupinline</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_ansistrict</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_onlystdkeywords</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_trigraphs</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_arm</NAME><VALUE>0</VALUE></SETTING>\n')		
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_checkprotos</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_c99</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_gcc_extensions</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_enumsalwaysint</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_unsignedchars</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_poolstrings</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWFrontEnd_C_dontreusestrings</NAME><VALUE>0</VALUE></SETTING>\n')

		#
		# Preprocessor settings
		#
		
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_PrefixText</NAME><VALUE>#define ')
		if target=='Release':
			fp.write('NDEBUG\n')
		else:
			fp.write('_DEBUG\n')
		if platformcode2=='w32':
			fp.write('#define WIN32_LEAN_AND_MEAN\n#define WIN32\n')
		for defineentry in solution.defines:
			fp.write('#define ' + defineentry + '\n')
		fp.write('</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_MultiByteEncoding</NAME><VALUE>encASCII_Unicode</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_PCHUsesPrefixText</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_EmitPragmas</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_KeepWhiteSpace</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_EmitFullPath</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_KeepComments</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_EmitFile</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>C_CPP_Preprocessor_EmitLine</NAME><VALUE>false</VALUE></SETTING>\n')

		#
		# Warnings panel
		#
		
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_illpragma</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_possunwant</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_pedantic</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_illtokenpasting</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_hidevirtual</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_implicitconv</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_impl_f2i_conv</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_impl_s2u_conv</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_impl_i2f_conv</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_ptrintconv</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_unusedvar</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_unusedarg</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_resultnotused</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_missingreturn</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_no_side_effect</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_extracomma</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_structclass</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_emptydecl</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_filenamecaps</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_filenamecapssystem</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_padding</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_undefmacro</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warn_notinlined</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWWarning_C_warningerrors</NAME><VALUE>0</VALUE></SETTING>\n')

		#
		# X86 code gen
		#
		
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_runtime</NAME><VALUE>Custom</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_processor</NAME><VALUE>PentiumIV</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_use_extinst</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_extinst_mmx</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_extinst_3dnow</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_extinst_cmov</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_extinst_sse</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_extinst_sse2</NAME><VALUE>0</VALUE></SETTING>\n')

		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_use_mmx_3dnow_convention</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_vectorize</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_profile</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_readonlystrings</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_alignment</NAME><VALUE>bytes8</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_intrinsics</NAME><VALUE>1</VALUE></SETTING>\n')
		if target=='Debug':
			fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_optimizeasm</NAME><VALUE>0</VALUE></SETTING>\n')
			fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_disableopts</NAME><VALUE>1</VALUE></SETTING>\n')
		else:
			fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_optimizeasm</NAME><VALUE>1</VALUE></SETTING>\n')
			fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_disableopts</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_relaxieee</NAME><VALUE>1</VALUE></SETTING>\n')

		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_exceptions</NAME><VALUE>ZeroOverhead</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWCodeGen_X86_name_mangling</NAME><VALUE>MWWin32</VALUE></SETTING>\n')
		
		#
		# Global optimizations
		#
		
		if target=='Debug':
			fp.write('\t\t\t\t<SETTING><NAME>GlobalOptimizer_X86__optimizationlevel</NAME><VALUE>Level0</VALUE></SETTING>\n')
		else:
			fp.write('\t\t\t\t<SETTING><NAME>GlobalOptimizer_X86__optimizationlevel</NAME><VALUE>Level4</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>GlobalOptimizer_X86__optfor</NAME><VALUE>Size</VALUE></SETTING>\n')

		#
		# x86 disassembler
		#
		
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showHeaders</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showSectHeaders</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showSymTab</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showCode</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showData</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showDebug</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showExceptions</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showRelocation</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showRaw</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showAllRaw</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showSource</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showHex</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showComments</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_resolveLocals</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_resolveRelocs</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_showSymDefs</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_unmangle</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>PDisasmX86_verbose</NAME><VALUE>false</VALUE></SETTING>\n')

		#
		# x86 linker settings
		#

		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_linksym</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_linkCV</NAME><VALUE>1</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_symfullpath</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_linkdebug</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_debuginline</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_subsystem</NAME><VALUE>Unknown</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_entrypointusage</NAME><VALUE>Default</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_entrypoint</NAME><VALUE></VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_codefolding</NAME><VALUE>Any</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_usedefaultlibs</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_adddefaultlibs</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_mergedata</NAME><VALUE>true</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_zero_init_bss</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_generatemap</NAME><VALUE>0</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_checksum</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_linkformem</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_nowarnings</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_verbose</NAME><VALUE>false</VALUE></SETTING>\n')
		fp.write('\t\t\t\t<SETTING><NAME>MWLinker_X86_commandfile</NAME><VALUE></VALUE></SETTING>\n')

		#
		# Settings are done
		#
		
		fp.write('\t\t\t</SETTINGLIST>\n')
		
		#
		# Add in the list of files
		#
		
		liblist = []
		if solution.kind!='library':
			if target=='Debug':
				liblist.append('burgerlibcw9w32dbg.lib')
				#liblist.append('burgercw9w32dbg.lib')
			elif target=='Internal':
				liblist.append('burgerlibcw9w32int.lib')
				#liblist.append('burgercw9w32int.lib')
			else:
				liblist.append('burgerlibcw9w32rel.lib')
				#liblist.append('burgercw9w32rel.lib')

		liblist.append('user32.lib')
		liblist.append('kernel32.lib')
		liblist.append('gdi32.lib')
		liblist.append('winmm.lib')
		liblist.append('version.lib')
		liblist.append('shell32.lib')
		liblist.append('advapi32.lib')
		liblist.append('shlwapi.lib')

		if target=='Debug':
			liblist.append('MSL_All_x86_D.lib')
		else:
			liblist.append('MSL_All_x86.lib')

		if len(alllists)!=0:
			
			fp.write('\t\t\t<FILELIST>\n')
			if solution.kind!='library':
				for i in liblist:
					fp.write('\t\t\t\t<FILE>\n')
					fp.write('\t\t\t\t\t<PATHTYPE>Name</PATHTYPE>\n')
					fp.write('\t\t\t\t\t<PATH>' + i + '</PATH>\n')
					fp.write('\t\t\t\t\t<PATHFORMAT>' + pathformat + '</PATHFORMAT>\n')
					fp.write('\t\t\t\t\t<FILEKIND>Library</FILEKIND>\n')
					if target!='Release': 
						fp.write('\t\t\t\t\t<FILEFLAGS>Debug</FILEFLAGS>\n')
					else:
						fp.write('\t\t\t\t\t<FILEFLAGS></FILEFLAGS>\n')
					fp.write('\t\t\t\t</FILE>\n')
				
			filelist = []
			for i in alllists:
				parts = burger.converttowindowsslashes(i.filename).split('\\')
				filelist.append(parts[len(parts)-1])
		
			filelist = sorted(filelist,cmp=lambda x,y: cmp(x,y))

			for i in filelist:
				fp.write('\t\t\t\t<FILE>\n')
				fp.write('\t\t\t\t\t<PATHTYPE>Name</PATHTYPE>\n')
				fp.write('\t\t\t\t\t<PATH>' + i + '</PATH>\n')
				fp.write('\t\t\t\t\t<PATHFORMAT>' + pathformat + '</PATHFORMAT>\n')
				fp.write('\t\t\t\t\t<FILEKIND>Text</FILEKIND>\n')
				if target!='Release' and (i.endswith('.c') or i.endswith('.cpp')): 
					fp.write('\t\t\t\t\t<FILEFLAGS>Debug</FILEFLAGS>\n')
				else:
					fp.write('\t\t\t\t\t<FILEFLAGS></FILEFLAGS>\n')
				fp.write('\t\t\t\t</FILE>\n')
			
			fp.write('\t\t\t</FILELIST>\n')
		
			fp.write('\t\t\t<LINKORDER>\n')
			if solution.kind!='library':
				for i in liblist:
					fp.write('\t\t\t\t<FILEREF>\n')
					fp.write('\t\t\t\t\t<PATHTYPE>Name</PATHTYPE>\n')
					fp.write('\t\t\t\t\t<PATH>' + i + '</PATH>\n')
					fp.write('\t\t\t\t\t<PATHFORMAT>' + pathformat + '</PATHFORMAT>\n')
					fp.write('\t\t\t\t</FILEREF>\n')
			for i in filelist:
				fp.write('\t\t\t\t<FILEREF>\n')
				fp.write('\t\t\t\t\t<PATHTYPE>Name</PATHTYPE>\n')
				fp.write('\t\t\t\t\t<PATH>' + i + '</PATH>\n')
				fp.write('\t\t\t\t\t<PATHFORMAT>' + pathformat + '</PATHFORMAT>\n')
				fp.write('\t\t\t\t</FILEREF>\n')
			fp.write('\t\t\t</LINKORDER>\n')
		
		fp.write('\t\t</TARGET>\n')

	#
	# All of the targets are saved
	#
	
	fp.write('\t</TARGETLIST>\n')
	
	#
	# Now output the list of targets
	#
	
	fp.write('\t<TARGETORDER>\n')
	fp.write('\t\t<ORDEREDTARGET><NAME>Everything</NAME></ORDEREDTARGET>\n')
	for target in solution.configurations:
		if solution.platform=='windows':
			platformcode2 = 'Win32'
		else:
			platformcode2 = solution.platform
		fp.write('\t\t<ORDEREDTARGET><NAME>' + platformcode2 + ' ' + target + '</NAME></ORDEREDTARGET>\n')
	fp.write('\t</TARGETORDER>\n')

	#
	# Save the file list as they are displayed in the IDE
	#
	
	if len(alllists):

		#	
		# Create groups first since CodeWarrior uses a nested tree structure
		# for file groupings
		#
		
		groups = dict()
		for item in alllists:
			groupname = item.extractgroupname()
			# Put each filename in its proper group
			if groupname in groups:
				groups[groupname].append(burger.converttowindowsslashes(item.filename))
			else:
				# New group!
				groups[groupname] = [burger.converttowindowsslashes(item.filename)]
		
		#
		# Create a recursive tree in order to store out the file list
		#

		if 'Release' in solution.configurations:
			solconfig = platformcode2 + ' Release'
		else:
			solconfig = platformcode2 + ' ' + solution.configurations[0]

		fp.write('\t<GROUPLIST>\n')
		tree = dict()
		for group in groups:
			#
			# Get the depth of the tree needed
			#
			
			parts = group.split('\\')
			next = tree
			#
			# Iterate over every part
			#
			for x in xrange(len(parts)):
				# Already declared?
				if not parts[x] in next:
					next[parts[x]] = dict()
				# Step into the tree
				next = next[parts[x]]

		# Use this tree to play back all the data
		dumptreecodewarrior(2,'',tree,fp,groups,solconfig)
		
		if solution.kind!='library':
			liblist = []
				
			liblist.append(['user32.lib',solconfig])
			liblist.append(['kernel32.lib',solconfig])
			liblist.append(['gdi32.lib',solconfig])
			liblist.append(['winmm.lib',solconfig])
			liblist.append(['version.lib',solconfig])
			liblist.append(['shell32.lib',solconfig])
			liblist.append(['advapi32.lib',solconfig])
			liblist.append(['shlwapi.lib',solconfig])
			
			if 'Release' in solution.configurations:
				liblist.append(['burgerlibcw9w32rel.lib','Win32 Release'])
				#liblist.append(['burgercw9w32rel.lib','Win32 Release'])
				liblist.append(['MSL_All_x86.lib','Win32 Release'])
			
			if 'Internal' in solution.configurations:
				liblist.append(['burgerlibcw9w32int.lib','Win32 Internal'])
				#liblist.append(['burgercw9w32int.lib','Win32 Internal'])
				if not 'Release' in solution.configurations:
					liblist.append(['MSL_All_x86.lib','Win32 Internal'])

			if 'Debug' in solution.configurations:
				liblist.append(['burgerlibcw9w32dbg.lib','Win32 Debug'])
				#liblist.append(['burgercw9w32dbg.lib','Win32 Debug'])
				liblist.append(['MSL_All_x86_D.lib','Win32 Debug'])

				
			fp.write('\t\t<GROUP><NAME>Libraries</NAME>\n')
			for i in liblist:
				fp.write('\t\t\t<FILEREF>\n')
				fp.write('\t\t\t\t<TARGETNAME>' + i[1] + '</TARGETNAME>\n')
				fp.write('\t\t\t\t<PATHTYPE>Name</PATHTYPE>\n')
				fp.write('\t\t\t\t<PATH>' + i[0] + '</PATH>\n')
				fp.write('\t\t\t\t<PATHFORMAT>Windows</PATHFORMAT>\n')
				fp.write('\t\t\t</FILEREF>\n')

			fp.write('\t\t</GROUP>\n')
	
		fp.write('\t</GROUPLIST>\n')

	#
	# Close the file
	#
	
	fp.write('</PROJECT>\n')
	fp.close()
	
	#
	# If codewarrior is installed, create the MCP file
	#
	
	cwfile = os.getenv('CWFolder')
	if cwfile!=None and solution.platform=='windows':
		burger.perforceedit(os.path.join(solution.workingDir,projectfilename + '.mcp'))
		cwfile = os.path.join(cwfile,'Bin','ide')
		cmd = '"' + cwfile + '" /x "' + projectpathname + '" "' + os.path.join(solution.workingDir,projectfilename + '.mcp') + '" /s /c /q'
		sys.stdout.flush()
		error = subprocess.call(cmd,cwd=os.path.dirname(projectpathname),shell=True)
		if error==0:
			os.remove(projectpathname)
		return error
		
	return 0

#
# Create a codeblocks 13.12 project
#

def createcodeblockssolution(solution):
		
	#
	# Now, let's create the project file
	#
	
	codefiles,includedirectories = solution.getfilelist([FileTypes.h,FileTypes.cpp,FileTypes.rc,FileTypes.hlsl,FileTypes.glsl])
	platformcode = solution.getplatformcode()
	idecode = solution.getidecode()
	projectfilename = str(solution.projectname + idecode + platformcode)
	projectpathname = os.path.join(solution.workingDir,projectfilename + '.cbp')

	#
	# Save out the filenames
	#
	
	listh = pickfromfilelist(codefiles,FileTypes.h)
	listcpp = pickfromfilelist(codefiles,FileTypes.cpp)
	listwindowsresource = []
	if platformcode=='win':
		listwindowsresource = pickfromfilelist(codefiles,FileTypes.rc)
	
	alllists = listh + listcpp + listwindowsresource

	burger.perforceedit(projectpathname)
	fp = open(projectpathname,'w')
	
	#
	# Save the standard XML header for CodeBlocks
	#
	
	fp.write('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n')
	fp.write('<CodeBlocks_project_file>\n')
	fp.write('\t<FileVersion major="1" minor="6" />\n')
	fp.write('\t<Project>\n')
	
	#
	# Output the project settings
	#
	
	fp.write('\t\t<Option title="burgerlib" />\n')
	fp.write('\t\t<Option makefile="makefile" />\n')
	fp.write('\t\t<Option pch_mode="2" />\n')
	fp.write('\t\t<Option compiler="ow" />\n')
		
	#
	# Output the per target build settings
	#
	
	
	fp.write('\t\t<Build>\n')
	
	fp.write('\t\t\t<Target title="Debug">\n')
	fp.write('\t\t\t\t<Option output="bin/burgerlibcdbwatw32dbg.lib" prefix_auto="0" extension_auto="0" />\n')
	fp.write('\t\t\t\t<Option working_dir="" />\n')
	fp.write('\t\t\t\t<Option object_output="temp/burgerlibcbpwatw32dbg/" />\n')
	if solution.kind=='tool':
		fp.write('\t\t\t\t<Option type="1" />\n')
	else:
		fp.write('\t\t\t\t<Option type="2" />\n')
	fp.write('\t\t\t\t<Option compiler="ow" />\n')
	fp.write('\t\t\t\t<Option createDefFile="1" />\n')
	fp.write('\t\t\t\t<Compiler>\n')
	fp.write('\t\t\t\t\t<Add option="-d2" />\n')
	fp.write('\t\t\t\t\t<Add option="-wx" />\n')
	fp.write('\t\t\t\t\t<Add option="-fp6" />\n')
	fp.write('\t\t\t\t\t<Add option="-6r" />\n')
	fp.write('\t\t\t\t\t<Add option="-fr=$(ERROR_FILE)" />\n')
	fp.write('\t\t\t\t\t<Add option="-d_DEBUG" />\n')
	fp.write('\t\t\t\t</Compiler>\n')
	fp.write('\t\t\t</Target>\n')

	fp.write('\t\t\t<Target title="Internal">\n')
	fp.write('\t\t\t\t<Option output="bin/burgerlibcdbwatw32int.lib" prefix_auto="0" extension_auto="0" />\n')
	fp.write('\t\t\t\t<Option working_dir="" />\n')
	fp.write('\t\t\t\t<Option object_output="temp/burgerlibcbpwatw32int/" />\n')
	if solution.kind=='tool':
		fp.write('\t\t\t\t<Option type="1" />\n')
	else:
		fp.write('\t\t\t\t<Option type="2" />\n')
	fp.write('\t\t\t\t<Option compiler="ow" />\n')
	fp.write('\t\t\t\t<Option createDefFile="1" />\n')
	fp.write('\t\t\t\t<Compiler>\n')
	fp.write('\t\t\t\t\t<Add option="-ox" />\n')
	fp.write('\t\t\t\t\t<Add option="-ot" />\n')
	fp.write('\t\t\t\t\t<Add option="-wx" />\n')
	fp.write('\t\t\t\t\t<Add option="-fr=$(ERROR_FILE)" />\n')
	fp.write('\t\t\t\t\t<Add option="-fp6" />\n')
	fp.write('\t\t\t\t\t<Add option="-6r" />\n')
	fp.write('\t\t\t\t\t<Add option="-d_DEBUG" />\n')
	fp.write('\t\t\t\t</Compiler>\n')
	fp.write('\t\t\t</Target>\n')

	fp.write('\t\t\t<Target title="Release">\n')
	fp.write('\t\t\t\t<Option output="bin/burgerlibcdbwatw32rel.lib" prefix_auto="0" extension_auto="0" />\n')
	fp.write('\t\t\t\t<Option working_dir="" />\n')
	fp.write('\t\t\t\t<Option object_output="temp/burgerlibcbpwatw32rel/" />\n')
	if solution.kind=='tool':
		fp.write('\t\t\t\t<Option type="1" />\n')
	else:
		fp.write('\t\t\t\t<Option type="2" />\n')
	fp.write('\t\t\t\t<Option compiler="ow" />\n')
	fp.write('\t\t\t\t<Option createDefFile="1" />\n')
	fp.write('\t\t\t\t<Compiler>\n')
	fp.write('\t\t\t\t\t<Add option="-ox" />\n')
	fp.write('\t\t\t\t\t<Add option="-ot" />\n')
	fp.write('\t\t\t\t\t<Add option="-wx" />\n')
	fp.write('\t\t\t\t\t<Add option="-fr=$(ERROR_FILE)" />\n')
	fp.write('\t\t\t\t\t<Add option="-fp6" />\n')
	fp.write('\t\t\t\t\t<Add option="-6r" />\n')
	fp.write('\t\t\t\t\t<Add option="-dNDEBUG" />\n')
	fp.write('\t\t\t\t</Compiler>\n')
	fp.write('\t\t\t</Target>\n')
	
	fp.write('\t\t\t<Environment>\n')
	fp.write('\t\t\t\t<Variable name="ERROR_FILE" value="$(TARGET_OBJECT_DIR)foo.err" />\n')
	fp.write('\t\t\t</Environment>\n')
	fp.write('\t\t</Build>\n')
		
	#
	# Output the virtual target
	#
	
	fp.write('\t\t<VirtualTargets>\n')
	fp.write('\t\t\t<Add alias="Everything" targets="')
	for target in solution.configurations:
		fp.write(target + ';')
	fp.write('" />\n')
	fp.write('\t\t</VirtualTargets>\n')
	
	#
	# Output the global compiler settings
	#
	
	fp.write('\t\t<Compiler>\n')
	fp.write('\t\t\t<Add option="-dGLUT_DISABLE_ATEXIT_HACK" />\n')
	fp.write('\t\t\t<Add option="-dGLUT_NO_LIB_PRAGMA" />\n')
	fp.write('\t\t\t<Add option="-dTARGET_CPU_X86=1" />\n')
	fp.write('\t\t\t<Add option="-dTARGET_OS_WIN32=1" />\n')
	fp.write('\t\t\t<Add option="-dTYPE_BOOL=1" />\n')
	fp.write('\t\t\t<Add option="-dUNICODE" />\n')
	fp.write('\t\t\t<Add option="-d_UNICODE" />\n')
	fp.write('\t\t\t<Add option="-dWIN32_LEAN_AND_MEAN" />\n')

	for dirnameentry in includedirectories:
		fp.write('\t\t\t<Add directory=\'&quot;' + burger.converttolinuxslashes(dirnameentry) + '&quot;\' />\n')

	if solution.kind!='library' or solution.projectname!='burgerlib':
		fp.write('\t\t\t<Add directory=\'&quot;$(BURGER_SDKS)/windows/burgerlib&quot;\' />\n')
	fp.write('\t\t\t<Add directory=\'&quot;$(BURGER_SDKS)/windows/perforce&quot;\' />\n')
	fp.write('\t\t\t<Add directory=\'&quot;$(BURGER_SDKS)/windows/opengl&quot;\' />\n')
	fp.write('\t\t\t<Add directory=\'&quot;$(BURGER_SDKS)/windows/directx9&quot;\' />\n')
	fp.write('\t\t\t<Add directory=\'&quot;$(BURGER_SDKS)/windows/windows5&quot;\' />\n')
	fp.write('\t\t</Compiler>\n')
		
	#
	# Output the list of source files
	#
	
	filelist = []
	for i in alllists:
		filelist.append(burger.converttolinuxslashes(i.filename))
		
	filelist = sorted(filelist,cmp=lambda x,y: cmp(x,y))
	
	for i in filelist:
		fp.write('\t\t<Unit filename="' + i + '" />\n')
	
	#
	# Add the extensions (If any)
	#

	fp.write('\t\t<Extensions>\n')
	fp.write('\t\t\t<code_completion />\n')
	fp.write('\t\t\t<envvars />\n')
	fp.write('\t\t\t<debugger />\n')
	fp.write('\t\t</Extensions>\n')

	#
	# Close the file
	#

	fp.write('\t</Project>\n')	
	fp.write('</CodeBlocks_project_file>\n')
	fp.close()
	return 0

#
# Create an OpenWatcom makefile
#

def createwatcomsolution(solution):
		
	#
	# Now, let's create the project file
	#
	
	codefiles,includedirectories = solution.getfilelist([FileTypes.h,FileTypes.cpp,FileTypes.x86])
	platformcode = solution.getplatformcode()
	idecode = solution.getidecode()
	projectfilename = str(solution.projectname + idecode + platformcode)
	projectpathname = os.path.join(solution.workingDir,projectfilename + '.wmk')

	#
	# Save out the filenames
	#
	
	listh = pickfromfilelist(codefiles,FileTypes.h)
	listcpp = pickfromfilelist(codefiles,FileTypes.cpp)
	listx86 = pickfromfilelist(codefiles,FileTypes.x86)
	listwindowsresource = []
	#if platformcode=='win':
	#	listwindowsresource = pickfromfilelist(codefiles,FileTypes.rc)
	
	alllists = listh + listcpp + listx86 + listwindowsresource

	burger.perforceedit(projectpathname)
	fp = open(projectpathname,'w')
	fp.write(
		'#\n'
		'# Build ' + solution.projectname + ' for ' + solution.platform + '\n'
		'#\n\n'
		'#\n'
		'# sourcedir = Set the work directories for the source\n'
		'#\n\n')	

	filelist = []
	for item in alllists:
		filelist.append(burger.converttowindowsslashes(item.filename))
		
	filelist = sorted(filelist,cmp=lambda x,y: cmp(x,y))
	
	sourcedir = []	
	for item in filelist:
		#
		# Remove the filename
		#
		index = item.rfind('\\')
		if index==-1:
			entry = item
		else:
			entry = item[0:index]
		if not entry in sourcedir:
			sourcedir.append(entry)
	
	fp.write("sourcedir = ")
	string = ''
	for item in sourcedir:
		string = string + item + ';'
	
	if len(string):
		# Get rid of the trailing semi colon
		string = string[0:len(string)-1]
		fp.write(string)
		
	fp.write('\n\n'
		'#\n'
		'# Name of the output library\n'
		'#\n\n'
		'projectname = ' + solution.projectname + '\n\n'

		'#\n'
		'# includedir = Header includes\n'
		'#\n\n'
		'includedir = $(sourcedir)')
		
	if len(solution.includefolders):
		string = ''
		for item in solution.includefolders:
			string = string + ';' + burger.converttowindowsslashes(item)
		fp.write(string)
	
	fp.write('\n\n'
		'#\n'
		'# Object files to work with for the library\n'
		'#\n\n')
		
	string = 'objs= &'
	for item in filelist:
		if not item.endswith('.h'):
			index = item.rfind('.')
			if index==-1:
				entry = item
			else:
				entry = item[0:index]

			index = entry.rfind('\\')
			if index==-1:
				entry = entry
			else:
				entry = entry[index+1:len(entry)]

			string = string + '\n\t$(A)\\' + entry + '.obj &'

	# Get rid of the trailing ampersand and space
	string = string[0:len(string)-2]
	fp.write(string + '\n\n')
	
	if solution.finalfolder!=None:
		final = burger.converttowindowsslashes(solution.finalfolder)
		if final.endswith('\\'):
			final = final[0:len(final)-1]
			
		fp.write('#\n'
			'# Final location folder\n'
			'#\n\n'
			'finalfolder = ' + final + '\n\n')			
			
	fp.write(
		'#\n'
		'# Create the build environment\n'
		'#\n\n'
		'!include $(%sdks)\\watcom\\burger.mif\n\n'
		'#\n'
		'# List the names of all of the final binaries to build\n'
		'#\n\n'
		'all : .SYMBOLIC\n')
	
	platforms = []
	if solution.platform == 'msdos':
		platforms = ['x32','dos4gw']
	elif solution.platform == 'windows':
		platforms = ['w32']
	
	if solution.kind=='library':
		suffix = 'lib'
	else:
		suffix = 'exe'
		
	for theplatform in platforms:
		if theplatform=='dos4gw':
			shortplatform = '4gw'
		else:
			shortplatform = theplatform
			
		for target in solution.configurations:
			fp.write('\t@set config=' + target + '\n')
			fp.write('\t@set target=' + theplatform + '\n')
			fp.write('\t@%make $(destdir)\$(projectname)wat' + shortplatform + getconfigurationcode(target) + '.' + suffix + '\n')

	fp.write('\n' +
		projectfilename + '.wmk :\n'
		'\t@%null\n'
		'\n'
		'#\n'
		'# A = The object file temp folder\n'
		'#\n'
		'\n')
		
	for theplatform in platforms:
		for target in solution.configurations:
			if theplatform=='dos4gw':
				theplatform = '4gw'
			fp.write('A = $(basetempdir)wat' + theplatform + getconfigurationcode(target) + '\n'
				'$(destdir)\\$(projectname)wat' + theplatform + getconfigurationcode(target) + '.' + suffix + ' : $+$(OBJS)$- ' + projectfilename + '.wmk\n'
				'\t@if not exist $(destdir) @!mkdir $(destdir)\n')
			if solution.kind=='library':

				fp.write('\t@SET WOW=$+$(OBJS)$-\n'
					'\t@WLIB -q -b -c -n $^@ @WOW\n')

				if solution.finalfolder!=None:
					fp.write('\t@"$(%perforce)\\p4" edit "$(finalfolder)\$^."\n'
						'\t@copy /y "$^@" "$(finalfolder)\\$^."\n'
						'\t@"$(%perforce)\\p4" revert -a "$(finalfolder)\\$^."\n\n')
			else:
				fp.write('\t@SET WOW={$+$(OBJS)$-}\n'
					'\t@$(LINK) $(LFlagsw32) $(LFlags' + target + ') LIBRARY burgerlibwat' + theplatform + getconfigurationcode(target) + '.lib NAME $^@ FILE @wow\n\n')
		
	fp.close()
	return 0

#
# Command line shell
#

	
def run(workingDir):

	#
	# Parse the command line
	#
	
	parser = argparse.ArgumentParser(
		description='Create project files. Copyright by Rebecca Ann Heineman. Given a .json input file, create project files')
	parser.add_argument('-xcode3', dest='xcode3', action='store_true',
		default=False,
		help='Build for Xcode 3.')
	parser.add_argument('-xcode4', dest='xcode4', action='store_true',
		default=False,
		help='Build for Xcode 4.')
	parser.add_argument('-xcode5', dest='xcode5', action='store_true',
		default=False,
		help='Build for Xcode 5.')
	parser.add_argument('-vs2005', dest='vs2005', action='store_true',
		default=False,
		help='Build for Visual Studio 2005.')
	parser.add_argument('-vs2008', dest='vs2008', action='store_true',
		default=False,
		help='Build for Visual Studio 2008.')
	parser.add_argument('-vs2010', dest='vs2010', action='store_true',
		default=False,
		help='Build for Visual Studio 2010.')
	parser.add_argument('-vs2015', dest='vs2015', action='store_true',
		default=False,
		help='Build for Visual Studio 2015.')
	parser.add_argument('-codeblocks', dest='codeblocks', action='store_true',
		default=False,
		help='Build for CodeBlocks 13.12')
	parser.add_argument('-codewarrior', dest='codewarrior', action='store_true',
		default=False,
		help='Build for CodeWarrior')
	parser.add_argument('-watcom', dest='watcom', action='store_true',
		default=False,
		help='Build for Watcom WMAKE')
	parser.add_argument('-ios', dest='ios', action='store_true',
		default=False,
		help='Build for iOS with XCode 5 or higher.')
	parser.add_argument('-vita', dest='vita', action='store_true',
		default=False,
		help='Build for PS Vita with Visual Studio 2010.')
	parser.add_argument('-360', dest='xbox360', action='store_true',
		default=False,
		help='Build for XBox 360 with Visual Studio 2010.')
	parser.add_argument('-wiiu', dest='wiiu', action='store_true',
		default=False,
		help='Build for WiiU with Visual Studio 2013.')

	parser.add_argument('-release', dest='release', action='store_true',
		default=False,
		help='Create a release target (Default is release/debug/internal)')
	parser.add_argument('-debug', dest='debug', action='store_true',
		default=False,
		help='Create a debug target')
	parser.add_argument('-internal', dest='internal', action='store_true',
		default=False,
		help='Create an internal target')
	parser.add_argument('-finalfolder', dest='finalfolder', action='store_true',
		default=False,
		help='Add a script to copy a release build to a folder and check in with Perforce')
	parser.add_argument('-app', dest='app', action='store_true',
		default=False,
		help='Build an application instead of a tool')
	parser.add_argument('-lib', dest='library', action='store_true',
		default=False,
		help='Build a library instead of a tool')

	parser.add_argument('-f',dest='jsonfiles',action='append',
		help='Input file to process')
	parser.add_argument('-v','-verbose',dest='verbose',action='store_true',
		default=False,
		help='Verbose output.')
	parser.add_argument('-default',dest='default',action='store_true',
		help='Create a default projects.json file')
	parser.add_argument('args',nargs=argparse.REMAINDER,help='project filenames')

	args = parser.parse_args()
	verbose = args.verbose
	
	#
	# Shall a default file be generated?
	#
	
	if args.default==True:
		savedefault(os.path.join(workingDir,'projects.json'))
		return 0
		
	#
	# Process defaults first
	#

	solution = SolutionData()
	solution.verbose = verbose
	solution.workingDir = workingDir
	
	#
	# No input file?
	#
	
	if args.jsonfiles==None:
		projectpathname = os.path.join(workingDir,'projects.json')
		if len(sys.argv)==1 and os.path.isfile(projectpathname)==True:
			args.jsonfiles = ['projects.json']
		else:
			error = solution.processcommandline(args)
			return error
	
	#
	# Read in the json file
	#
	
	for input in args.jsonfiles:
		projectpathname = os.path.join(workingDir,input)
		if os.path.isfile(projectpathname)!=True:
			print input + ' was not found'
			return 2
	
		#
		# To allow '#' and '//' comments, the file has to be pre-processed
		#
		
		fp = open(projectpathname,'r')
		jsonlines = fp.readlines()
		fp.close()
		
		#
		# Remove all lines that have a leading '#' or '//'
		#
		
		pure = ''
		for item in jsonlines:
			cleanitem = item.lstrip()
			if cleanitem.startswith('#') or cleanitem.startswith('//'):
				# Insert an empty line so that line numbers still match on error
				pure = pure + '\n'
			else:
				pure = pure + item
			
		#
		# Parse the json file (Handle errors)
		#
		
		try:
			myjson = json.loads(pure)
		except Exception as e:
			print str(e) + ' in parsing ' + projectpathname
			return 2

		#
		# Process the list of commands
		#
	
		if type(myjson) is list:
			error = solution.process(myjson)
		else:
			print 'Invalid json input file!'
			error = 2
		if error!=0:
			break

	return error
