PYTHON=python2
PYVERSION=$(shell $(PYTHON) -c "import sys; print(sys.version[:3])")
HAS_CYTHON=$(shell bash -c "which cython &> /dev/null && echo 1 || echo 0")
ifneq ($(HAS_CYTHON),0)

../bin/irpf90: irpf90.so
	rm ../bin/irpf90 ; cd ../bin ; ln -s ../src/irpf90_python.exe irpf90

irpf90.so : $(wildcard *.py) irpf90.c
	./cython_setup.py build_ext --inplace

irpf90.c: irpf90.py
	cython --embed irpf90.py

else
../bin/irpf90: irpf90_python.exe
	rm ../bin/irpf90 ; cd ../bin ; ln -s ../src/irpf90_python.exe irpf90
endif

clean:
	rm -f *.c *.so *.pyc *.pyo 2>/dev/null
