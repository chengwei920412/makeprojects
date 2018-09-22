#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains the code for the command line "buildme"
"""

## \package makeprojects.buildme

from __future__ import absolute_import, print_function, unicode_literals

import os
import sys
import argparse
import subprocess
import struct
import burger

from .__pkginfo__ import VERSION

## List of watcom platforms to build
WATCOM_PLATFORM_LIST = [
	'dos4gw',
	'dosx32',
	'win32'
]

## List of default configurations to build

DEFAULT_CONFIGURATION_LIST = [
	'Debug',
	'Internal',
	'Release'
]

CODEWARRIOR_ERRORS = (
	None,
	'error opening file',
	'project not open',
	'IDE is already building',
	'invalid target name (for /t flag)',
	'error changing current target',
	'error removing objects',
	'build was cancelled',
	'build failed',
	'process aborted',
	'error importing project',
	'error executing debug script',
	'attempted use of /d together with /b and/or /r'
)

########################################


class BuildError(object):
	"""
	Error message generated by builders
	"""
	def __init__(self, error, filename, configuration=None, msg=None):
		"""
		Initializers for an BuildError

		Args:
			error: Integer error code, zero if not error
			filename: File that generated the error
			configuration: If applicable, configuration that was compiled
			msg: Error message test, if available

		"""

		## Integer error code
		self.error = error

		## File name that generated the error
		self.filename = filename

		## Build configuration
		self.configuration = configuration

		## Error message
		self.msg = msg

	def __repr__(self):
		"""
		Convert the error into a string

		Returns:
			A full error string
		"""

		if self.error:
			result = 'Error #{} in file {}'.format(self.error, self.filename)
		else:
			result = 'No error in file {}'.format(self.filename)
		if self.configuration:
			result += ' Configuration "{}"'.format(self.configuration)
		if self.msg:
			result += ' "{}"'.format(self.msg)
		return result

	__str__ = __repr__

########################################


def build_rez_script(full_pathname, verbose=False):
	"""
	Build a rezfile using 'makerez'

	Execute the program 'makerez' to build the script.

	Args:
		full_pathname: Pathname to the *.rezscript to build
		verbose: True if verbose output
	Returns:
		BuildError object
	"""

	# Create the build command
	cmd = ['makerez', full_pathname]
	if verbose:
		# Have makerez be verbose
		cmd.insert(1, '-v')
		print(' '.join(cmd))

	# Perform the command
	try:
		error_code = subprocess.call(cmd, cwd=os.path.dirname(full_pathname))
		msg = None
	except OSError as error:
		error_code = getattr(error, 'winerror', error.errno)
		msg = str(error)
		print(msg, file=sys.stderr)

	# Return the results
	return BuildError(error_code, full_pathname, msg=msg)

########################################


def build_slicer_script(full_pathname, verbose=False):
	"""
	Build slicer data

	Args:
		full_pathname: Pathname to the *.slicer to build
		verbose: True if verbose output
	Returns:
		BuildError object
	"""

	# Create the build command
	cmd = ['slicer', full_pathname]
	if verbose:
		print(' '.join(cmd))

	# Perform the command
	try:
		error_code = subprocess.call(cmd, cwd=os.path.dirname(full_pathname))
		msg = None
	except OSError as error:
		error_code = getattr(error, 'winerror', error.errno)
		msg = str(error)
		print(msg, file=sys.stderr)

	# Return the results
	return BuildError(error_code, full_pathname, msg=msg)


########################################


def build_doxygen(full_pathname, verbose=False):
	"""
	Build Doxygen docs

	Args:
		full_pathname: Pathname to the doxygen config file
		verbose: True for verbose output
	Returns:
		BuildError object
	"""

	# Is Doxygen installed?

	doxygenpath = burger.where_is_doxygen(verbose=verbose)
	if doxygenpath is None:
		error_code = 10
		msg = '{} requires Doxygen to be installed to build!'.format(full_pathname)
	else:

		# Determine the working directory
		full_pathname = os.path.abspath(full_pathname)
		doxyfile_dir = os.path.dirname(full_pathname)

		# Make the output folder for errors (If needed)
		temp_dir = os.path.join(doxyfile_dir, 'temp')
		burger.create_folder_if_needed(temp_dir)

		# The macOS/Linux version will die if the text file isn't Linux
		# format, copy the config file with the proper line feeds
		if burger.get_windows_host_type() is False:
			doxyfile_data = burger.load_text_file(full_pathname)
			temp_doxyfile = full_pathname + '.tmp'
			burger.save_text_file(temp_doxyfile, doxyfile_data, line_feed='\n')
		else:
			temp_doxyfile = full_pathname

		# Create the build command
		cmd = [doxygenpath, burger.encapsulate_path(temp_doxyfile)]
		if verbose:
			print(' '.join(cmd))

		# Capture the error output
		stderr = burger.run_command(cmd, working_dir=doxyfile_dir, \
			quiet=not verbose, capture_stderr=True)[2]

		# If there was a temp doxyfile, get rid of it.
		if temp_doxyfile != full_pathname:
			burger.delete_file(temp_doxyfile)

		# Location of the log file
		log_filename = os.path.join(temp_dir, 'doxygenerrors.txt')

		# If the error log has something, save it.
		if stderr:
			burger.save_text_file(log_filename, stderr.splitlines())
			error_code = 10
			msg = 'Errors stored in {}'.format(log_filename)
		else:
			# Make sure it's gone since there's no errors
			burger.delete_file(log_filename)
			error_code = 0
			msg = None

	# Return the results
	return BuildError(error_code, full_pathname, msg=msg)

########################################


def build_watcom_makefile(full_pathname, verbose=False, fatal=False):
	"""
	Build Watcom MakeFile

	Args:
		full_pathname: Pathname to the doxygen config file
		verbose: True for verbose output
		fatal: If True, abort on the first failed build
	Returns:
		List of BuildError objects
	"""

	# Is Watcom installed?
	watcom_path = burger.where_is_watcom(verbose=verbose)
	if watcom_path is None:
		return BuildError(10, full_pathname, \
				msg=full_pathname + ' requires Watcom to be installed to build!')

	# Watcom requires the path set up so it can access link files
	saved_path = os.environ['PATH']
	if burger.get_windows_host_type():
		new_path = os.path.join(watcom_path, 'binnt') + os.pathsep + \
			os.path.join(watcom_path, 'binw')
		exe_name = 'binnt\\wmake.exe'
	else:
		new_path = os.path.join(watcom_path, 'binl')
		exe_name = 'binl/wmake'
	os.environ['PATH'] = new_path + os.pathsep + saved_path

	commands = []
	# New format has an 'all' target
	if full_pathname.lower().endswith('.wmk'):
		commands.append(([os.path.join(watcom_path, exe_name), '-e', \
			'-h', '-f', burger.encapsulate_path(full_pathname), 'all'], 'all'))
	else:
		for platform in WATCOM_PLATFORM_LIST:
			for target in DEFAULT_CONFIGURATION_LIST:
				commands.append(([os.path.join(watcom_path, exe_name), '-e', \
					'-h', '-f', burger.encapsulate_path(full_pathname), \
					'Target=' + target, 'Platform=' + platform], \
					platform + '|' + target))

	# Iterate over the commands
	results = []
	for cmd in commands:
		if verbose:
			print(' '.join(cmd[0]))
		# Perform the command
		try:
			error_code = subprocess.call(cmd[0], cwd=os.path.dirname(full_pathname), \
				shell=True)
			msg = None
		except OSError as error:
			error_code = getattr(error, 'winerror', error.errno)
			msg = str(error)
			print(msg, file=sys.stderr)
		results.append(BuildError(error_code, full_pathname, configuration=cmd[1], \
			msg=msg))
		if error_code and fatal:
			break

	# Restore the path variable
	os.environ['PATH'] = saved_path

	# Return the error code
	return results

########################################


def parse_sln_file(full_pathname):
	"""
	Find build targets in .sln file.

	Given a .sln file for Visual Studio 2003, 2005, 2008, 2010,
	2012, 2013, 2015 or 2017 locate and extract all of the build
	targets available and return the list.

	It will also determine which version of Visual
	Studio this solution file requires

	Args:
		full_pathname: Pathname to the .sln file
	Returns:
		tuple(list of configuration strings, integer Visual Studio version year)
	"""

	# Load in the .sln file, it's a text file
	file_lines = burger.load_text_file(full_pathname)

	# Version not known yet
	vs_version = 0

	# Start with an empty list
	target_list = []

	if file_lines:
		# Not looking for 'Visual Studio'
		looking_for_visual_studio = False

		# Not looking for EndGlobalSection
		looking_for_end_global_section = False

		# Parse
		for line in file_lines:

			# Scanning for 'EndGlobalSection'?

			if looking_for_end_global_section:

				# Once the end of the section is reached, end
				if 'EndGlobalSection' in line:
					looking_for_end_global_section = False
					continue

				# The line contains 'Debug|Win32 = Debug|Win32'
				# Split it in half at the equals sign and then
				# remove the whitespace and add to the list
				lineparts = line.split('=')
				target_list.append(lineparts[0].strip())
				continue

			# Scanning for the secondary version number in Visual Studio 2012 or higher

			if looking_for_visual_studio and '# Visual Studio' in line:
				# The line contains '# Visual Studio 15'

				# Parse the number
				versionstring = line.rsplit()[-1]

				# Use the version number to determine which visual studio to launch
				if versionstring == '2012':
					vs_version = 2012
				elif versionstring == '2013':
					vs_version = 2013
				elif versionstring == '14':
					vs_version = 2015
				elif versionstring == '15':
					vs_version = 2017
				looking_for_visual_studio = False
				continue

			# Get the version number
			if 'Microsoft Visual Studio Solution File' in line:
				# The line contains
				# 'Microsoft Visual Studio Solution File, Format Version 12.00'
				# The number is in the last part of the line
				versionstring = line.split()[-1]

				# Use the version string to determine which visual studio to launch
				if versionstring == '8.00':
					vs_version = 2003
				elif versionstring == '9.00':
					vs_version = 2005
				elif versionstring == '10.00':
					vs_version = 2008
				elif versionstring == '11.00':
					vs_version = 2010
				elif versionstring == '12.00':
					# 2012 or higher requires a second check
					vs_version = 2012
					looking_for_visual_studio = True
				continue

			# Look for this section, it contains the configurations
			if 'GlobalSection(SolutionConfigurationPlatforms)' in line:
				looking_for_end_global_section = True

	# Exit with the results
	if not vs_version:
		print('The visual studio solution file {} ' \
			'is corrupt or an unknown version!'.format(full_pathname), file=sys.stderr)
	return (target_list, vs_version)

########################################


def build_visual_studio(full_pathname, verbose=False, fatal=False):
	"""
	Build a visual studio .sln file

	Args:
		full_pathname: Pathname to the Visual Studio .sln file
		verbose: True for verbose output
		fatal: If True, abort on the first failed build
	Returns:
		List of BuildError objects
	"""

	# Get the list of build targets
	targetlist, vs_version = parse_sln_file(full_pathname)

	# Was the file corrupted?
	if not vs_version:
		return BuildError(10, full_pathname, msg=full_pathname + ' is corrupt!')

	# Locate the proper version of Visual Studio for this .sln file
	vstudioenv = None
	if vs_version == 2003:
		# Is Visual studio 2003 installed?
		vstudioenv = 'VS71COMNTOOLS'
	elif vs_version == 2005:
		# Is Visual studio 2005 installed?
		vstudioenv = 'VS80COMNTOOLS'
	elif vs_version == 2008:
		# Is Visual studio 2008 installed?
		vstudioenv = 'VS90COMNTOOLS'
	elif vs_version == 2010:
		# Is Visual studio 2010 installed?
		vstudioenv = 'VS100COMNTOOLS'
	elif vs_version == 2012:
		# Is Visual studio 2012 installed?
		vstudioenv = 'VS110COMNTOOLS'
	elif vs_version == 2013:
		# Is Visual studio 2013 installed?
		vstudioenv = 'VS120COMNTOOLS'
	elif vs_version == 2015:
		# Is Visual studio 2015 installed?
		vstudioenv = 'VS140COMNTOOLS'
	elif vs_version == 2017:
		# Is Visual studio 2017 installed?
		vstudioenv = 'VS150COMNTOOLS'
	else:
		msg = '{} requires Visual Studio version {} which is unsupported!'.format( \
			full_pathname, vs_version)
		print(msg, file=sys.stderr)
		return BuildError(0, full_pathname, msg=msg)

	# Is Visual studio installed?
	vstudiopath = os.getenv(vstudioenv, default=None)
	if vstudiopath is None:
		msg = '{} requires Visual Studio version {} to be installed ' \
			'to build!'.format(full_pathname, vs_version)
		print(msg, file=sys.stderr)
		return BuildError(0, full_pathname, msg=msg)

	# Locate the launcher
	vstudiopath = os.path.abspath(vstudiopath + r'\..\ide\devenv.com')

	# Build each and every target
	xboxfail = False
	xbox360fail = False
	xboxonefail = False
	ps3fail = False
	ps4fail = False
	vitafail = False
	shieldfail = False
	androidfail = False
	results = []
	for target in targetlist:

		# Certain targets require an installed SDK
		# verify that the SDK is installed before trying to build

		targettypes = target.rsplit('|')

		# Sony platforms
		if targettypes[1] == 'PS3':
			if os.getenv('SCE_PS3_ROOT', default=None) is None:
				ps3fail = True
				continue
		if targettypes[1] == 'ORBIS':
			if os.getenv('SCE_ORBIS_SDK_DIR', default=None) is None:
				ps4fail = True
				continue
		if targettypes[1] == 'PSVita':
			if os.getenv('SCE_PSP2_SDK_DIR', default=None) is None:
				vitafail = True
				continue

		# Microsoft platforms
		if targettypes[1] == 'Xbox':
			if os.getenv('XDK', default=None) is None:
				xboxfail = True
				continue
		if targettypes[1] == 'Xbox 360':
			if os.getenv('XEDK', default=None) is None:
				xbox360fail = True
				continue
		if targettypes[1] == 'Xbox ONE':
			if os.getenv('DurangoXDK', default=None) is None:
				xboxonefail = True
				continue

		# Android
		if targettypes[1] == 'Android':
			if os.getenv('ANDROID_NDK', default=None) is None:
				androidfail = True
				continue

		# nVidia Shield
		if targettypes[1] == 'Tegra-Android':
			if os.getenv('NV', default=None) is None:
				shieldfail = True
				continue

		# Create the build command
		# Note: Use the single line form, because Windows will not
		# process the target properly due to the presence of the | character
		# which causes piping.
		cmd = '{} {} /Build {}'.format(burger.encapsulate_path(vstudiopath), \
			burger.encapsulate_path(full_pathname), burger.encapsulate_path(target))
		if verbose:
			print(cmd)
		sys.stdout.flush()
		error = subprocess.call(cmd, cwd=os.path.dirname(full_pathname), shell=True)
		results.append(BuildError(error, full_pathname, configuration=target))
		if error and fatal:
			break

	if xboxfail:
		print('Xbox classic project detected but XDK was not installed', \
			file=sys.stderr)
	if xbox360fail:
		print('Xbox 360 project detected but XEDK was not installed', \
			file=sys.stderr)
	if xboxonefail:
		print('Xbox ONE project detected but DurangoXDK was not installed', \
			file=sys.stderr)

	if ps3fail:
		print('PS3 project detected but SCE_PS3_ROOT was not found', \
			file=sys.stderr)
	if ps4fail:
		print('PS4 project detected but SCE_ORBIS_SDK_DIR was not found', \
			file=sys.stderr)
	if vitafail:
		print('PS Vita project detected but SCE_PSP2_SDK_DIR was not found', \
			file=sys.stderr)

	if shieldfail:
		print('nVidia Shield project detected but NV was not found', \
			file=sys.stderr)

	if androidfail:
		print('Android project detected but ANDROID_NDK was not found', \
			file=sys.stderr)

	return results

########################################


def parse_mcp_file(full_pathname):
	"""
	Detect Codewarrior version

	Given an .mcp file for Metrowerks Codewarrior, determine
	which version of Codewarrrior was used to build it.

	It will parse Freescale Codewarrior for Nintendo (59), Metrowerks
	Codewarrior 9.0 for Windows (50) and Metrowerks Codewarrior 10.0
	for macOS (58)

	Args:
		full_pathname: Pathname to the .mcp file
	Returns:
		tuple(list of configuration strings, integer CodeWarrior Version)
	"""

	# Handle ../../
	full_pathname = os.path.abspath(full_pathname)

	try:
		# Load in the .mcp file, it's a binary file
		with open(full_pathname, 'rb') as filep:

			# Get the signature and the endian
			cool = filep.read(4)
			if cool == 'cool':
				# Big endian
				endian = '>'
			elif cool == 'looc':
				# Little endian
				endian = '<'
			else:
				print('Codewarrior "cool" signature not found!', file=sys.stderr)
				return None, None, None

			# Get the offset to the strings
			filep.seek(16)
			index_offset = struct.unpack(endian + 'I', filep.read(4))[0]
			filep.seek(index_offset)
			string_offset = struct.unpack(endian + 'I', filep.read(4))[0]

			# Read in the version
			filep.seek(28)
			cw_version = bytearray(filep.read(4))

			# Load the string 'CodeWarrior Project'
			filep.seek(40)
			if filep.read(19) != 'CodeWarrior Project':
				print('"Codewarrior Project" signature not found!', file=sys.stderr)
				return None, None, None

			# Read in the strings for the targets
			filep.seek(string_offset)
			targets = []
			linkers = []
			# Scan for known linkers
			while True:
				item = burger.read_zero_terminated_string(filep)
				if not item:
					break

				# Only strings with a colon are parsed
				parts = item.split(':')
				if len(parts) == 2:
					# Target:panel
					target = parts[0]
					panel = parts[1]

					# Add the target
					if target not in targets:
						targets.append(target)

					# Add the linker
					if panel == 'MW ARM Linker Panel' or \
						panel == 'x86 Linker' or \
						panel == 'PPC Linker' or \
						panel == '68K Linker':
						if panel not in linkers:
							linkers.append(panel)

			return targets, linkers, cw_version

	except IOError as error:
		print(str(error), file=sys.stderr)

	return None, None, None

########################################


def build_codewarrior(full_pathname, verbose=False, fatal=False):
	"""
	Build a Metrowerks Codewarrior file

	Return 0 if no error, 1 if an error, 2 if
	Code Warrior was not found
	"""

	# Test for older macOS or Windows
	if burger.get_mac_host_type():
		if not burger.is_codewarrior_mac_allowed():
			return BuildError(0, full_pathname, \
				msg='Codewarrior is not compatible with this version of macOS')
	elif not burger.get_windows_host_type():
		return BuildError(0, full_pathname, \
			msg='Codewarrior is not compatible with this operating system')

	# Handle ../../
	full_pathname = os.path.abspath(full_pathname)
	targets, linkers, _ = parse_mcp_file(full_pathname)
	if targets is None:
		return BuildError(0, full_pathname, msg='File corrupt')

	if burger.get_windows_host_type():
		if '68K Linker' in linkers:
			return BuildError(0, full_pathname, \
					msg="Requires a 68k linker which Windows doesn't support.")
		if 'PPC Linker' in linkers:
			return BuildError(0, full_pathname, \
					msg="Requires a PowerPC linker which Windows doesn't support.")

		cw_path = None
		if 'MW ARM Linker Panel' in linkers:
			cw_path = os.getenv('CWFOLDER_NITRO', default=None)
			if cw_path is None:
				cw_path = os.getenv('CWFOLDER_TWL', default=None)
		elif 'x86 Linker' in linkers:
			cw_path = os.getenv('CWFolder', default=None)

		if cw_path is None:
			return BuildError(0, full_pathname, \
				msg="CodeWarrior is not installed.")

		# Note: CmdIDE is preferred, however, Codewarrior 9.4 has a bug
		# that it will die horribly if the pathname to it
		# has a space, so ide is used instead.
		cwfile = os.path.join(cw_path, 'Bin', 'IDE.exe')
	else:
		# Handle mac version
		cwfile = None
		if 'x86 Linker' in linkers:
			cwfile = '/Applications/Metrowerks CodeWarrior 9.0/' + \
				'Metrowerks CodeWarrior/CodeWarrior IDE'
			if not os.path.isfile(cwfile):
				cwfile = '/Applications/Metrowerks CodeWarrior 9.0/' + \
					'Metrowerks CodeWarrior/CodeWarrior IDE 9.6'
		elif any(i in ('68K Linker', 'PPC Linker') for i in linkers):
			cwfile = '/Applications/Metrowerks CodeWarrior 10.0/' + \
				'Metrowerks CodeWarrior/CodeWarrior IDE'
			if not os.path.isfile(cwfile):
				cwfile = '/Applications/Metrowerks CodeWarrior 10.0/' + \
					'Metrowerks CodeWarrior/CodeWarrior IDE 10'
		if cwfile is None:
			return BuildError(0, full_pathname, \
					"CodeWarrior with proper linker is not installed.")

	# If there's an "Uber" target, just use that
	if 'Everything' in targets:
		targets = ['Everything']

	mytempdir = os.path.join(os.path.dirname(full_pathname), 'temp')
	burger.create_folder_if_needed(mytempdir)

	results = []
	for target in targets:
		if burger.get_windows_host_type():
			# Create the build command
			# /s New instance
			# /t Project name
			# /b Build
			# /c close the project after completion
			# /q Close Codewarrior on completion
			cmd = [cwfile, full_pathname, '/t', target, '/s', '/c', '/q', '/b']
		else:
			# Create the folder for the error log
			error_file = os.path.basename(full_pathname)
			error_list = os.path.splitext(error_file)
			error_file = os.path.join(mytempdir, '{}-{}.err'.format( \
				error_list[0], target))
			cmd = ['cmdide', '-proj', '-bcwef', error_file, \
				'-y', cwfile, '-z', target, full_pathname]

		if verbose:
			print(' '.join(cmd))
		sys.stdout.flush()
		error = subprocess.call(cmd, cwd=os.path.dirname(full_pathname))
		msg = None
		if error and error < len(CODEWARRIOR_ERRORS):
			msg = CODEWARRIOR_ERRORS[error]
		results.append(BuildError(error, full_pathname, configuration=target, \
			msg=msg))
		if error and fatal:
			break

	return results

########################################


def parsexcodeprojdir(file_name):
	"""
	Given a .xcodeproj directory for XCode for MacOSX
	locate and extract all of the build targets
	available and return the list
	"""

	# Start with an empty list

	targetlist = []
	filep = open(os.path.join(file_name, 'project.pbxproj'))
	projectfile = filep.read().splitlines()
	filep.close()
	configurationfound = False
	for line in projectfile:
		# Look for this section. Immediately after it
		# has the targets
		if configurationfound is False:
			if 'buildConfigurations' in line:
				configurationfound = True
		else:
			# Once the end of the section is reached, end
			if ');' in line:
				break
			# Format 1DEB923608733DC60010E9CD /* Debug */,
			lineparts = line.rsplit()
			# The third entry is the data needed
			targetlist.append(lineparts[2])

	# Exit with the results
	return targetlist

########################################


def buildxcode(file_name, verbose, ignoreerrors):
	"""
	Build a Mac OS X XCode file
	Return 0 if no error, 1 if an error, 2 if
	XCode was not found
	"""

	# Get the list of build targets
	targetlist = parsexcodeprojdir(file_name)
	file_name_lower = file_name.lower()
	# Use XCode 3 off the root
	if 'xc3' in file_name_lower:
		# On OSX Lion and higher, XCode 3.1.4 is a separate folder
		xcodebuild = '/Xcode3.1.4/usr/bin/xcodebuild'
		if not os.path.isfile(xcodebuild):
			# Use the pre-Lion folder
			xcodebuild = '/Developer/usr/bin/xcodebuild'
	# Invoke XCode 4 or higher from the app store
	else:
		xcodebuild = '/Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild'

	# Is this version of XCode installed?
	if os.path.isfile(xcodebuild) is not True:
		print('Can\'t build ' + file_name + \
			', the proper version of XCode is not installed')
		return BuildError(0, file_name, msg='Proper version of XCode not found')

	# Build each and every target
	results = []
	for target in targetlist:
		# Create the build command
		cmd = xcodebuild + ' -project "' + os.path.basename(file_name) + \
			'" -alltargets -parallelizeTargets -configuration "' + target + '"'
		if verbose:
			print(cmd)
		sys.stdout.flush()
		error = subprocess.call(cmd, cwd=os.path.dirname(file_name), shell=True)
		results.append(BuildError(error, file_name, configuration=target))
		if error:
			if not ignoreerrors:
				break

	return results

########################################


def buildcodeblocks(fullpathname, verbose):
	"""
	Build a Codeblocks project

	Commands available as of 13.12
	--safe-mode
	--no-check-associations
	--no-dde
	--no-splash-screen
	--multiple-instance
	--debug-log
	--no-crash-handler
	--verbose
	--no-log
	--log-to-file
	--debug-log-to-file
	--rebuild
	--build
	--clean
	--target=
	--no-batch-window-close
	--batch-build-notify
	--script=
	--file=
	"""

	if burger.get_windows_host_type():
		if fullpathname.endswith('osx.cbp'):
			return BuildError(0, fullpathname, msg="Can only be built on macOS")
		# Is Codeblocks installed?
		codeblockspath = os.getenv('CODEBLOCKS')
		if codeblockspath is None:
			return BuildError(0, fullpathname, \
				msg='Requires Codeblocks to be installed to build!')
		codeblockspath = os.path.join(codeblockspath, 'codeblocks')
		codeblocksflags = '--no-check-associations --no-dde --no-batch-window-close'
	else:
		if not fullpathname.endswith('osx.cbp'):
			return BuildError(0, fullpathname, msg="Can not be built on macOS")

		codeblockspath = '/Applications/Codeblocks.app/Contents/MacOS/CodeBlocks'
		codeblocksflags = '--no-ipc'
	# Create the build command
	cmd = '"' + codeblockspath + '" ' + codeblocksflags + \
		' --no-splash-screen --build "' + \
		fullpathname + '" --target=Everything'
	if verbose:
		print(cmd)
	print(cmd)
	# error = subprocess.call(cmd, cwd=os.path.dirname(fullpathname), shell=True)
	return BuildError(0, fullpathname, \
		msg='Codeblocks is currently broken. Disabled for now')

########################################


def addproject(projects, file_name):

	"""
	Detect the project type and add it to the list
	"""
	# Only process project files

	base_name = os.path.basename(file_name)
	base_name_lower = base_name.lower()
	projecttype = None
	priority = 50
	if base_name_lower == 'prebuild.py':
		projecttype = 'python'
		priority = 1
	elif base_name_lower.endswith('.slicerscript'):
		projecttype = 'slicer'
		priority = 20
	elif base_name_lower.endswith('.rezscript'):
		projecttype = 'makerez'
		priority = 25
	elif base_name_lower == 'custombuild.py':
		projecttype = 'python'
		priority = 40
	elif base_name_lower.endswith('.sln'):
		projecttype = 'visualstudio'
		priority = 45
	elif base_name_lower.endswith('.mcp'):
		projecttype = 'codewarrior'
	elif base_name_lower == 'makefile' or base_name_lower.endswith('.wmk'):
		projecttype = 'watcommakefile'
	elif base_name_lower.endswith('.xcodeproj'):
		projecttype = 'xcode'
	elif base_name_lower.endswith('.cbp'):
		projecttype = 'codeblocks'
	elif base_name_lower == 'doxyfile':
		projecttype = 'doxygen'
		priority = 90
	elif base_name_lower == 'postbuild.py':
		projecttype = 'python'
		priority = 99

	if projecttype:
		projects.append((file_name, projecttype, priority))
		return True
	return False

########################################


def getprojects(projects, working_dir):
	"""
	Scan a folder for files that need to be 'built'
	"""

	# Get the list of files in this directory
	try:
		for base_name in os.listdir(working_dir):
			file_name = os.path.join(working_dir, base_name)
			addproject(projects, file_name)
	except OSError as error:
		print(error)

########################################


def recursivegetprojects(projects, working_dir):
	"""
	Recursively scan a folder and look for any project files than need to
	be built. Returns all files in the list "projects"
	"""
	# Iterate through this folder and build the contents

	getprojects(projects, working_dir)

	for base_name in os.listdir(working_dir):
		base_name_lower = base_name.lower()

		# Skip known folders that contain temp files and not potential projects
		if base_name_lower == 'temp':
			continue
		if base_name_lower == 'bin':
			continue
		if base_name_lower == 'appfolder':
			continue
		# Xcode folders don't have subprojects inside
		if base_name_lower.endswith('.xcodeproj'):
			continue
		# Codewarrior droppings (Case sensitive)
		if base_name.endswith('_Data'):
			continue
		if base_name.endswith(' Data'):
			continue
		file_name = os.path.join(working_dir, base_name)

		# Handle the directories found
		if os.path.isdir(file_name):
			recursivegetprojects(projects, file_name)

########################################


def main(working_dir=None, args=None):
	"""
	Command line shell for buildme

	Args:
		working_dir: Directory to operate on, or None for os.getcwd()
		args: Command line to use instead of sys.argv
	Returns:
		Zero
	"""

	# Make sure working_dir is properly set
	if working_dir is None:
		working_dir = os.getcwd()

	# Parse the command line
	parser = argparse.ArgumentParser( \
		description='Build project files. Copyright by Rebecca Ann Heineman. ' \
		'Builds *.sln, *.mcp, *.cbp, *.rezscript, *.slicerscript, doxyfile, ' \
		'makefile and *.xcodeproj files')

	parser.add_argument('--version', action='version', \
		version='%(prog)s ' + VERSION)
	parser.add_argument('-r', '-all', dest='recursive', action='store_true', \
		default=False, help='Perform a recursive build')
	parser.add_argument('-v', '-verbose', dest='verbose', action='store_true', \
		default=False, help='Verbose output.')
	parser.add_argument('--generate-rcfile', dest='generate_rc', \
		action='store_true', default=False, \
		help='Generate a sample configuration file and exit.')
	parser.add_argument('--rcfile', dest='rcfile', \
		metavar='<file>', default=None, help='Specify a configuration file.')

	parser.add_argument('-f', dest='fatal', action='store_true', \
		default=False, help='Quit immediately on any error.')
	parser.add_argument('-d', dest='directories', action='append', \
		help='List of directories to build in.')
	parser.add_argument('-docs', dest='documentation', action='store_true', \
		default=False, help='Compile Doxyfile files.')
	parser.add_argument('args', nargs=argparse.REMAINDER, \
		help='project filenames')

	# Parse everything
	args = parser.parse_args(args=args)

	# Output default configuration
	if args.generate_rc:
		from .config import savedefault
		savedefault(working_dir)
		return 0

	verbose = args.verbose

	#
	# List of files to build
	#

	projects = []

	#
	# Get the list of directories to process
	#

	directories = args.directories
	if not directories:
		# Use the current working directory instead
		directories = [working_dir]
		if not args.recursive:

			#
			# If any filenames were passed, add them to the possible projects list
			#

			if args.args:
				for file_name in args.args:
					projectname = os.path.join(working_dir, file_name)
					if addproject(projects, os.path.join(working_dir, projectname)) is False:
						print('Error: ' + projectname + ' is not a known project file')
						return 10

	#
	# Create the list of projects that need to be built
	#

	if not projects:
		for my_dir_name in directories:
			if not args.recursive:
				getprojects(projects, my_dir_name)
			else:
				recursivegetprojects(projects, my_dir_name)

	#
	# If the list is empty, just exit now
	#

	if not projects:
		print('Nothing to build')
		return 0

	#
	# Sort the list by priority (The third parameter is priority from 1-99
	#
	projects = sorted(projects, key=lambda entry: entry[2])

	#
	# Let's process each and every file
	#

	#
	# args.documentation exists because building Doxygen files
	# are very time consuming
	#

	results = []
	for project in projects:
		fullpathname = project[0]
		projecttype = project[1]
		berror = None

		# Is it a python script?
		if projecttype == 'python':
			if verbose:
				print('Invoking ' + fullpathname)
			error = burger.run_py_script(fullpathname, 'main', \
				os.path.dirname(fullpathname))
			berror = BuildError(error, fullpathname)

		# Is it a slicer script?
		elif projecttype == 'slicer':
			berror = build_slicer_script(fullpathname, verbose=verbose)

		# Is it a makerez script?
		elif projecttype == 'makerez':
			berror = build_rez_script(fullpathname, verbose=verbose)

		# Is this a doxygen file?
		elif projecttype == 'doxygen':
			if args.documentation:
				berror = build_doxygen(fullpathname, verbose=verbose)

		# Is this a Watcom Makefile?
		elif projecttype == 'watcommakefile':
			berror = build_watcom_makefile(fullpathname, verbose=verbose, \
				fatal=args.fatal)

		# Visual studio solution files?
		elif projecttype == 'visualstudio':
			if burger.get_windows_host_type():
				berror = build_visual_studio(fullpathname, verbose=verbose, \
					fatal=args.fatal)

		# Metrowerks Codewarrior files?
		elif projecttype == 'codewarrior':
			berror = build_codewarrior(fullpathname, verbose=verbose, fatal=args.fatal)

		# XCode project file?
		elif projecttype == 'xcode':
			if burger.get_mac_host_type():
				berror = buildxcode(fullpathname, verbose=verbose, ignoreerrors=True)

		# Codeblocks project file?
		elif projecttype == 'codeblocks':
			berror = buildcodeblocks(fullpathname, verbose=verbose)

		error = 0
		if berror is not None:
			if isinstance(berror, BuildError):
				results.append(berror)
				error = berror.error
			else:
				results.extend(berror)
				for i in berror:
					if i.error:
						error = i.error
						break

		# Abort on error?
		if error and args.fatal:
			break

	# List all the projects that failed

	for item in results:
		if item.error:
			print('Errors detected in the build.', file=sys.stderr)
			error = 10
			break
	else:
		if verbose:
			print('Build successful!')
		error = 0

	# Dump the error log
	if verbose or error:
		for entry in results:
			if verbose or entry.error:
				print(entry)
	return error


# If called as a function and not a class,
# call my main

if __name__ == "__main__":
	sys.exit(main())
