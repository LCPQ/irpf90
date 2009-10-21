#!/usr/bin/python
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


def strip(x):
  return x.strip()

def lower(x):
  return x.lower()

def same_file(filename,txt):
  assert isinstance(filename,str)
  assert isinstance(txt,list)

  try:
    file = open(filename,"r")
  except IOError:
    return False
  stream = file.read()
  file.close()

  buffer = ''.join(txt)
 
  if len(stream) != len(buffer):
    return False
  if stream != buffer:
      return False
  return True

def build_dim(dim):
  if len(dim) == 0:
    return ""
  else:
    return "(%s)"%( ",".join(dim) )

def build_dim_colons(v):
  d = v.dim
  if d == []:
    return ""
  else:
    x = map(lambda x: ":", d)
    return "(%s)"%(','.join(x))


import error
def find_subname(line):
  buffer = line.text
  if not buffer.endswith(')'):
    buffer += "()"
  buffer = buffer.split('(')
  if len(buffer) > 1:
    buffer = " ".join(buffer[:-1])
  else:
    buffer = buffer[0]
  buffer = buffer.lower().split()
  if len(buffer) < 2:
    error.fail(line,"Syntax Error")
  return buffer[-1]

def make_single(l):
  d = {}
  for x in l:
   d[x] = True
  return d.keys()

def flatten(l):
  if isinstance(l,list):
    result = []
    for i in range(len(l)):
      elem = l[i]
      result += flatten(elem)
    return result
  else:
    return [l]

def dimsize(x):
  assert isinstance(x,str)
  buffer = x.split(':')
  if len(buffer) == 1:
    return x
    buffer = map(strip,buffer)
  else:
    assert len(buffer) == 2
    size = ""
    b0, b1 = buffer
    if b0.replace('-','').isdigit() and b1.replace('-','').isdigit():
      size = str( int(b1) - int(b0) + 1 )
    else:
      if b0.replace('-','').isdigit():
        size = "%s - (%d)"%(b1,int(b0)-1)
      elif b1.replace('-','').isdigit():
        size = "%d - %s"%(int(b1)+1,b0)
      else:
        size = "%s - %s + 1"%(b1,b0)
    return size

def put_info(text,filename):
  assert isinstance(text,list)
  if len(text) > 0:
    assert isinstance(text[0],tuple)
    from irpf90_t import Line
    assert isinstance(text[0][0],list)
    assert isinstance(text[0][1],Line)
    lenmax = 80 - len(filename)
    format = "%"+str(lenmax)+"s ! %s:%4s"
    for vars,line in text:
      line.text = format%(line.text.ljust(lenmax),line.filename,str(line.i))
  return text

if __name__ == '__main__':
  print "10",dimsize("10") #-> "10"
  print "0:10",dimsize("0:10") # -> "11"
  print "0:x",dimsize("0:x")  # -> "x+1"
  print "-3:x",dimsize("-3:x")  # -> "x+1"
  print "x:y",dimsize("x:y")  # -> "y-x+1"
  print "x:5",dimsize("x:5")  # -> "y-x+1"

