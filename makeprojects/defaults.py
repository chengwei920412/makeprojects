#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains the code to generate defaults.
"""

## \package makeprojects.defaults

from __future__ import absolute_import, print_function, unicode_literals

import os
from burger import convert_to_array

from .enums import IDETypes, PlatformTypes, ProjectTypes

########################################


def get_project_name(build_rules_list, working_directory, args):
    """
    Determine the project name.

    Scan the build_rules.py file for the command 'default_project_name'
    and if found, use that string for the project name. Otherwise,
    use the name of the working folder.

    Args:
        build_rules_list: List to append a valid build_rules file instance.
        working_directory: Full path name of the build_rules.py to load.
        args: Args for determining verbosity for output.

    Returns:
        Name of the project.
    """

    # Check build_rules.py
    for rules in build_rules_list:
        project_name = rules('default_project_name', working_directory=working_directory)
        if project_name:
            break
    else:
        # Use the default
        project_name = os.path.basename(working_directory)

    # Print if needed.
    if args.verbose:
        print("Project name is {}".format(project_name))
    return project_name

########################################


def get_project_type(build_rules_list, working_directory, args):
    """
    Determine the project type.

    Scan the build_rules.py file for the command 'default_project_type'
    and if found, use that string for the project type. Otherwise,
    assume it's a command line tool.

    Args:
        build_rules_list: List to append a valid build_rules file instance.
        working_directory: Full path name of the build_rules.py to load.
        args: Args for determining verbosity for output.

    Returns:
        ProjectTypes enumeration.
    """

    # Check build_rules.py
    for rules in build_rules_list:
        item = rules('default_project_type', working_directory=working_directory)
        if item:
            project_type = ProjectTypes.lookup(item)
            if project_type is not None:
                break
            print('Project Type {} is not supported.'.format(item))
    else:
        # Use the default
        project_type = ProjectTypes.tool

    # Print if needed.
    if args.verbose:
        print("Project type is {}".format(str(project_type)))
    return project_type

########################################


def get_ide_list(build_rules_list, working_directory, args):
    """
    Determine the IDEs to generate projects for.

    Scan the build_rules.py file for the command 'default_ide'
    and if found, use that list of IDETypes or strings to lookup with
    IDETypes.lookup().

    Args:
        build_rules_list: List to append a valid build_rules file instance.
        working_directory: Full path name of the build_rules.py to load.
        args: Args for determining verbosity for output.

    Returns:
        List of IDEs to generate projects for.
    """

    # Get the IDE list from the command line
    temp_list = args.ides
    if not temp_list:
        for rules in build_rules_list:
            default = rules('default_ide', working_directory=working_directory)
            if default != 0:
                # Check if it's a single IDETypes enum
                if isinstance(default, IDETypes):
                    # Convert to a list
                    temp_list = [default]
                else:
                    # Assume it's a single string or a list of strings.
                    temp_list = convert_to_array(default)
                break

    # Convert strings to IDETypes.
    ide_list = []
    for item in temp_list:
        ide_type = IDETypes.lookup(item)
        if ide_type is None:
            print('IDE {} is not supported.'.format(item))
        else:
            ide_list.append(ide_type)

    # Print if needed.
    if args.verbose:
        print("IDE name {}".format(ide_list))

    return ide_list

########################################


def get_platform_list(build_rules_list, working_directory, args):
    """
    Determine the platforms to generate projects for.

    Scan the build_rules.py file for the command 'default_platform'
    and if found, use that list of PlatformTypes or strings to lookup with
    PlatformTypes.lookup().

    Args:
        build_rules_list: List to append a valid build_rules file instance.
        working_directory: Full path name of the build_rules.py to load.
        args: Args for determining verbosity for output.

    Returns:
        List of platforms to generate projects for.
    """

    # Add the build platforms
    temp_list = args.platforms
    if not temp_list:
        for rules in build_rules_list:
            default = rules('default_platform', working_directory=working_directory)
            if default != 0:
                # Check if it's a single IDETypes enum
                if isinstance(default, PlatformTypes):
                    # Convert to a list
                    temp_list = [default]
                else:
                    # Assume it's a single string or a list of strings.
                    temp_list = convert_to_array(default)
                break

    # Convert strings to PlatformTypes.
    platform_list = []
    for item in temp_list:
        platform_type = PlatformTypes.lookup(item)
        if platform_type is None:
            print('Platform {} is not supported.'.format(item))
        else:
            platform_list.append(platform_type)

    # Print if needed.
    if args.verbose:
        print("Platform name {}".format(platform_list))

    return platform_list

########################################


def get_configuration_list(build_rules_list, working_directory, args, platform, ide):
    """
    Determine the configurations to generate projects for.

    Scan the build_rules.py file for the command 'configuration_list'
    and if found, use that list of strings to create configurations.

    Args:
        build_rules_list: List to append a valid build_rules file instance.
        working_directory: Full path name of the build_rules.py to load.
        args: Args for determining verbosity for output.
        platform: Platform building.
        ide: IDETypes for the ide generating for.

    Returns:
        List of configuration strings to generate projects for.
    """

    # Create the configurations for this platform
    if args.configurations:
        configuration_list = args.configurations
    else:
        for rules in build_rules_list:
            configuration_list = rules('configuration_list',
                                       working_directory=working_directory,
                                       platform=platform,
                                       ide=ide)
            if configuration_list != 0:
                break
        else:
            configuration_list = [
                'Debug',
                'Internal',
                'Release'
            ]

    return configuration_list

########################################


def fixup_ide_platform(ide_list, platform_list):
    """
    Fix empty IDE/Platform lists.

    Given a list of IDEs and Platforms, determine what should be the defaults
    in case one or both of the lists are empty.

    Args:
        ide_list: List of IDEs to generate for.
        platform_list: List of platforms to build for.
    """

    # If no platform and IDE were selected, use the system defaults
    if not platform_list and not ide_list:
        platform_list.append(PlatformTypes.default())
        ide_list.append(IDETypes.default())

    # If no platform was selected, but and IDE was, choose
    # the host machine as the platform.
    elif not platform_list:
        platform_list.append(PlatformTypes.default())

    # No IDE selected?
    elif not ide_list:
        # Platform without an IDE is tricky, because video game platforms
        # are picky.
        if PlatformTypes.xbox360 in platform_list:
            ide_list.append(IDETypes.vs2010)

        elif PlatformTypes.ps3 in platform_list:
            ide_list.append(IDETypes.vs2010)

        elif PlatformTypes.ps4 in platform_list:
            ide_list.append(IDETypes.vs2010)

        elif PlatformTypes.vita in platform_list:
            ide_list.append(IDETypes.vs2010)

        elif PlatformTypes.shield in platform_list:
            ide_list.append(IDETypes.vs2010)

        elif PlatformTypes.wiiu in platform_list:
            ide_list.append(IDETypes.vs2013)

        # Unknown, punt on the IDE
        else:
            ide_list.append(IDETypes.default())
