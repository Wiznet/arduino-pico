#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# build.py — build a sketch using arduino-builder
#
# Wrapper script around arduino-builder which accepts some ESP8266-specific
# options and translates them into FQBN
#
# Copyright © 2016 Ivan Grokhotkov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
#

from __future__ import print_function
import sys
import os
import argparse
import platform
import subprocess
import tempfile
import shutil


# Arduino-builder needs forward-slash paths for passed in params or it cannot
# launch the needed toolset.
def windowsize_paths(l):
    """Convert forward-slash paths to backslash paths referenced from C:"""
    out = []
    for i in l:
        if i.startswith('/'):
            i = 'C:' + i
        out += [i.replace('/', '\\')]
    return out

def compile(tmp_dir, sketch, cache, tools_dir, hardware_dir, ide_path, f, args):
    cmd = []
    cmd += [ide_path + '/arduino-builder']
    cmd += ['-compile', '-logger=human']
    cmd += ['-build-path', tmp_dir]
    cmd += ['-tools', ide_path + '/tools-builder']
    if cache != "":
        cmd += ['-build-cache', cache ]
    if args.library_path:
        for lib_dir in args.library_path:
            cmd += ['-libraries', lib_dir]
    cmd += ['-hardware', ide_path + '/hardware']
    if args.hardware_dir:
        for hw_dir in args.hardware_dir:
            cmd += ['-hardware', hw_dir]
    else:
        cmd += ['-hardware', hardware_dir]
    # Debug=Serial,DebugLevel=Core____
    fqbn = '-fqbn=pico:rp2040:rpipico:' \
               'flash=2097152_65536,' \
               'freq={freq},' \
               'dbgport={dbgport},' \
               'dbglvl={dbglvl},' \
               'usbstack={usbstack}'.format(**vars(args))
    if "/WiFi" in sketch:
        fqbn = fqbn.replace("rpipico", "rpipicow")
    if "/ArduinoOTA" in sketch:
        fqbn = fqbn.replace("rpipico", "rpipicow")
    cmd += [fqbn]
    cmd += ['-built-in-libraries', ide_path + '/libraries']
    cmd += ['-ide-version=10607']
    cmd += ['-warnings={warnings}'.format(**vars(args))]
    if args.verbose:
        cmd += ['-verbose']
    cmd += [sketch]

    if platform.system() == "Windows":
        cmd = windowsize_paths(cmd)

    if args.verbose:
        print('Building: ' + " ".join(cmd), file=f)

    p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
    p.wait()
    return p.returncode

def parse_args():
    parser = argparse.ArgumentParser(description='Sketch build helper')
    parser.add_argument('-v', '--verbose', help='Enable verbose output',
                        action='store_true')
    parser.add_argument('-i', '--ide_path', help='Arduino IDE path')
    parser.add_argument('-p', '--build_path', help='Build directory')
    parser.add_argument('-l', '--library_path', help='Additional library path',
                        action='append')
    parser.add_argument('-d', '--hardware_dir', help='Additional hardware path',
                        action='append')
    parser.add_argument('-b', '--board_name', help='Board name', default='generic')
    parser.add_argument('-f', '--freq', help='CPU frequency', default=133,
                        choices=[50, 125, 133], type=int)
    parser.add_argument('-w', '--warnings', help='Compilation warnings level',
                        default='none', choices=['none', 'all', 'more'])
    parser.add_argument('-o', '--output_binary', help='File name for output binary')
    parser.add_argument('-k', '--keep', action='store_true',
                        help='Don\'t delete temporary build directory')
    parser.add_argument('--dbgport', help='Debug port', default='Disabled',
                        choices=['Disabled', 'Serial', 'Serial1'])
    parser.add_argument('--dbglvl', help='Debug level', default='None',
                        choices=['None', 'All'])
    parser.add_argument('--usbstack', help='USB stack', default='picosdk',
                        choices=['picosdk', 'tinyusb'])
    parser.add_argument('--build_cache', help='Build directory to cache core.a', default='')
    parser.add_argument('sketch_path', help='Sketch file path')
    return parser.parse_args()

def main():
    args = parse_args()

    ide_path = args.ide_path
    if not ide_path:
        ide_path = os.environ.get('ARDUINO_IDE_PATH')
        if not ide_path:
            print("Please specify Arduino IDE path via --ide_path option"
                  "or ARDUINO_IDE_PATH environment variable.", file=sys.stderr)
            return 2

    sketch_path = args.sketch_path
    tmp_dir = args.build_path
    created_tmp_dir = False
    if not tmp_dir:
        tmp_dir = tempfile.mkdtemp()
        created_tmp_dir = True

    tools_dir = os.path.dirname(os.path.realpath(__file__)) + '/../tools'
    # this is not the correct hardware folder to add.
    hardware_dir = os.path.dirname(os.path.realpath(__file__)) + '/../cores'

    output_name = tmp_dir + '/' + os.path.basename(sketch_path) + '.bin'

    if args.verbose:
        print("Sketch: ", sketch_path)
        print("Build dir: ", tmp_dir)
        print("Cache dir: ", args.build_cache)
        print("Output: ", output_name)

    if args.verbose:
        f = sys.stdout
    else:
        f = open(tmp_dir + '/build.log', 'w')

    res = compile(tmp_dir, sketch_path, args.build_cache, tools_dir, hardware_dir, ide_path, f, args)
    if res != 0:
        return res

    if args.output_binary is not None:
        shutil.copy(output_name, args.output_binary)

    if created_tmp_dir and not args.keep:
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == '__main__':
    sys.exit(main())
