#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration file on how to build and clean projects in a specific folder.

This file is parsed by the cleanme, buildme, rebuildme and makeprojects
command line tools to clean, build and generate project files.
"""

## \package makeprojects.build_rules

from __future__ import absolute_import, print_function, unicode_literals

import sys
import os

from makeprojects.enums import PlatformTypes, ProjectTypes, IDETypes


########################################


def do_project_settings(project):
    """
    Set up defines and default libraries.

    Args:
        project: Project record to update.
    """

    project.use_mfc = False
    project.use_atl = False
    project.clr_support = False
    project.vs_CharacterSet = 'Unicode'
    return 0

########################################


def do_configuration_settings(configuration):
    """
    Set up defines and default libraries.

    Args:
        configuration: Configuration record to update.
    """

    # Too many branches
    # Too many statements
    # pylint: disable=R0912,R0915

    ide = configuration.project.ide
    define_list = []
    libraries_list = []

    # Debug/Release
    if configuration.debug:
        define_list.append('_DEBUG')
    else:
        define_list.append('NDEBUG')

    # Sanity check for missing platform
    platform = configuration.platform
    if platform is not None:

        # Windows specific defines
        if platform.is_windows():

            if ide.is_codewarrior():
                configuration.library_folders_list = [
                    '$(CodeWarrior)/MSL', '$(CodeWarrior)/Win32-x86 Support']
                if configuration.debug:
                    libraries_list.append('MSL_All_x86_D.lib')
                else:
                    libraries_list.append('MSL_All_x86.lib')

            libraries_list.extend(
                ['Kernel32.lib', 'Gdi32.lib', 'Shell32.lib', 'Ole32.lib',
                 'User32.lib', 'Advapi32.lib', 'version.lib', 'Ws2_32.lib',
                 'Comctl32.lib'])

            define_list.extend(['_WINDOWS', 'WIN32_LEAN_AND_MEAN'])
            if platform in (PlatformTypes.win64,
                            PlatformTypes.winarm64, PlatformTypes.winitanium):
                define_list.append('WIN64')
            else:
                define_list.append('WIN32')

            # Command line tools need this define
            if configuration.project_type is ProjectTypes.tool:
                define_list.append('_CONSOLE')

            if ide in (IDETypes.watcom, IDETypes.codeblocks):
                define_list.append('GLUT_DISABLE_ATEXIT_HACK')
                define_list.append('GLUT_NO_LIB_PRAGMA')

        # MSDos with DOS4GW extender
        if platform is PlatformTypes.msdos4gw:
            define_list.append('__DOS4G__')

        # MSDos with X32 extender
        if platform is PlatformTypes.msdosx32:
            define_list.append('__X32__')

        # Playstation 4
        if platform is PlatformTypes.ps4:
            define_list.append('__ORBIS2__')

        # Playstation Vita
        if platform is PlatformTypes.vita:
            define_list.append('SN_TARGET_PSP2')

        # Android targets
        if platform.is_android():
            define_list.append('DISABLE_IMPORTGL')
            libraries_list.extend(['android', 'EGL', 'GLESv1_CM'])

        # Xbox 360
        if platform == PlatformTypes.xbox360:
            define_list.extend(['_XBOX', 'XBOX'])
            libraries_list.extend(['xbdm.lib', 'xboxkrnl.lib'])
            if configuration.get_chained_value('profile'):
                libraries_list.extend(
                    ['d3d9i.lib', 'd3dx9i.lib', 'xgraphics.lib', 'xapilibi.lib',
                     'xaudio2.lib', 'x3daudioi.lib', 'xmcorei.lib'])
            elif configuration.debug:
                libraries_list.extend(
                    ['d3d9d.lib', 'd3dx9d.lib', 'xgraphicsd.lib',
                     'xapilibd.lib', 'xaudiod2.lib', 'x3daudiod.lib',
                     'xmcored.lib'])
            else:
                libraries_list.extend(
                    ['d3d9ltcg.lib', 'd3dx9.lib', 'xgraphics.lib',
                     'xapilib.lib', 'xaudio2.lib', 'x3daudioltcg.lib',
                     'xmcoreltcg.lib'])

        # Mac Carbon
        if platform.is_macos_carbon():
            define_list.append('TARGET_API_MAC_CARBON=1')

        # Nintendo DSI specific defines
        if platform == PlatformTypes.dsi:
            define_list.extend([
                'NN_BUILD_DEBUG',
                'NN_COMPILER_RVCT',
                'NN_COMPILER_RVCT_VERSION_MAJOR=$(CTRSDK_RVCT_VER_MAJOR)',
                'NN_PROCESSOR_ARM',
                'NN_PROCESSOR_ARM11MPCORE',
                'NN_PROCESSOR_ARM_V6',
                'NN_PROCESSOR_ARM_VFP_V2',
                'NN_HARDWARE_CTR',
                'NN_PLATFORM_CTR',
                'NN_HARDWARE_CTR_TS',
                'NN_SYSTEM_PROCESS',
                'NN_SWITCH_ENABLE_HOST_IO=1',
                'NN_BUILD_VERBOSE',
                'NN_BUILD_NOOPT',
                'NN_DEBUGGER_KMC_PARTNER'])

        # Nintendo Switch
        if platform.is_switch():
            configuration.include_folders_list.append(
                '$(NINTENDO_SDK_ROOT)\\include')

            if platform is PlatformTypes.switch32:
                configuration.include_folders_list.append(
                    '$(NINTENDO_SDK_ROOT)\\Common\\Configs\\'
                    'Targets\\NX-NXFP2-a32\\Include')
            else:
                configuration.include_folders_list.append(
                    '$(NINTENDO_SDK_ROOT)\\Common\\Configs\\'
                    'Targets\\NX-NXFP2-a64\\Include')

            define_list.append('NN_NINTENDO_SDK')
            if configuration.debug:
                define_list.append('NN_ENABLE_ASSERT')
                define_list.append('NN_ENABLE_ABORT_MESSAGE')
                if configuration.optimization:
                    define_list.append('NN_SDK_BUILD_DEVELOP')
                else:
                    define_list.append('NN_SDK_BUILD_DEBUG')
            else:
                define_list.append('NN_SDK_BUILD_RELEASE')
                define_list.append('NN_DISABLE_ASSERT')
                define_list.append('NN_DISABLE_ABORT_MESSAGE')

        # Linux platform
        if platform is PlatformTypes.linux:
            define_list.append('__LINUX__')

        # macOS X platform
        if platform.is_macosx():
            if not configuration.project_type.is_library():
                configuration.frameworks_list = [
                    'AppKit.framework',
                    'AudioToolbox.framework',
                    'AudioUnit.framework',
                    'Carbon.framework',
                    'Cocoa.framework',
                    'CoreAudio.framework',
                    'IOKit.framework',
                    'OpenGL.framework',
                    'QuartzCore.framework',
                    'SystemConfiguration.framework'
                ]

        # iOS platform
        if platform.is_ios():
            if not configuration.project_type.is_library():
                configuration.frameworks_list = [
                    'AVFoundation.framework',
                    'CoreGraphics.framework',
                    'CoreLocation.framework',
                    'Foundation.framework',
                    'QuartzCore.framework',
                    'UIKit.framework'
                ]

    # Save the #defines
    configuration.define_list = define_list

    # Only link libraries for executables.
    project_type = configuration.project_type
    if project_type is not None:
        if not project_type.is_library():
            configuration.libraries_list = libraries_list

    return 0


def do_configuration_list(platform, ide):
    """
    Create the default configurations.

    Args:
        platform: platform being built.
        ide: IDE being generated for.
    Returns:
        List of dict() descriptions of configurations.
    """

    # All platforms support this format.
    results = [
        {'name': 'Debug', 'short_code': 'dbg', 'debug': True},
        {'name': 'Internal', 'short_code': 'int', 'optimization': 4,
         'debug': True},
        {'name': 'Release', 'short_code': 'rel', 'optimization': 4}]

    # Xbox and Windows support link time code generation
    # as a platform
    if ide.is_visual_studio() and platform in (PlatformTypes.win32,
                                               PlatformTypes.win64,
                                               PlatformTypes.winarm32,
                                               PlatformTypes.winarm64,
                                               PlatformTypes.winitanium,
                                               PlatformTypes.xbox360):
        results.append({'name': 'Release_LTCG',
                        'short_code': 'ltc',
                        'optimization': 4,
                        'link_time_code_generation': True})

    # Configurations specific to the Xbox 360
    if platform is PlatformTypes.xbox360:
        results.extend(
            [{'name': 'Profile', 'short_code': 'pro',
              'optimization': 4, 'profile': True},
             {'name': 'Profile_FastCap', 'short_code': 'fas',
              'optimization': 4, 'profile': 'fast'},
             {'name': 'CodeAnalysis', 'short_code': 'cod', 'analyze': True}])

    return results

########################################


def rules(command, working_directory, root=True, **kargs):
    """
    Main entry point for build_rules.py.

    When ``makeprojects``, ``cleanme``, or ``buildme`` is executed, they will
    call this function to perform the actions required for build customization.

    The parameter ``working_directory`` is required, and if it has no default
    parameter, this function will only be called with the folder that this
    file resides in. If there is a default parameter of ``None``, it will be
    called with any folder that it is invoked on. If the default parameter is a
    directory, this function will only be called if that directory is desired.

    The optional parameter of ``root``` alerts the tool if subsequent processing
    of other ``build_rules.py`` files are needed or if set to have a default
    parameter of ``True``, processing will end once the calls to this
    ``rules()`` function are completed.

    Commands are 'build', 'clean', 'prebuild', 'postbuild', 'project',
    'configurations'

    Arg:
        command: Command to execute.
        working_directory: Directory for this function to operate on.
        root: If True, stop execution upon completion of this function
        kargs: Extra arguments specific to each command.
    Return:
        Zero on no error or no action.
    """

    # Unused arguments
    # Too many return statements
    # pylint: disable=W0613,R0911

    # Commands for cleanme.
    if command == 'clean':
        # Call functions to delete files and / or folders
        # Return non zero integer on error.
        pass

    # Commands for buildme.
    elif command == 'prebuild':
        # Perform actions before building any IDE based projects
        # Return non zero integer on error.
        pass

    elif command == 'build':
        # Perform actions to build
        # Return non zero integer on error.
        pass

    elif command == 'postbuild':
        # Perform actions after all IDE based projects
        # Return non zero integer on error.
        pass

    # Commands for makeprojects.
    elif command == 'default_project_name':
        # Return the default name of the project to create.
        return os.path.basename(working_directory)

    elif command == 'default_project_type':
        # Return the default type of project to create.
        return ProjectTypes.tool

    elif command == 'default_platform_ide':
        # Return the default IDE to build for.
        return IDETypes.default()

    elif command == 'default_platform':
        # Return the default platform to build for.
        return PlatformTypes.default()

    elif command == 'configuration_list':
        return do_configuration_list(kargs.get('platform'), kargs.get('ide'))

    elif command == 'project_settings':
        # Return the settings for a specific project
        return do_project_settings(kargs.get('project'))

    elif command == 'configuration_settings':
        # Set the defaults for this configuration
        return do_configuration_settings(kargs.get('configuration'))

    # Return zero to denote no error or no action.
    return 0


# If called as a command line and not a class, perform the build
if __name__ == "__main__":
    sys.exit(rules('build', os.path.dirname(os.path.abspath(__file__))))
