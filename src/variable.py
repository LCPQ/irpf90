#!/usr/bin/python

from irpf90_t import *
from util import *
import error
from command_line import command_line

class Variable(object):

  ############################################################
  def __init__(self,text,name = None):
    assert isinstance(text,list)
    assert len(text) > 0
    assert isinstance(text[0],Begin_provider)
    self.text = text
    if name is not None:
      self._name = name.lower()
    self.is_read    = False
    self.is_written = False

  ############################################################
  def is_touched(self):
    '''Name is lowercase'''
    if '_is_touched' not in self.__dict__:
      from variables import variables
      result = False
      for i in self.children:
        if variables[i].is_touched:
          result = True
          break
      self._is_touched = result
    return self._is_touched
  is_touched = property(is_touched)

  ############################################################
  def is_main(self):
    '''Name is lowercase'''
    if '_is_main' not in self.__dict__:
      self._is_main = (self.name == self.same_as)
    return self._is_main
  is_main = property(is_main)

  ############################################################
  def name(self):
    '''Name is lowercase'''
    if '_name' not in self.__dict__:
      buffer = None
      for line in self.text:
        if isinstance(line,Begin_provider):
          self._name = line.filename[1]
          break
    return self._name
  name = property(name)

  ############################################################
  def doc(self):
    if '_doc' not in self.__dict__:
      def f(l): return 
      buffer = filter(lambda l:isinstance(l,Doc), self.text)
      self._doc = map(lambda l: l.text[1:], buffer)
      if buffer == []:
        error.warn(None,"Variable %s is not documented"%(self.name))
    return self._doc
  doc = property(doc)

  ############################################################
  def documented(self):
    if '_documented' not in self.__dict__:
      self._documented = (self.doc != [])
    return self._documented
  documented = property(documented)

  ############################################################
  def others(self):
    if '_others' not in self.__dict__:
      result = []
      f = lambda  l: type(l) in [Begin_provider, Cont_provider]
      lines = filter(f, self.text)
      for line in lines:
        result.append(line.filename[1])
      result.remove(self.name)
      self._others = result
    return self._others
  others = property(others)

  ############################################################
  def same_as(self):
    if '_same_as' not in self.__dict__:
      if isinstance(self.line,Begin_provider):
        result = self.name
      else:
        result = self.text[0].filename[1]
      self._same_as = result
    return self._same_as
  same_as = property(same_as)

  ############################################################
  def allocate(self):
    if '_allocate' not in self.__dict__:
      if not self.is_main:
        self._allocate = []
      else:
        from variables import variables
        def f(var):
          return variables[var].dim != []
        self._allocate = filter ( f, self.others + [self.name] )
    return self._allocate
  allocate = property(allocate)

  ############################################################
  def dim(self):
    if '_dim' not in self.__dict__:
      line = self.line.text.split('!')[0]
      buffer = line.replace(']','').split(',',2)
      if len(buffer) == 2:
        self._dim = []
      else:
        buffer = buffer[2].strip()[1:-1].split(',')
        self._dim = map(strip,buffer)
    return self._dim
  dim = property(dim)

  ############################################################
  def type(self):
    if '_type' not in self.__dict__:
      line = self.line.text
      buffer = line.split(',')[0]
      buffer = buffer.split('[')[1].strip()
      if self.dim != []:
        buffer = "%s, allocatable"%(buffer)
      self._type = buffer
    return self._type
  type = property(type)

  ############################################################
  def fmodule(self):
    if '_fmodule' not in self.__dict__:
      self._fmodule = self.line.filename[0].split('.irp.f')[0]+'_mod'
    return self._fmodule
  fmodule = property(fmodule)

  ############################################################
  def regexp(self):
    if '_regexp' not in self.__dict__:
      import re
      self._regexp = re.compile( \
       #r"^.*[^a-z0-9'\"_]+%s([^a-z0-9_]|$)"%(self.name),re.I)
        r"([^a-z0-9'\"_]|^)%s([^a-z0-9_]|$)"%(self.name),re.I)
    return self._regexp
  regexp = property(regexp)

  ############################################################
  def line(self):
    if '_line' not in self.__dict__:
      f = lambda l: type(l) in [Begin_provider, Cont_provider]
      lines = filter(f, self.text)
      for line in lines:
        buffer = line.filename[1]
        if self._name == buffer:
          self._line = line
          break
    assert '_line' in self.__dict__
    return self._line
  line = property(line)

  ############################################################
  def header(self):
    if '_header' not in self.__dict__:
      name = self.name
      def build_dim(d):
        if d == []:
          return ""
        else:
          x = map(lambda x: ":", self.dim)
          return "(%s)"%(','.join(x))
      self._header = [ "  %s :: %s %s"%(self.type, name, build_dim(self.dim) ) ]
      if self.is_main:
       self._header += [ "  logical :: %s_is_built = .False."%(name) ]
    return self._header
  header = property(header)

  ############################################################
  def toucher(self):
    if '_toucher' not in self.__dict__:
      if not self.is_main:
        self._toucher = []
      else:
        from modules import modules
        from variables import variables
        if '_needed_by' not in self.__dict__:
          import parsed_text
        parents = self.parents
        parents.sort()
        mods = map(lambda x: variables[x].fmodule, parents)
        mods = make_single(mods)+[self.fmodule]
        name = self.name
        result = [ "subroutine touch_%s"%(name) ]
        result += map(lambda x: "  Use %s"%(x),mods)
        result.append("  implicit none")
        if command_line.do_debug:
          length = str(len("touch_%s"%(name)))
          result += [ "  character*(%s), parameter :: irp_here = 'touch_%s'"%(length,name),
                      "  call irp_enter(irp_here)" ]
        result += map( lambda x: "  %s_is_built = .False."%(x), parents)
        result.append("  %s_is_built = .True."%(name))
        if command_line.do_debug:
          result.append("  call irp_leave(irp_here)")
        result.append("end subroutine touch_%s"%(name))
        result.append("")
        self._toucher = result
    return self._toucher
  toucher = property(toucher)

  ##########################################################
  def reader(self):
    if '_reader' not in self.__dict__:
      if not self.is_main:
        self._reader = []
      else:
        if '_needs' not in self.__dict__:
          import parsed_text
        from variables import variables
        name = self.name
        result = [ \
        "subroutine reader_%s(irp_num)"%(name),
        "  use %s"%(self.fmodule),
        "  implicit none",
        "  character*(*), intent(in) :: irp_num",
        "  logical                   :: irp_is_open",
        "  integer                   :: irp_iunit" ]
        if command_line.do_debug:
          length = len("reader_%s"%(self.name))
          result += [\
          "  character*(%d), parameter :: irp_here = 'reader_%s'"%(length,name),
          "  call irp_enter(irp_here)" ]
        result += map(lambda x: "  call reader_%s(irp_num)"%(x),self.needs) 
        result += [ \
        "  irp_is_open = .True.",
        "  irp_iunit = 9",
        "  do while (irp_is_open)",
        "   irp_iunit = irp_iunit+1", 
        "   inquire(unit=irp_iunit,opened=irp_is_open)",
        "  enddo"]
        for n in [ name ]+self.others:
          result += [\
          "  open(unit=irp_iunit,file='irpf90_%s_'//trim(irp_num),form='FORMATTED',status='OLD',action='READ')"%(n),
          "  read(irp_iunit,*) %s%s"%(n,build_dim(variables[n].dim)),
          "  close(irp_iunit)" ]
        result += [ \
        "  call touch_%s"%(name),
        "  %s_is_built = .True."%(name) ]
        if command_line.do_debug:
          result.append("  call irp_leave(irp_here)")
        result.append("end subroutine reader_%s"%(name))
        result.append("")
        self._reader = result
    return self._reader
  reader = property(reader)

  ##########################################################
  def writer(self):
    if '_writer' not in self.__dict__:
      if not self.is_main:
        self._writer = []
      else:
        from variables import variables
        if '_needs' not in self.__dict__:
          import parsed_text
        name = self.name
        result = [ \
        "subroutine writer_%s(irp_num)"%(name),
        "  use %s"%(self.fmodule),
        "  implicit none",
        "  character*(*), intent(in) :: irp_num",
        "  logical                   :: irp_is_open",
        "  integer                   :: irp_iunit" ]
        if command_line.do_debug:
          length = len("writer_%s"%(self.name))
          result += [\
          "  character*(%d), parameter :: irp_here = 'writer_%s'"%(length,name),
          "  call irp_enter(irp_here)" ]
        result += [ \
        "  if (.not.%s_is_built) then"%(self.same_as),
        "    call provide_%s"%(self.same_as),
        "  endif" ]
        result += map(lambda x: "  call writer_%s(irp_num)"%(x),self.needs) 
        result += [ \
        "  irp_is_open = .True.",
        "  irp_iunit = 9",
        "  do while (irp_is_open)",
        "   irp_iunit = irp_iunit+1", 
        "   inquire(unit=irp_iunit,opened=irp_is_open)",
        "  enddo" ]
        for n in [ name ] + self.others:
          result += [\
          "  open(unit=irp_iunit,file='irpf90_%s_'//trim(irp_num),form='FORMATTED',status='UNKNOWN',action='WRITE')"%(n),
          "  write(irp_iunit,*) %s%s"%(n,build_dim(variables[n].dim)),
          "  close(irp_iunit)" ]
        if command_line.do_debug:
          result.append("  call irp_leave(irp_here)")
        result.append("end subroutine writer_%s"%(name))
        result.append("")
        self._writer = result
    return self._writer
  writer = property(writer)

  ##########################################################
  def free(self):
    if '_free' not in self.__dict__:
      name = self.name
      result = [ "!","! >>> FREE %s"%(self.name),
        "  %s_is_built = .False."%(self.same_as) ] 
      if self.dim != []:
        result += [ \
        "  if (allocated(%s)) then"%(name),
        "    deallocate (%s)"%(name),
        "  endif" ]
      result.append("! <<< END FREE")
      self._free = result
    return self._free
  free = property(free)

  ##########################################################
  def provider(self):
    if '_provider' not in self.__dict__:
     if not self.is_main:
       self._provider = []
     else:
      if '_to_provide' not in self.__dict__:
        import parsed_text
      from variables import variables, build_use, call_provides
      name = self.name
      same_as = self.same_as

      def build_alloc(name):
        self = variables[name]
        if self.dim == []:
           return []

        def do_size():
           result = "     print *, ' size: ("
           result += ','.join(self.dim)
           return result+")'"

        def check_dimensions():
          result = map(lambda x: "(%s>0)"%(dimsize(x)), self.dim)
          result = ".and.".join(result)
          result = "   if (%s) then"%(result)
          return result
 
        def dimensions_OK():
          result = [ "  irp_dimensions_OK = .True." ]
          for i,k in enumerate(self.dim):
              result.append("  irp_dimensions_OK = irp_dimensions_OK.AND.(SIZE(%s,%d)==(%s))"%(name,i+1,dimsize(k)))
          return result

        def do_allocate():
          result = "    allocate(%s(%s),stat=irp_err)"
          result = result%(name,','.join(self.dim))
          return result

        result = [ " if (allocated (%s) ) then"%(name) ]
        result += dimensions_OK()
        result += [\
          "  if (.not.irp_dimensions_OK) then",
          "   deallocate(%s)"%(name) ]
        result.append(check_dimensions())
        result.append(do_allocate())
        result += [\
          "    if (irp_err /= 0) then",
          "     print *, irp_here//': Allocation failed: %s'"%(name),
          do_size(),
          "    endif",
          "   endif",
          "  endif",
          " else" ]
        result.append(check_dimensions())
        result.append(do_allocate())
        result += [\
          "    if (irp_err /= 0) then",
          "     print *, irp_here//': Allocation failed: %s'"%(name),
          do_size(),
          "    endif",
          "   endif",
          " endif" ]
        return result

      result = [ "subroutine provide_%s"%(name) ] 
      result += build_use( [same_as]+self.to_provide )
      result.append("  implicit none")
      length = len("provide_%s"%(name))
      result += [\
      "  character*(%d), parameter :: irp_here = 'provide_%s'"%(length,name),
      "  integer                   :: irp_err ",
      "  logical                   :: irp_dimensions_OK" ] 
      if command_line.do_assert or command_line.do_debug:
        result.append("  call irp_enter(irp_here)")
      result += call_provides(self.to_provide)
      result += flatten( map(build_alloc,[self.same_as]+self.others) )
      result += [\
      "  call bld_%s"%(same_as),
      "  %s_is_built = .True."%(same_as),
      "" ]
      if command_line.do_assert or command_line.do_debug:
        result.append("  call irp_leave(irp_here)")
      result.append("end subroutine provide_%s"%(name) )
      result.append("")
      self._provider = result
    return self._provider
  provider = property(provider)

  ##########################################################
  def builder(self):
    if '_builder' not in self.__dict__:
      if not self.is_main:
        self._builder = []
      else:
        import parsed_text
        from variables import build_use, call_provides
        for filename,buffer in parsed_text.parsed_text:
          if self.line.filename[0].startswith(filename):
            break
        text = []
        same_as = self.same_as
        inside = False
        for vars,line in buffer:
          if isinstance(line,Begin_provider):
            if line.filename[1] == same_as:
              inside = True
            vars = []
          if inside:
            text.append( (vars,line) )
            text += map( lambda x: ([],Simple_line(line.i,x,line.filename)), call_provides(vars) )
          if isinstance(line,End_provider):
            if inside:
              break
        name = self.name
        text = parsed_text.move_to_top(text,Declaration)
        text = parsed_text.move_to_top(text,Implicit)
        text = parsed_text.move_to_top(text,Use)
        text = map(lambda x: x[1], text)
        for line in filter(lambda x: type(x) not in [ Begin_doc, End_doc, Doc], text):
          if type(line) == Begin_provider:
            result = [ "subroutine bld_%s"%(name) ]
            result += build_use([name]+self.needs)
          elif type(line) == Cont_provider:
            pass
          elif type(line) == End_provider:
            result.append( "end subroutine bld_%s"%(name) )
            break
          else:
            result.append(line.text)
        self._builder = result
    return self._builder
  builder = property(builder)

  ##########################################################
  def children(self):
    if '_children' not in self.__dict__:
      if not self.is_main:
        self._children = []
      from variables import variables
      if '_needs' not in self.__dict__:
        import parsed_text
      result = []
      for x in self.needs:
        result.append(x)
        try:
          result += variables[x].children
        except RuntimeError:
          pass # Exception will be checked after
      self._children = make_single(result)
      if self.name in result:
        error.fail(self.line,"Cyclic dependencies:\n%s"%(str(self._children)))
    return self._children
  children = property(children)

  ##########################################################
  def parents(self):
    if '_parents' not in self.__dict__:
      if not self._is_main:
        self._parents = []
      else:
        from variables import variables
        if '_needed_by' not in self.__dict__:
          import parsed_text
        result = []
        for x in self.needed_by:
          result.append(x)
          try:
            result += variables[x].parents
          except RuntimeError:
            pass # Exception will be checked after
        self._parents = make_single(result)
        if self.name in result:
          error.fail(self.line,"Cyclic dependencies:\n%s"%(str(self._parents)))
    return self._parents
  parents = property(parents)

######################################################################
if __name__ == '__main__':
  from preprocessed_text import preprocessed_text
  from variables import variables
 #for v in variables.keys():
 #  print v
  for line in variables['e_loc'].parents:
    print line
