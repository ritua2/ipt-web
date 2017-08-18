# Abaco actor to launch an IPT terminal job and store the URL and port back in the
#

import os
import paramiko
import StringIO

# get the username, container name and token out of the environment
user_name = os.environ.get('user_name')
container_name = os.environ.get('container_name')
token = os.environ.get("access_token")

# actual command to run on the execution host
command = 'cd /data/ipt/jobs/terminals/; ' \
          './wrapper.sh {} /data/ipt/storage/{}'.format(container_name, user_name)

# connection details about the execution host
# IP address of the execution host:
execution_ip = os.environ.get('execution_ip', '129.114.17.73')
execution_ssh_user = os.environ.get('execution_ssh_user', 'centos')
execution_ssh_key = os.environ.get('execution_ssh_key')

# instantiate an SSH client
ssh = paramiko.SSHClient()

# create an RSAKey object from the private key string.
pkey = paramiko.RSAKey.from_private_key(StringIO.StringIO(execution_ssh_key))

# ignore known_hosts errors:
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# connect to the execution system
ssh.connect(execution_ip, username=execution_ssh_user, pkey=pkey)

# run the command to launch the container
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)

# parse standard out for the port of the container:
# TODO