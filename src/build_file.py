#!/usr/bin/env python
#   IRPF90 is a Fortran90 preprocessor written in Python for programming using
#   the Implicit Reference to Parameters (IRP) method.
#   Copyright (C) 2009 Anthony SCEMAMA 
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
#   Anthony Scemama
#   LCPQ - IRSAMC - CNRS
#   Universite Paul Sabatier
#   118, route de Narbonne      
#   31062 Toulouse Cedex 4      
#   scemama@irsamc.ups-tlse.fr

import os, sys
import irpf90_t
from command_line import command_line

from os.path import basename

irpdir = irpf90_t.irpdir
mandir = irpf90_t.mandir
irp_id = irpf90_t.irp_id

cwd = os.getcwd()

def dress(f, in_root=False):
    #(str,bool) -> str
    """ Transfoms the filename into $PWD/IRPF90_temp/f 

    Note:
	 In root=True resurn $PWD/f
    """

    pwd = os.getcwd()
    if in_root:
        result = os.path.join(pwd, f)
    else:
        result = os.path.join(pwd, irpdir, f)
    return os.path.normpath(result)


def create_build_touches(l_irp_m, ninja):

    irp_id = irpf90_t.irp_id
    name = "irp_touches"
    short_target_o = "%s.irp.o" % name
    short_target_F90 = "%s.irp.F90" % name
    target_o = dress(short_target_o)
    target_F90 = dress(short_target_F90)

    list_of_modules_irp = ' '.join(l_irp_m)

    result_ninja = '\n'.join([
        "build {target_o}: compile_fortran_{irp_id} {target_F90} | {list_of_modules_irp}",
        "   short_in = {short_target_F90}", 
	"   short_out = {short_target_o}",
	""
    ])

    result_make = '\n'.join([
        "{target_o}: {target_F90} | {list_of_modules_irp}",
	'\t@printf "F: {short_target_F90} -> {short_target_o}\\n"',
	"\t@$(FC) $(FCFLAGS) -c $^ -o $@", ""
    ])

    result = result_ninja if ninja else result_make

    return result.format(**locals())


def create_build_archive(l_irp_o, l_usr_o_wo_main, l_ext_o, l_irp_sup_o, ninja=True):
    # (List[str] * 6 ) -> str
    """Create the build command for the irp_touches.o file and the irpf90.a library.
 
    - the touch file need all the irp_module.
    - the archive file need all the object.

    """

    irp_id = irpf90_t.irp_id
    short_lib = "irpf90.a"
    lib = dress(short_lib)

    list_of_object = ' '.join(l_irp_o + l_usr_o_wo_main + l_ext_o + l_irp_sup_o)

    result_ninja = '\n'.join([
	"build {lib}: archive_{irp_id} {list_of_object}",
	"   short_out = {short_lib}",
	""])

    result_make = '\n'.join([
	"{lib}: {list_of_object}",
	'\t@printf "Archive: {short_lib}\\n"',
	"\t@$(AR) cr $@ $^", ""])

    result = result_ninja if ninja else result_make
    return result.format(**locals())


def create_build_link(t, l_irp_m, l_usr_m, l_ext_m, ninja=True):
    # (Module, List[str], List[str]) -> str
    """ Create the build command who will link the .o file into the target executable

	To link we need the .o file corresponding to the target, and the ar lib.
    """

    irp_id = irpf90_t.irp_id

    filename = t.filename
    progname = t.prog_name

    basename = os.path.basename(filename)
    if basename != progname:
 	from util import logger
	logger.info('program-name `{0}` != file-name `{1}` (using file-name for now...)'.format(progname,basename))

    target = dress(filename, in_root=True)
    short_target = filename
    short_target_o = "%s.irp.o" % filename

    target_o = dress(short_target_o)

    list_of_module = ' '.join(l_irp_m + l_usr_m + l_ext_m)
    irp_lib = dress("irpf90.a")

    result_ninja = '\n'.join([
        "build {target}: link_{irp_id} {target_o} {irp_lib} | {list_of_module}",
        "   short_out = {short_target}", 
	""])

    result_make = '\n'.join([
	"{target}:{target_o} {irp_lib} | {list_of_module}",
	'\t@printf "Link: {short_target}\\n"',
	"\t@$(FC) $^ $(LIB) -o $@",
         ""])

    result = result_ninja if ninja else result_make

    return result.format(**locals())


def create_build_compile(t, l_module, l_ext_modfile=[], ninja=True):
    # (Module, List[Module], List[str], bool) -> str
    """Create the build command for the module t.
 
     - The module can produce a .MOD file
     - The module can Need another .MOD file. 
	 This .MOD file can be produced by:
	     1) a file generated by IRP_F90 preprocessor.
             2) a file defined by the user but a .irp.f90 file.
             3) a file not handle at all by IRPF90.

     - The fortran90 file maybe created by the Python module need no dependency.

     """

    irp_id = irpf90_t.irp_id
    name = t.filename

    short_target = name
    target = dress(name, in_root=True)

    short_target_o = "%s.irp.o" % name
    short_target_F90 = "%s.irp.F90" % name

    target_o = dress(short_target_o)
    target_F90 = dress(short_target_F90)

    # Here is the hack. We don't check MOD files, but the associated .o.
    # MOD name are not part of the standart.

    needed_modules = [dress(x, in_root=True) for x in l_ext_modfile]

    # Expensive and stupid. We can create a dict to do the loockup only once 
    for m in t.needed_modules_usr:
		# m is name
		for x in l_module:
			if m in x.gen_mod and x.filename != t.filename:
				needed_modules.append("%s.irp.o" %  x.filename)

    from util import uniquify
    needed_modules = uniquify(needed_modules)

    needed_modules_irp = [
        "%s.irp.module.o" % (x.filename) for x in l_module if x.name in t.needed_modules_irp
    ]

    if t.has_irp_module:
        short_target_module_F90 = "%s.irp.module.F90" % name
        short_target_module_o = "%s.irp.module.o" % name

        target_module_o = dress(short_target_module_o)
        target_module_F90 = dress(short_target_module_F90)
        needed_modules_irp += [target_module_o]

    list_of_modules     = ' '.join(map(dress, needed_modules))
    list_of_modules_irp = ' '.join(map(dress, needed_modules_irp))

    inline_include = True
    if not inline_include:
	    #Wrong name, this not work!
	    #list_of_includes = ' '.join(map(lambda x: dress(x, in_root=True), t.includes))
	    raise NotImplemented
    else:
	    #The include have already by included
	    list_of_includes = ' '
  
    l_build = [
        "build {target_o}: compile_fortran_{irp_id} {target_F90} | {list_of_includes}  {list_of_modules} {list_of_modules_irp}",
        "   short_in  = {short_target_F90}",
	"   short_out = {short_target}",
	""
    ]

    l_build_make = [
        "{target_o}: {target_F90} | {list_of_includes}  {list_of_modules} {list_of_modules_irp}",
	'\t@printf "F: {short_target_F90} -> {short_target}\\n"',
        "\t@$(FC) $(FCFLAGS) -c $^ -o $@", ""
    ]

    # No need of module when compiling the irp_module.
    if t.has_irp_module:
        l_build += [
            "build {target_module_o}: compile_fortran_{irp_id} {target_module_F90} | {list_of_includes} {list_of_modules} ",
            "   short_in  = {short_target_module_F90}",
	    "   short_out = {short_target_module_o}",
	    ""
        ]

        l_build_make += [
            "{target_module_o}: {target_module_F90} | {list_of_includes} {list_of_modules}",
	    '\t@printf "F: {short_target_module_F90} -> {short_target_module_o}\\n"',
	    "\t@$(FC) $(FCFLAGS) -c $^ -o $@", ""
        ]

    l_cur = l_build if ninja else l_build_make
    return '\n'.join(l_cur).format(**locals())


def create_build_remaining(f,ninja):
    """
    Create the build command for the remaining file f. f is a file name (str).
    """

    irp_id = irpf90_t.irp_id

    t, extension = f.rsplit('.', 1)
    t1 = dress(t, in_root=True)
    t2 = dress(t, in_root=False)
    target_i = f
    target_o = "%s.o" % t

    if not target_o.startswith(os.path.join(cwd, irpdir)):
        target_o = target_o.replace(cwd, os.path.join(cwd, irpdir))

    short_target_o = os.path.split(target_o)[1]
    short_target_i = os.path.split(target_i)[1]

    if extension.lower() in ['f', 'f90']:
        result = ["build {target_o}: compile_fortran_{irp_id} {target_i}"]
	result_make = [
            '{target_o}: {target_i}',
            '\t@printf "F: {short_target_o} -> {short_target_i}\\n"',
            "\t@$(FC) $(FCFLAGS) -c $^ -o $@", ""]

    elif extension.lower() in ['c']:
        result = ["build {target_o}: compile_c_{irp_id} {target_i}"]
    elif extension.lower() in ['cxx', 'cpp']:
        result = ["build {target_o}: compile_cxx_{irp_id} {target_i}"]

    result += ["   short_in  = {short_target_i}", "   short_out = {short_target_o}", ""]

    result_final = result if ninja else result_make 

    return '\n'.join(result_final).format(**locals())


def create_makefile(d_flags,d_var,irpf90_flags,ninja=True):

    result = ["IRPF90= irpf90",
              "IRPF90FLAGS= %s" % irpf90_flags,
              "BUILD_SYSTEM= %s" % ('ninja' if ninja else 'make'),
	      ""]

    # Export all the env variable used by irpf90
    result += ['.EXPORT_ALL_VARIABLES:',
		'',
		'\n'.join("{0} = {1}".format(k, v) for k, v in sorted(d_flags.iteritems())),
		'',
		'\n'.join("{0} = {1}".format(k, ' '.join(v)) for k, v in sorted(d_var.iteritems())),
		'']

    result += [ r'# Dark magic below modify with caution!',
	        r'# "You are Not Expected to Understand This"',
                r"#                     .",
		r"#           /^\     .",
		r'#      /\   "V",',
		r"#     /__\   I      O  o",
		r"#    //..\\  I     .",
		r"#    \].`[/  I",
		r"#    /l\/j\  (]    .  O",
		r"#   /. ~~ ,\/I          .",
		r"#   \\L__j^\/I       o",
		r"#    \/--v}  I     o   .",
		r"#    |    |  I   _________",
		r"#    |    |  I c(`       ')o",
		r"#    |    l  I   \.     ,/",
		r"#  _/j  L l\_!  _//^---^\\_",
		r""]

    result += ["",
	      "ifeq ($(BUILD_SYSTEM),ninja)",
              "\tBUILD_FILE=IRPF90_temp/build.ninja",
              "\tIRPF90FLAGS += -j",
              "else ifeq ($(BUILD_SYSTEM),make)",
              "\tBUILD_FILE=IRPF90_temp/build.make",
	      "\tBUILD_SYSTEM += -j",
	      "else",
	      "DUMMY:",
              "\t$(error 'Wrong BUILD_SYSTEM: $(BUILD_SYSTEM)')",
	      "endif"]

    result += ["",
               "define run_and_touch",
	       "        $(BUILD_SYSTEM) -C $(dir $(1) ) -f $(notdir $(1) ) $(addprefix $(CURDIR)/, $(2)) && touch $(2)",
	       "endef",
	       "",
               "EXE := $(shell egrep -ri '^\s*program' *.irp.f | cut -d'.' -f1)",
               "",
               ".PHONY: all",
	       "",
               "all: $(BUILD_FILE)",
               "\t$(call run_and_touch, $<, $(EXE))",
               "",
	       ".NOTPARALLEL: $(EXE)",
               "$(EXE): $(BUILD_FILE)",
               "\t$(call run_and_touch, $<, $(EXE))",
               
               "$(BUILD_FILE): $(shell find .  -maxdepth 2 -path ./IRPF90_temp -prune -o -name '*.irp.f' -print)",
               "\t$(IRPF90) $(IRPF90FLAGS)",
	       "",
	       "clean:",
	       '\trm -f -- $(BUILD_FILE) $(EXE)'
	       '\t$(shell find IRPF90_temp -type f \\( -name "*.o" -o -name "*.mod" -name "*.a" \\)  -delete;)',
	       "veryclean: clean",
	       "\trm -rf IRPF90_temp/ IRPF90_man/ irpf90_entities dist tags"]

    import util
    data = '%s\n' % '\n'.join(result) 
    util.lazy_write_file('Makefile',data,conservative=True)

def create_make_all_clean(l_main):
	# 
	'''Create the ALL and CLEAN target of Makefile

	Note: Portability doesn't mater. -delete is maybe not posix
	      but  -exec rm {} + is far more ugly!
	
	 '''

    	l_executable =' '.join(dress( t.filename, in_root=True) for t in l_main)

	output = [".PHONY : all",
		  "all: {l_executable}",
		  "",
		  ".PHONY: clean",
		  "clean:", 
		  '\tfind . -type f \( -name "*.o" -o -name "*.mod" \)  -delete; rm -f {l_executable} --'
		  ""]

	return [ '\n'.join(output).format(**locals())]

def create_var_and_rule(d_flags, ninja):

    output = ['\n'.join("{0} = {1}".format(k, v) for k, v in d_flags.iteritems())]

    if ninja:
        output += ["builddir = %s" % os.path.join(cwd, irpdir)]

        # Rules
        t = [
            "rule compile_fortran_{irp_id}",
	    "  command = $FC $FCFLAGS -c $in -o $out",
            "  description = F   : $short_in -> $short_out", 
            "",
            "rule compile_c_{irp_id}",
            "  command = $CC $CFLAGS -c $in -o $out",
            "  description = C   : $short_in -> $short_out",
            "",
            "rule compile_cxx_{irp_id}",
            "  command = $CXX $CXXFLAGS -c $in -o $out",
            "  description = C++ :  $short_in -> $short_out",
            "",
            "rule archive_{irp_id}",
            "  command = $AR cr $out $in",
            "  description = Archive: $short_out",
	    "",
            "rule link_{irp_id}",
            "  command = $FC $FCFLAGS $in $LIB -o $out",
            "  description = Link: $short_out",
            ""
        ]

        output += ['\n'.join(t).format(irp_id=irpf90_t.irp_id, **d_flags)]

    return output


# Environment variables

d_default = {
        "FC": "gfortran",
        "FCFLAGS": "-O2",
        "AR": "ar",
        "RANLIB": " ranlib",
        "CC": "gcc",
        "CFLAGS": "-O2",
        "CXX": "g++",
        "CXXFLAGS": "-O2",
	"LIB": ""}

d_flags = dict()
for k, v in d_default.iteritems():
        d_flags[k] = os.environ[k] if k in os.environ else v

include_dir = ' ' + ' '.join(["-I %s" % (i) for i in command_line.include_dir])

d_var = dict()
for k in ['SRC', 'OBJ']:
       d_var[k] = os.environ[k].split() if k in os.environ else []


def create_generalmakefile(ninja):
	    create_makefile(d_flags,d_var, include_dir,ninja)

def run(d_module, ninja):
    #(Dict[str,Module],bool) -> str
    """Wrote the ninja file needed to compile the program

    Note:
	- FC,AR,CC,CXX,LIB, FCFLAGS, CFLAGS, CXXFLAGS are compiler enviroment read
	- SRC,OBJ: Are the not irp.f file defined by the user 
    """

    # Add required flags

    for k in ['FCFLAGS', 'CFLAGS', 'CXXFLAGS']:
        d_flags[k] += include_dir

    # Each python module can produce one or two .F90/.o file and maybe one .MOD file:
    #
    #    No usr defined module and no IRP-F90 provider declaration:
    #           - One .F90  - No .MOD file
    #    Usr defined module AND no IRP-F90 provider:
    #           - One .F90  - One. MOD file
    #    No usr define module AND IRP-F90 provider:
    #           - Two .F90  - One. MOD file

    # Each python module can depend of different module:
    #    - IRP created one
    #    - usr declared
    #    - external (don't know by IRP)

    # Each python module can need 3 type of .MOD file
    l_mod = list(d_module.values())

    # Modules that are not targets
    l_mod_no_main = filter(lambda m: not m.is_main, l_mod)
    l_mod_main = filter(lambda m: m.is_main, l_mod)

    # List irp supl object/source files
    l_irp_sup_o = ["irp_touches.irp.o"]
    l_irp_sup_s = ["irp_touches.irp.F90"]

    if command_line.do_assert:
        l_irp_sup_o += ["irp_stack.irp.o"]
        l_irp_sup_s += ["irp_stack.irp.F90"]

    if command_line.do_openmp:
        l_irp_sup_o += ["irp_locks.irp.o"]
        l_irp_sup_s += ["irp_locks.irp.F90"]

    if command_line.do_profile:
        l_irp_sup_o += ["irp_profile.irp.o", "irp_rdtsc.o"]
        l_irp_sup_s += ["irp_profile.irp.F90", "irp_rdtsc.c"]

    l_irp_sup_o = map(dress, l_irp_sup_o)
    l_irp_sup_s = map(dress, l_irp_sup_s)

    # List of extrernal object/source file
    l_ext_o = l_ext_m = map(lambda x: dress(x, in_root=True), d_var['OBJ'])
    l_ext_s = map(lambda x: dress(x, in_root=True), d_var['SRC'])

    # List of object create by the IRP-F90
    l_irp_o = l_irp_m = map(dress,
                            ["%s.irp.module.o" % (m.filename) for m in l_mod if m.has_irp_module])

    # List of object create by the USR. Maybe he have a module, maybe not.
    l_usr_o_wo_main = map(dress, ["%s.irp.o" % (m.filename) for m in l_mod_no_main])
    l_usr_m = map(dress, ["%s.irp.o" % (m.filename) for m in l_mod if m.needed_modules_usr])

    #-=~=~= 
    # O U T P U T
    #~=~=~=

    output = create_var_and_rule(d_flags, ninja)
    if not ninja:
	output += create_make_all_clean(l_mod_main)
	
    # Create all the .irp.F90 -> .o
    for m in l_mod:
        output.append(create_build_compile(m, l_mod, l_ext_m, ninja))

    output.append(create_build_touches(l_irp_m,ninja))
    # All the objects. Kind of, only need usr without main for the static library
    output.append(create_build_archive(l_irp_o, l_usr_o_wo_main, l_ext_o, l_irp_sup_o, ninja))

    for i in l_mod_main:
        # All the mod (overshoot)
        output.append(create_build_link(i, l_irp_m, l_usr_m, l_ext_m, ninja))

    # Remaining files
    for i in l_irp_sup_s[1:]+l_ext_s:
        output.append(create_build_remaining(i, ninja))

    filename = os.path.join(irpdir, "build.ninja" if ninja else "build.make")

    data = '%s\n' % '\n\n'.join(output)
    import util
    util.lazy_write_file(filename,data,touch=True)

    return
