
# IPT on the Web #

This is the main repository for assets related to IPT on the Web: a web-accessible version of the Interactive Parallelization Tool (IPT).
For more information about the IPT command line tool, see the literature (e.g. https://www.tacc.utexas.edu/documents/13601/1028648/paper_xsede_formatted.pdf)

## Background and Architecture ##

IPT on the Web is an interactive computing environment mixing traditional HPC and web technologies. The web application
provides users with an isolated IPT shell running on an execution cluster as well as web forms for launching IPT
related jobs on machines like Stampede. Job execution and history is managed by the Agave API while management of the
IPT terminals on the cluster is handled by an actor registered with the Abaco API. State associated with the terminal
shells is stored in Agave's metadata service. As a result, the IPT web application itself is entirely stateless. At a high
level, the architecture is:
* Stateless IPT Django application (`ipt-web`) uses TACC OAuth for authorization.
* `ipt-web` makes calls to an Abaco actor (`ipt-actor`) to start and stop IPT terminals running in Docker containers on a configurable compute cluster.
* `ipt-web` and `ipt-actor` communicate state about the terminals (e.g. their status and URL) via the Agave metadata service.


## Development ##
Starting a development stack on your local machine can be done with the following steps:

1. Clone this repository onto your local machine.

2. Install Docker and docker-compose.

3. Generate self-signed certs (or download the ssl certs from the IPT/certs directory on UTBox) and place them
 in the `docker/nginx/ssl` directory within the repo.

4. Export secrets to the environment. You will to export the AGAVE_CLIENT_SECRET and AGAVE_SERVICE_TOKEN to the
environment, as these values are not stored in the repository for security reasons. A valid set of values for these
 variables is maintained in a stache entry called "ipt-web credentials".

5. Modify your hosts file to point at the local stack by adding the following entry:

  ```
  127.0.0.1 ipt-web.tacc.utexas.edu
  ```

6. Run the stack using the docker-compose file by issuing the following command in the project root:

   ```
   $ docker-compose up -d
   ```

Navigate to https://ipt-web.tacc.utexas.edu to interact with your development stack.


### Building the Images ###
If you want to modify the source code and see your changes in the local development stack, you will need to rebuild
one or more images, depending on what you have modified.

The `ipt-web` image contains the Django application. Rebuild the image by executing the following from within the git project
root:

  ```
  $ docker build -t jstubbs/ipt-web .
  ```

Each time new images are built, run the following commands to regenerate your dev stack

  ```
  $ docker-compose down
  $ docker-compose up -d
  ```


The `ipt-actor` image is responsible for managing the terminals on the cluster. It takes a `command` variable to know
what to do. Its source code is contained in the `actor` directory within the main `iptweb` directory. To rebuild the
actor image, execute the following from within the `iptweb` directory:

  ```
  $ docker build -f Dockerfile-actor -t jstubbs/ipt-actor .
  ```

The actor must also be re-registered with the Abaco API. To re-register the actor, delete and add it using (note the
values in the default environment; the SSH KEY is stored in a stache entry called "ipt-actor"):

  ```
  >>> ag.actors.delete(actorId=current_actor_id)
  >>> body = {'default_environment': {'execution_ip': '129.114.17.73', 'execution_ssh_key': '..', ipt_instance': 'dev'}, 'image': 'jstubbs/ipt-actor', 'name': 'IPT-dev-actor'}
  >>> ag.actors.add(body=body)
  ```

The Abaco API returns a new uuid for the actor. Update the docker-compose.yml file ACTOR_ID variable with this new uuid.


### Admin Tab ###

The IPT web application provides an Admin tab for managing the IPT terminals on the cluster. The tab will show up if your
username is in the ADMIN_USERS list in the settings.py file.


### Webterm API ###

In addition to the web application, the Django code contains a small API at `/webterm` for providing the terminal
metadata associated with the logged in user. Only the GET method is supported and JSON is returned.


### Turning off Calls to the Actor ###

Using the actor to execute terminals on the cluster requires a SERVICE_TOKEN representing a privileged
user. If you do not have such a service token or want to skip calls to the Abaco API set the

  ```
  CALL_ACTOR = False
  ```

in the Django settings file.


### Manually Managing the Webterm ###

If you have turned off calls to the actor, you can still manage a webterm manually on your laptop. Use
the following commands:

#### Start a New Webterm ####

To start a new IPT webterm, run:

  ```
  docker run --name <your_username>.dev.IPT -p 3000 -dt -v $(pwd)/docker/nginx/ssl:/ssl jstubbs/ipt-webterm /app/app.js --urlPath /test --sslkey /ssl/ipt-web.tacc.utexas.edu.key --sslcert /ssl/ipt-web.tacc.utexas.edu.bundle.crt -p 3000
  ```

This should start a terminal in a docker container on a high random port. Use `docker ps` to see which
port was used.


#### Modify Associated Metadata ####

To set the metadata so that your development stack renders the terminal, use the agavepy SDK
and the TerminalMetadata model defined in the iptsite models like so:

  ```
  >>> from agavepy.agave import Agave
  >>> ag = Agave(api_server='https://api.tacc.utexas.edu', token='<your_token>')
  >>> from models import TerminalMetadata
  >>> t = TerminalMetadata('<your_username>', ag)
  >>> t.set_ready('https://ipt-web.tacc.utexas.edu:<your_port>')
  ```

### Agave Systems ###
IPT on the Web uses Agave storage and execution systems to launch jobs to build IPT generated source
codes and run test jobs of the binaries.

For development, IPT uses a separate set of Agave storage and execution systems. Register these systems using the files
in the ~/agave/systems directory:
  * ipt-cloud-storage-dev.json
  * ipt-terminal-execution-dev.json

Use a command such as:

  ```
  >>> requests.post('https://api.tacc.utexas.edu/systems/v2', files={'fileToUpload': open('ipt-cloud-storage-dev.json')}, headers=headers)
  ```

Both hosts must be Docker hosts with the root directories created.
 
