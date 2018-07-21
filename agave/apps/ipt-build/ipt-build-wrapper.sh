#!/bin/bash
#
# Wrapper script for the IPT build Agave application. The purpose of this application
# is to compile an IPT-generated source code using standard tools such as mpicc.
#

#for testing while running in vm
#################################
# PATH=$PATH:/bin:/usr/bin/ipt-temp
#################################

# first, load custom modules, if applicable.
if [ -n "${modules}" ]; then
    # multiple modules could be passed in
	for i in ${modules}; do
        echo loading "$i"
        module load "$i"
    done
fi

echo "modules: ${modules}"
echo "supp files: ${supplemental-files}"
echo "driver: ${driver}"
echo "command: ${command}"
echo "full command: ${command} ${driver} -o ${output} ${args} ${supplemental-files}"

# run the actual compile command
${command} ${driver} -o ${output} ${args} ${supplemental-files}
chmod +x ${output} #doesn't work
