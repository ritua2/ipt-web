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
# ALL commands:
#    - execution_ssh_key (required): The KEY used to access the execution host(s).
#    - execution_ip and execution_ssh_user (optional): Connection information for the
#           execution host.
#    - user_name (required): The username to act on.
#    - ipt_instance (required): The IPT instance string (e.g. "dev" or "prod").
#    - access_token (required): An OAuth access token representing the user.
#    - api_server (optional): The Agave api_server to use.
#


import os
import paramiko
import StringIO

from agavepy.actors import get_context
from agavepy.agave import Agave

from models import TerminalMetadata

def get_ssh_connection(message):
    """Create an SSH connection to the execution host."""
    execution_ip = message.get('execution_ip', '129.114.17.73')
    execution_ssh_user = message.get('execution_ssh_user', 'centos')
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

def get_user_data(message):
    """Get the username, ipt_instance, container name and token."""
    user_name = message.get('user_name')
    ipt_instance = message.get('ipt_instance')
    container_name = '{}.{}.IPT'.format(user_name, ipt_instance)
    return user_name, container_name

def get_agave_client(message):
    """Instantiate an Agave client using the access token and api server in the message."""
    token = message.get("access_token")
    api_server = message.get("api_server", "https://api.tacc.utexas.edu")
    return Agave(api_server=api_server, token=token)

def launch_terminal(user_name, container_name, conn, ip):
    """Launch an IPT terminal application container."""
    command = 'cd /data/ipt/jobs/terminals/; ' \
              './wrapper.sh {} /data/ipt/storage/{}'.format(container_name, user_name)
    ssh_stdin, ssh_stdout, ssh_stderr = conn.exec_command(command)
    # TODO - parse standard error to ensure command was successful.
    # TODO - parse standard out for the port of the container:
    port = ssh_stdout.read()
    return "https://{}:{}".format(ip, port)

def stop_terminal(container_name, conn):
    """Stop and remove an IPT terminal application container."""
    command = 'docker rm -f {}'.format(container_name)
    _, ssh_stdout, ssh_stderr = conn.exec_command(command)
    # TODO - parse standard error to ensure command was successful.

def get_terminal_status(container_name, conn):
    command = 'docker ps -a {}'.format(container_name)
    ssh_stdin, ssh_stdout, ssh_stderr = conn.exec_command(command)
    # TODO - parse standard error to ensure command was successful.
    # TODO - parse standard out to get status of the container:


def main():
    context = get_context()
    message = context['message_dict']
    conn, ip = get_ssh_connection(message)
    user_name, container_name = get_user_data(message)
    ag = get_agave_client(message)
    m = TerminalMetadata(user_name, ag)
    command = message.get('command', 'START')
    if command == 'START':
        url = launch_terminal(user_name, container_name, conn, ip)
        m.set_ready(url)
    elif command == 'STOP':
        stop_terminal(container_name, conn)
        m.
    elif command == "SYNC":
        get_terminal_status()


if __name__ == "__main__":
    main()