#!/bin/bash
#
# Wrapper script for the IPT build Agave application. The purpose of this application
# is to compile an IPT-generated source code using standard tools such as mpicc.
#

# first, load custom modules, if applicable.
if [ -n "${modules}" ]; then
    # multiple modules could be passed in
	for i in ${dataset}; do
        module load "$i"
    done
fi

# run the actual compile command
${command} ${driver} -o ${output} ${args}

