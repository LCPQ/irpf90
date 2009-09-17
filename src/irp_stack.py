#!/usr/bin/python

import util 
from command_line import command_line

do_assert = command_line.do_assert
do_debug = command_line.do_debug

import irpf90_t

FILENAME = irpf90_t.irpdir+"irp_stack.irp.F90"

def create():

  txt = """
module irp_stack_mod
  integer, parameter            :: STACKMAX=1000
  character*(128),allocatable   :: irp_stack(:,:)
  double precision,allocatable  :: irp_cpu(:,:)
  integer,allocatable           :: stack_index(:)
  logical                       :: alloc = .False.
  character*(128)               :: white = ''
end module

subroutine irp_enter(irp_where)
 use irp_stack_mod
 integer       :: ithread
 integer       :: nthread
 character*(*) :: irp_where
 ithread = 0
 nthread = 1
$1
$2
end subroutine

subroutine irp_leave (irp_where)
 use irp_stack_mod
  character*(*) :: irp_where
  integer       :: ithread
  double precision :: cpu
  ithread = 0
$3
$4
end subroutine
"""

  # $1
  if do_assert or do_debug:
    txt = txt.replace("$1","""
!$OMP CRITICAL
 if (.not.alloc) then
   allocate(irp_stack(STACKMAX,nthread))
   allocate(irp_cpu(STACKMAX,nthread))
   allocate(stack_index(nthread))
   alloc = .True.
 endif
!$OMP END CRITICAL
 stack_index(ithread+1) = stack_index(ithread+1)+1
 irp_stack(stack_index(ithread+1),ithread+1) = irp_where""")
  else:
    txt = txt.replace("$1","")

  # $2
  if do_debug:
    txt = txt.replace("$2","""
  print *, ithread, ':', white(1:stack_index(ithread+1))//'-> ', trim(irp_where)
  call cpu_time(irp_cpu(stack_index(ithread+1),ithread+1))""")
  else:
    txt = txt.replace("$2","")

  # $3
  if do_debug:
    txt = txt.replace("$3","""
  call cpu_time(cpu)
  print *, ithread, ':', white(1:stack_index(ithread+1))//'<- ', &
    trim(irp_stack(stack_index(ithread+1),ithread+1)), &
    cpu-irp_cpu(stack_index(ithread+1),ithread+1)""")
  else:
    txt = txt.replace("$3","")

  # $4
  if do_debug or do_assert:
    txt = txt.replace("$4","""
  stack_index(ithread+1) = stack_index(ithread+1)-1""")
  else:
    txt = txt.replace("$4","")

  if do_debug or do_assert:
    txt += """
subroutine irp_trace
 use irp_stack_mod
 integer :: ithread
 integer :: i
 ithread = 0
 if (.not.alloc) return
 print *, 'Stack trace: ', ithread
 print *, '-------------------------'
 do i=1,stack_index(ithread+1)
  print *, trim(irp_stack(i,ithread+1))
 enddo
 print *, '-------------------------'
end subroutine
"""

  txt = txt.split('\n')
  txt = map(lambda x: x+"\n",txt)
  if not util.same_file(FILENAME, txt):
    file = open(FILENAME,'w')
    file.writelines(txt)
    file.close()


