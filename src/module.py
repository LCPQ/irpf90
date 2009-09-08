#!/usr/bin/python

from irpf90_t import *
from variable import *
from variables import variables
import preprocessed_text

class Fmodule(object):

  def __init__(self,text,filename):
    self.text = text
    self.name = "%s_mod"%(filename[:-6].lower())

  def put_info(text):
    if len(text) > 0:
      lenmax = 80 - len(filename)
      format = "%"+str(lenmax)+"s ! %s:%4s"
      for vars,line in text:
        line.text = format%(line.text.ljust(lenmax),line.filename,str(line.i))
    return text

  def is_main(self):
    if '_is_main' not in self.__dict__:
      self._is_main = self.prog_name is not None
    return self._is_main
  is_main = property(is_main)

  def prog_name(self):
    if '_prog_name' not in self.__dict__:
      buffer = filter(lambda x: isinstance(x[1],Program),self.text)
      if buffer == []:
        self._prog_name = None
      else:
        self._prog_name = buffer[0][1].filename
    return self._prog_name
  prog_name = property(prog_name)

  def variables(self):
    if '_variables' not in self.__dict__:
      from variables import variables
      name = self.name
      self._variables = filter(lambda x: variables[x].fmodule == name, variables)
    return self._variables
  variables = property(variables)

  def head(self):
    if '_head' not in self.__dict__:
      result = [ "module %s"%(self.name) ]
      result += self.use
      result += self.dec
      result.append( "end module %s"%(self.name) )
      self._head = result
    return self._head
  head = property(head)

  def needed_vars(self):
    if '_needed_vars' not in self.__dict__:
      result = map(lambda x: variables[x].needs,self.variables)
      result = make_single ( flatten(result) )
      self._needed_vars = result
    return self._needed_vars
  needed_vars = property(needed_vars)

  def generated_text(self):
    if '_generated_text' not in self.__dict__:
      result = []
      for var in self.variables:
        var = variables[var]
        result += var.provider
        result += var.builder
        if var.is_freed:
          result += var.free
        if var.is_touched:
          result += var.toucher
        if var.is_read:
          result += var.reader
        if var.is_written:
          result += var.writer
      self._generated_text = result
    return self._generated_text
  generated_text = property(generated_text)

  def residual_text(self):
    if '_residual_text' not in self.__dict__:
      from variables import build_use
      def remove_providers(text):
        result = []
        inside = False
        for vars,line in text:
          if isinstance(line,Begin_provider):
            inside = True
          if not inside:
            result.append( (vars,line) )
          if isinstance(line,End_provider):
            inside = False
        return result

      def modify_functions(text):
        result = []
        for vars,line in text:
          if type(line) in [ Subroutine, Function ]:
            variable_list = list(vars)
          elif isinstance(line,End):
            result += map(lambda x: ([],Use(line.i,x,line.filename)), build_use(variable_list))
          else:
            variable_list += vars
          result.append( (vars,line) )
        return result

      def extract_use_dec_text(text):
        inside = False
        result = []
        dec = []
        use = []
        for vars,line in text:
          if type(line) in [ Subroutine, Function]:
            inside = True
          if inside:
            result.append( (vars,line) )
          else:
            if isinstance(line,Use):
              use.append( (vars,line) )
            elif isinstance(line,Declaration):
              dec.append( (vars,line) )
          if isinstance(line,End):
            inside = False
        return use, dec, result

      result = remove_providers(self.text)
      result = modify_functions(result)
      result = preprocessed_text.move_to_top(result,Declaration)
      result = preprocessed_text.move_to_top(result,Use)
      use,dec,result = extract_use_dec_text(result)
      self._use = make_single(map(lambda x: " "+x[1].text, use))
      self._dec = make_single(map(lambda x: " "+x[1].text, dec))
      result    = map(lambda x: " "+x[1].text, result)
      if self.is_main:
        result = [ \
        "program irp_program",
        " call %s"%(self.prog_name),
        "end irp_program",
        ] + result
      self._residual_text = result
    return self._residual_text
  residual_text = property(residual_text)

  def use(self):
    if '_use' not in self.__dict__:
      self.residual_text
    return self._use
  use = property(use)

  def dec(self):
    if '_dec' not in self.__dict__:
      self.residual_text
    return self._dec
  dec = property(dec)

  def needed_modules(self):
    if '_needed_modules' not in self.__dict__:
      buffer = filter(lambda x: isinstance(x,Use), self.generated_text)
      buffer = map(lambda x: x.text.split()[1].lower(), buffer)
      self._needed_modules = make_single(buffer)
    return self._needed_modules
  needed_modules = property(needed_modules)

if __name__ == '__main__':
  from parsed_text import parsed_text
  for filename, text in parsed_text:
    if filename == 'random.irp.f':
     x = Fmodule(text,filename)
     break
  for line in x.residual_text:
    print line
