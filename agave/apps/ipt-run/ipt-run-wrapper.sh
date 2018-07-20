#!/bin/bash
#
# Wrapper script for the IPT build Agave application. The purpose of this application
# is to compile an IPT-generated source code using standard tools such as mpicc.
#

echo "supp files: ${supplemental-files}"
echo "binary: ${binary}"
echo "command: ${command}"
echo "batchQueue: ${batchQueue}"
echo "number of cores: ${processorsPerNode}"
echo "number of nodes: ${nodeCount}"
echo "estimate runtime: ${runtime}"
echo "args: ${args}"
echo "modules: ${modules}"

# first, load custom modules, if applicable.
if [ -n "${modules}" ]; then
    # multiple modules could be passed in
	for i in ${modules}; do
        echo loading "$i"
        module load "$i"
    done
fi

if [ "${command}" = "./" ]; then
    echo "${command} = ./"
    FULL_COMMAND="${command}${binary}"
elif [[ "${command}" = *./* ]]; then
    echo "${command} =*./*"
    FULL_COMMAND="${command}"
else
    echo "else"
    FULL_COMMAND="${command} ./${binary}"
fi

if [ "${binary}" ]; then
  chmod +x ${binary}
fi

echo "full command: $FULL_COMMAND"
$FULL_COMMAND
