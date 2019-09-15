#! /usr/bin/env python3

def readExtsFile(path):
    exts = []
    with open(path, 'r') as f:
        for l in f.readlines():
            ext = l.strip()
            if ext.startswith('#'):
                continue
            if len(ext):
                exts.append(ext)
    return exts

if __name__ == "__main__":

    import sys
    import os
    from os import path
    import argparse

    import xml.etree.ElementTree as etree

    rootDir = path.dirname(path.realpath(__file__))
    regDir = path.join(rootDir, 'registry')
    sys.path.insert(0, regDir)

    from reg import Registry
    from gldgen import *

    parser = argparse.ArgumentParser(description='OpenGL D bindings generator')
    parser.add_argument('--package', dest='package', default='gld',
                        help='D package of generated modules [gld]')
    parser.add_argument('--dest', dest='dest', default=path.join(rootDir, 'd'),
                        help='Destination folder for generated files [(gldgen)/d]')
    parser.add_argument('--gl-def-exts', dest='glDefExts', 
                        help='Set of default extensions to include in the generation')
    parser.add_argument('--gl-addext-file', dest='glAddExtFile', 
                        help="Path to file containing extensions to add (one by line)")
    parser.add_argument('--gl-remext', dest='glRemExts', nargs="*", default=[],
                        help="Extensions to remove (defaults to None)")
    parser.add_argument('--gl-remext-file', dest='glRemExtFile', 
                        help="Path to file containing extensions to remove (one by line)")
    args = parser.parse_args()

    pack = args.package
    srcDir = path.join(args.dest, pack.replace('.', os.sep))

    os.makedirs(srcDir, exist_ok=True)

    files = []

    # first we generate files from the hand-written templates
    templateFiles = [ 'eglplatform.d.in', 'khrplatform.d.in', 'loader.d.in', 'util.d.in' ]
    for tf in templateFiles:
        from string import Template
        with open(path.join(rootDir, 'templates', tf), mode="r") as ifile:
            t = Template(ifile.read())
            ofname = path.join(srcDir, tf.replace('.in', ''))
            with open(ofname, mode="w") as ofile:
                ofile.write(t.substitute(pack=pack))
            files.append(ofname)

    glRemExts = args.glRemExts
    if args.glRemExtFile:
        glRemExts += readExtsFile(args.glRemExtFile)

    glAddExts = []
    if args.glAddExtFile:
        glAddExts += readExtsFile(args.glAddExtFile) 

    # Turn a list of strings into a regexp string matching exactly those strings
    def makeREstring(list):
        return "^(" + "|".join(list) + ")$"

    # Descriptive names for various regexp patterns used to select
    # versions and extensions

    allVersions       = allExtensions = ".*"
    noVersions        = noExtensions = None
    gl12andLaterPat   = "1\.[2-9]|[234]\.[0-9]"
    # Extensions in old glcorearb.h but not yet tagged accordingly in gl.xml
    glCoreARBPat      = None
    glx13andLaterPat  = "1\.[3-9]"

    glAddExtsPat = None
    if len(glAddExts):
        glAddExtsPat = makeREstring(glAddExts)

    glRemExtsPat = None
    if len(glRemExts):
        glRemExtsPat = makeREstring(glRemExts)

    buildList = [
        DGeneratorOptions(      # equivalent of glcorearb.h
            filename            = path.join(srcDir, "gl.d"),
            apiname             = "gl",
            profile             = "core",
            versions            = allVersions,
            emitversions        = allVersions,
            defaultExtensions   = args.glDefExts,
            addExtensions       = glAddExtsPat,
            removeExtensions    = glRemExtsPat,
            regFile             = path.join(regDir, "gl.xml"),
            module              = "{}.gl".format(pack),
            humanName           = "OpenGL",
            cmdPrefix           = "gl",
            importedStructDecls = [],
            stmts               = [
                "import core.stdc.stdint;",
                "import {}.khrplatform;".format(pack),
                "import {}.loader : SymbolLoader;".format(pack),
            ]
        ),
        DGeneratorOptions(
            filename            = path.join(srcDir, "glx.d"),
            apiname             = "glx",
            profile             = None,
            versions            = allVersions,
            emitversions        = allVersions,
            defaultExtensions   = "glx",
            addExtensions       = None,
            removeExtensions    = makeREstring([
                "GLX_SGIX_dmbuffer", "GLX_SGIX_video_source"
            ]),
            regFile             = path.join(regDir, "glx.xml"),
            humanName           = "GLX",
            cmdPrefix           = "glX",
            module              = "{}.glx".format(pack),
            importedStructDecls = [],
            stmts               = [
                "version(linux):",
                "",
                "import core.stdc.config;",
                "import core.stdc.stdint;",
                "import {}.loader : SymbolLoader;".format(pack),
                "import {}.gl;".format(pack),
                "import X11.Xlib;",
            ]
        ),
        DGeneratorOptions(      # equivalent of wglext.h
            filename            = path.join(srcDir, "wgl.d"),
            apiname             = "wgl",
            profile             = None,
            versions            = allVersions,
            emitversions        = allVersions,
            defaultExtensions   = "wgl",
            addExtensions       = None,
            removeExtensions    = None,
            regFile             = path.join(regDir, "wgl.xml"),
            humanName           = "WinGL",
            cmdPrefix           = "wgl",
            module              = "{}.wgl".format(pack),
            importedStructDecls = [],
            stmts               = [
                "version(Windows):",
                "import core.stdc.config : c_ulong;",
                "import core.sys.windows.windef;",
                "import core.sys.windows.wingdi;",
                "import {}.loader : SymbolLoader;".format(pack),
                "import {}.gl;".format(pack),
            ]
        ),
        DGeneratorOptions(
            filename            = path.join(srcDir, "egl.d"),
            apiname             = "egl",
            profile             = None,
            versions            = allVersions,
            emitversions        = allVersions,
            defaultExtensions   = "egl",
            addExtensions       = None,
            removeExtensions    = None,
            regFile             = path.join(regDir, "egl.xml"),
            humanName           = "EGL",
            cmdPrefix           = "egl",
            module              = "{}.egl".format(pack),
            importedStructDecls = [],
            stmts               = [
                "import core.stdc.stdint;",
                "import {}.loader : SymbolLoader;".format(pack),
                "import {}.eglplatform;".format(pack),
                "import {}.khrplatform;".format(pack),
            ]
        ),
    ]

    for opts in buildList:
        gen = DGenerator()
        reg = Registry()
        reg.loadElementTree( etree.parse( opts.regFile ))
        reg.setGenerator( gen )
        reg.apiGen(opts)
        files.append(opts.filename)

    import platform
    libname=''
    if platform.system() == 'Windows':
        libname='gld.lib'
    else:
        libname='libgld.a'

    with open(path.join(rootDir, 'dmd_args.txt'), "w") as argfile:
        argfile.write('-lib\n')
        argfile.write('-I'+args.dest+'\n')
        argfile.write('-of'+path.join(rootDir, libname)+'\n')
        for f in files:
            if not 'glx' in f: # exclude due to external dep
                argfile.write(f + '\n')
