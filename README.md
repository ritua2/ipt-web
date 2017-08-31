
# IPT Web #

This is the main repository for assets related to web-based deployments of the Interactive Parallelization Tool (IPT).
For more information about IPT, see the literature (e.g. https://www.tacc.utexas.edu/documents/13601/1028648/paper_xsede_formatted.pdf)

## Development ##
First, clone this repository onto your local machine.
Starting the development stack requires Docker and docker-compose. Once Docker is installed on your system, build
the ipt-web image by executing the following from within the git project root:
  ```shell
  $ docker build -t jstubbs/ipt-web .
  ```

Next, generate self-signed certs (or download the ssl certs from the IPT/certs directory on UTBox) and place them
 in the `docker/nginx/ssl` directory within the repo.

You will also need to export some environment variables that contain Agave credentials, SSH keys, etc that cannot be
stored in the repository for security reasons. A set of these credentials is maintained in a stache entry called
"ipt-web credentials". Ask an IPT admin to share this stache entry with you, or generate your own Agave OAuth client,
SSH key, etc.

Once the variables are exported into a shell, run the stack using the docker-compose file:
   ```shell
   $ docker-compose up -d
   ```

Finally, modify your hosts file to point at the local stack by adding the following entry:
  ```shell
  127.0.0.1 ipt-web.tacc.utexas.edu
  ```

Navigate to https://ipt-web.tacc.utexas.edu to interact with your development stack.


### Agave Systems ###
For development, IPT uses a separate set of Agave storage and execution systems. Register these systems using the files
in the ~/agave/systems directory:
  * ipt-cloud-storage-dev.json
  * ipt-terminal-execution-dev.json

Use a command such as:

  ```shell
  >>> requests.post('https://api.tacc.utexas.edu/systems/v2', files={'fileToUpload': open('ipt-cloud-storage-dev.json')}, headers=headers)
  ```

Both hosts must be Docker hosts with the root directories created.
 
