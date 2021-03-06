# Abaco actor to manage IPT terminals and associated metadata.
# Supports the following actions, specified by passing the following values in the
# "command" string:
#    1. START - Start a new IPT terminal for a user.
#    2. STOP  - Stop and remove the IPT terminal container associated with a user.
#    3. SYNC  - Sync the metadata record with the existing state of the terminal container
#               associated with a user. The IPT existence of an IPT container or its state
#               will not be affected by this command; only the metadata record will be
#               modified.
#
# Required parameters. The following parameters should be registered in the actor's default
# environment or passed in the JSON message when executing the actor. This actor looks
# in the context created by the Abaco SDK for these values.
#
# PASSED IN AT REGISTRATION (these can be overritten at run time):
#    - execution_ssh_key (required): The KEY used to access the execution host(s).
#    - ipt_instance (required): The IPT instance string (e.g. "dev" or "prod").

# PARAMETERS to ALL commands:
#    - user_name (required): The username to act on.
#    - access_token (required): An OAuth access token representing the user.
#    - command (optional, defaults to START): the command to use.
#    - execution_ip and execution_ssh_user (optional): Connection information for the
#           execution host.
#    - api_server (optional): The Agave api_server to use.
#
# Building the image:
#    docker build -t taccsciapps/ipt-actor -f Dockerfile-actor .
#
# Testing locally:
#    docker run -it --rm -e MSG='{...}' taccsciapps/ipt-actor

import os
import sys
import paramiko
import random
import string
import StringIO

from agavepy.actors import get_context
from agavepy.agave import Agave

from models import TerminalMetadata

def audit_required_fields(context, message):
    print("context: {}".format(context))
    print("message: {}".format(message))
    if not message.get('execution_ssh_key'):
        if not context.get('execution_ssh_key'):
            print("Missing SSH key. message: {}".format(message))
            sys.exit(1)
    if not message.get("user_name"):
        print("Missing user_name. message: {}".format(message))
        sys.exit(1)
    if not message.get("access_token"):
        print("Missing access_token. message: {}".format(message))
        sys.exit(1)
    print("All required fields passed. message: {}".format(message))

def get_ssh_connection(context, message):
    """Create an SSH connection to the execution host."""
    execution_ip = context.get('execution_ip', '129.114.17.63')
    if message.get('execution_ip'):
        execution_ip = message.get('execution_ip', '129.114.17.63')
    execution_ssh_user = context.get('execution_ssh_user', 'root')
    if message.get('execution_ssh_user'):
        execution_ssh_user = message.get('execution_ssh_user')
    execution_ssh_key = context.get('execution_ssh_key')
    if message.get('execution_ssh_key'):
        execution_ssh_key = message.get('execution_ssh_key')
    # instantiate an SSH client
    ssh = paramiko.SSHClient()
    # create an RSAKey object from the private key string.
    pkey = paramiko.RSAKey.from_private_key(StringIO.StringIO(execution_ssh_key))
    # ignore known_hosts errors:
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # connect to the execution system
    ssh.connect(execution_ip, username=execution_ssh_user, pkey=pkey)
    return ssh, execution_ip

def get_user_data(context, message):
    """Get the username, ipt_instance, container name and token."""
    ipt_instance = context.get('ipt_instance')
    if message.get('ipt_instance'):
        ipt_instance = message.get('ipt_instance')
    user_name = message.get('user_name')

    container_name = '{}-{}-IPT'.format(user_name, ipt_instance)
    return user_name, container_name

def get_agave_client(message):
    """Instantiate an Agave client using the access token and api server in the message."""
    token = message.get("access_token")
    api_server = message.get("api_server", "https://api.tacc.utexas.edu")
    return Agave(api_server=api_server, token=token)

def launch_terminal(user_name, container_name, conn, ip):
    """Launch an IPT terminal application container."""
    password = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(27))
    command = 'cd /data/ipt/jobs/terminals/; ' \
              './wrapper.sh {} /gpfs/corral3/repl/utexas/ipt_storage/{} {}'.format(container_name, user_name, password)
    print("command: {}".format(command))
    ssh_stdin, ssh_stdout, ssh_stderr = conn.exec_command(command)
    print("ssh connection made and command executed")
    # TODO - parse standard error to ensure command was successful.
    st_out = ssh_stdout.read()
    print("st out from command: {}".format(st_out))
    #
    try:
        # port = st_out.split('0.0.0.0:')[1]
        port = st_out.splitlines()[1]
    except IndexError:
        print("There was an IndexError parsing the standard out of the terminal launch for the port. "
              "Standard out was: {}".format(st_out))
        return ""
    print("got a port: {}".format(port))
    url = "https://{}:{}/{}".format('ipt-compute.tacc.cloud', port, password).replace('\n', '')
    print("returning url: {}".format(url))
    return url

def stop_terminal(container_name, conn):
    """Stop and remove an IPT terminal application container."""
    command = 'docker service rm {}'.format(container_name)
    _, ssh_stdout, ssh_stderr = conn.exec_command(command)

def get_terminal_status(container_name, conn):
    command = 'docker ps -a {}'.format(container_name)
    ssh_stdin, ssh_stdout, ssh_stderr = conn.exec_command(command)
    # TODO - parse standard error to ensure command was successful.
    # TODO - parse standard out to get status of the container:


def main():
    context = get_context()
    message = context['message_dict']
    audit_required_fields(context, message)
    conn, ip = get_ssh_connection(context, message)
    user_name, container_name = get_user_data(context, message)
    ag = get_agave_client(message)
    m = TerminalMetadata(user_name, ag)
    command = message.get('command', 'START')
    if command == 'START':
        url = launch_terminal(user_name, container_name, conn, ip)
        if not url:
            m.set_error("Actor got an error trying to launch terminal. Check the logs")
        else:
            print("Setting actor to ready status for URL: {}".format(url))
            m.set_ready(url)
            print("Status updated. Actor exiting.")
    elif command == 'STOP':
        stop_terminal(container_name, conn)
        m.set_stopped()
    elif command == "SYNC":
        get_terminal_status()


if __name__ == "__main__":
    main()
