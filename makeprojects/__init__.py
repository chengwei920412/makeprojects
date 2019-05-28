#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Root namespace for the makeprojects tool

"""

#
## \package makeprojects
#
# Makeprojects is a set of functions to generate project files
# for the most popular IDEs and build systems. Included are
# tools to automate building, cleaning and rebuilding projects.
#

#
## \mainpage
#
# \htmlinclude README.html
#
# \par List of IDE classes
#
# \li \ref makeprojects
# \li \ref makeprojects.core
# \li \ref makeprojects.enums.FileTypes
# \li \ref makeprojects.SourceFile
# \li \ref makeprojects.core.Solution
# \li \ref makeprojects.core.Project
#
# \par List of sub packages
#
# \li \ref makeprojects.__pkginfo__
# \li \ref makeprojects.enums
# \li \ref makeprojects.visualstudio
# \li \ref makeprojects.xcode
# \li \ref makeprojects.codewarrior
# \li \ref makeprojects.codeblocks
# \li \ref makeprojects.watcom
#
# \par List of tool modules
#
# \li \ref makeprojects.buildme
# \li \ref makeprojects.cleanme
# \li \ref makeprojects.rebuildme
#
# To use in your own script:
#
# \code
# from makeprojects import *
#
# solution = newsolution(name='myproject')
# project = newproject(name='myproject')
# solution.add_project(project=project)
#
# project.addsourcefiles(os.path.join(os.getcwd(),'*.*'),recursive=True)
# solution.save(solution.xcode3)
#
# \endcode
#

from __future__ import absolute_import, print_function, unicode_literals

import os
from copy import deepcopy
from burger import convert_to_array, get_windows_host_type
from burger import convert_to_windows_slashes, convert_to_linux_slashes

from .__pkginfo__ import NUMVERSION, VERSION, AUTHOR, TITLE, SUMMARY, URI, EMAIL, LICENSE, COPYRIGHT
from .enums import AutoIntEnum, IDETypes, PlatformTypes, FileTypes, ProjectTypes

########################################

# pylint: disable=W0105

## Current version of the library as a numeric tuple
__numversion__ = NUMVERSION

## Current version of the library
__version__ = VERSION

## Author's name
__author__ = AUTHOR

## Name of the module
__title__ = TITLE

## Summary of the module's use
__summary__ = SUMMARY

## Home page
__uri__ = URI

## Email address for bug reports
__email__ = EMAIL

## Type of license used for distribution
__license__ = LICENSE

## Copyright owner
__copyright__ = COPYRIGHT

## Items to import on "from makeprojects import *"

__all__ = [
    'build',
    'clean',
    'rebuild',
    'new_solution',
    'new_project',
    'new_configuration',

    'FileTypes',
    'ProjectTypes',
    'IDETypes',
    'PlatformTypes',

    'SourceFile',
    'Property',
    'visualstudio',
    'watcom',
    'codeblocks',
    'codewarrior',
    'xcode',
    'makefile'
]

########################################


def build(working_directory=None, args=None):
    """
    Invoke the buildme command line from within Python

    Args:
        working_directory: Directory to process, ``None`` for current working directory
        args: Argument list to pass to the command, None uses sys.argv
    Returns:
        Zero on success, system error code on failure
    See Also:
        makeprojects.buildme
    """
    from .buildme import main
    return main(working_directory, args)

########################################


def clean(working_directory=None, args=None):
    """
    Invoke the cleanme command line from within Python

    Args:
        working_directory: Directory to process, ``None`` for current working directory
        args: Argument list to pass to the command, None uses sys.argv
    Returns:
        Zero on success, system error code on failure
    See Also:
        makeprojects.cleanme
    """

    from .cleanme import main
    return main(working_directory, args)

########################################


def rebuild(working_directory=None, args=None):
    """
    Invoke the rebuildme command line from within Python

    Args:
        working_directory: Directory to rebuild
        args: Command line to use instead of sys.argv
    Returns:
        Zero on no error, non-zero on error
    See Also:
        makeprojects.rebuildme, makeprojects.rebuildme.main
    """

    from .rebuildme import main
    return main(working_directory, args)

########################################


class Property(object):
    """
    Object for special properties

    For every configuration or source file, there are none
    or more properties that affect the generated project
    files either by object or globally
    """

    def __init__(self, configuration=None, platform=None, name=None, data=None):
        # Sanity check
        if name is None:
            raise TypeError("Property is missing a name")

        # Save the configuration this matches
        self.configuration = configuration
        # Save the platform type this matches
        self.platform = platform
        # Save the name of the property
        self.name = name
        # Save the data for the property
        self.data = data

    @staticmethod
    def find(entries, name=None, configuration=None, platform=None):
        """
        find
        """
        result = []
        for item in entries:
            if configuration is None or item.configuration is None or \
                    item.configuration == configuration:
                if platform is None or item.platform is None or \
                        item.platform.match(platform):
                    if name is None or item.name == name:
                        result.append(item)
        return result

    @staticmethod
    def getdata(entries, name=None, configuration=None, platform=None):
        """
        getdata
        """
        result = []
        for item in entries:
            if configuration is None or item.configuration is None or \
                    item.configuration == configuration:
                if platform is None or item.platform is None or \
                        item.platform.match(platform):
                    if name is None or item.name == name:
                        result.append(item.data)
        return result

    def __repr__(self):
        """
        Convert the property record into a human readable file description

        Returns:
            Human readable string or None if the record is invalid
        """

        return 'Configuration: {}, Platform: {}, Name: {}, Data: {}'.format(
            str(self.configuration),
            str(self.platform), self.name, self.data)

    __str__ = __repr__


class SourceFile():

    """
    Object for each input file to insert to a solution

    For every file that could be included into a project file
    one of these objects is created and attached to a solution object
    for processing
    """
    #

    #

    def __init__(self, relativepathname, directory, filetype):
        """
        Default constructor

        Args:
            self: The 'this' reference
            relativepathname: Filename of the input file (relative to the root)
            directory: Pathname of the root directory
            filetype: Compiler to apply
        See Also:
            _FILETYPES_LOOKUP
        """
        # Sanity check
        if not isinstance(filetype, FileTypes):
            raise TypeError("parameter 'filetype' must be of type FileTypes")

        ## File base name with extension using windows style slashes
        self.filename = convert_to_windows_slashes(relativepathname)

        ## Directory the file is found in (Full path)
        self.directory = directory

        ## File type enumeration, see: \ref enums.FileTypes
        self.type = filetype

    def extractgroupname(self):
        """
        Given a filename with a directory, remove the filename

        To determine if the file should be in a sub group in the project, scan
        the filename to find if it's a base filename or part of a directory
        If it's a basename, return an empty string.
        If it's in a folder, remove any ..\\ prefixes and .\\ prefixes
        and return the filename with the basename removed

        Args:
            self: The 'this' reference
        """

        slash = '\\'
        index = self.filename.rfind(slash)
        if index == -1:
            slash = '/'
            index = self.filename.rfind(slash)
            if index == -1:
                return ''

        #
        # Remove the basename
        #

        newname = self.filename[0:index]

        #
        # If there are ..\\ at the beginning, remove them
        #

        while newname.startswith('..' + slash):
            newname = newname[3:len(newname)]

        #
        # If there is a .\\, remove the single prefix
        #

        while newname.startswith('.' + slash):
            newname = newname[2:len(newname)]

        return newname

    def getabspath(self):
        """
        Return the full pathname of the file entry

        Returns:
            Absolute pathname for the file
        """

        if get_windows_host_type():
            filename = self.filename
        else:
            filename = convert_to_linux_slashes(self.filename)
        return os.path.abspath(os.path.join(self.directory, filename))

    def __repr__(self):
        """
        Convert the file record into a human readable file description

        Returns:
            Human readable string or None if the enumeration is invalid
        See Also:
            makeprojects.enums._PROJECTTYPES_READABLE
        """

        return 'Type: {} Name: "{}"'.format(str(self.type),
                                            self.getabspath())

    __str__ = __repr__

########################################


def new_solution(name=None, working_directory=None, verbose=False, ide=None, perforce=True):
    """
    Create a new instance of a core.Solution

    Convenience routine to create a core.Solution instance.

    Args:
        name: Name of the project
        working_directory: Directory to store the solution.
        verbose: If True, verbose output.
        ide: IDE to build for.
    See Also:
        core.Solution
    """

    from .core import Solution
    return Solution(name=name, working_directory=working_directory, verbose=verbose, ide=ide, perforce=True)

########################################


def new_project(name=None, working_directory=None, project_type=None, platform=None):
    """
    Create a new instance of a core.Project

    Convenience routine to create a core.Project instance.

    Args:
        kargs: Keyword args
    See Also:
        core.Project
    """

    from .core import Project
    return Project(name=name, working_directory=working_directory,
                   project_type=project_type, platform=platform)

########################################


def new_configuration(name, platform=None, project_type=None):
    """
    Create a new instance of a core.Configuration

    Convenience routine to create a core.Configuration instance.

    Args:
        kargs: Keyword args
    See Also:
        core.Configuration
    """

    from .core import Configuration

    results = []
    name_array = convert_to_array(name)
    for name in name_array:

        # Special case, if the platform is an expandable, convert to an array
        # of configurations that fit the bill.
        if platform:
            platform_type = PlatformTypes.lookup(platform)
            if platform_type is None:
                raise TypeError("parameter 'platform_type' must be of type PlatformTypes")
            for item in platform_type.get_expanded():
                results.append(Configuration(name, item, project_type))
        else:
            results.append(Configuration(name, platform, project_type))

    # If a single object, pass back as is.
    if len(results) == 1:
        return results[0]
    return results
