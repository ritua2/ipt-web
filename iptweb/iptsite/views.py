import os
import urllib
import inspect

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

from datetime import datetime

from agavepy.agave import Agave
from django.shortcuts import render, redirect, reverse
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, JsonResponse, FileResponse

from models import is_ipt_meta, get_user, TerminalMetadata, IPTError, IPTModelError
from django.core.files.uploadhandler import MemoryFileUploadHandler, TemporaryFileUploadHandler
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from zipfile import ZipFile
import StringIO
import shutil
import json
from messageBoard.models import Newscollection
from django.views.generic.edit import DeleteView, CreateView
from .forms import NewsForm


AGAVE_STORAGE_SYSTEM_ID = os.environ.get('AGAVE_STORAGE_SYSTEM_ID', 'dev.ipt.cloud.storage')

SYSTEMS = {
    'stampede':{
        'display_name': 'Stampede 2',
        'build': {
            'app': settings.STAMPEDE_BUILD_APP_VERSION,
            'system': 'ipt.build.stampede',
        },
        'run': {
            'app': settings.STAMPEDE_RUN_APP_VERSION,
            'system': 'ipt.run.stampede',
        },
        'queues':(
            'normal',
            'development',
            'flat-quadrant',
            'skx-dev',
            'skx-normal',
        )
    },
    'ls5':{
        'display_name': 'Lonestar 5',
        'build': {
            'app': settings.LS5_BUILD_APP_VERSION,
            'system': 'ipt.build.ls5',
        },
        'run': {
            'app': settings.LS5_RUN_APP_VERSION,
            'system': 'ipt.run.ls5',
        },
        'queues':(
            'normal',
            'development',
            'gpu',
            'vis',
        )
    },
    'comet':{
        'display_name': 'Comet',
        'build': {
            'app': settings.COMET_BUILD_APP_VERSION,
            'system': 'ipt.build.comet',
        },
        'run': {
            'app': settings.COMET_RUN_APP_VERSION,
            'system': 'ipt.run.comet',
        },
        'queues':(
            'gpu-shared',
            'gpu',
            'debug',
            'compute',
        )
    },
}

def get_agave_exception_content(e):
    """Check if an Agave exception has content"""
    try:
        return e.response.content
    except Exception:
        return ""


def format_path(path):
    if path.startswith('/home/ipt/'):
        return path[10:]
    elif path.startswith('~/'):
        return path[2:]
    return path

def get_request():
    """Walk up the stack, return the nearest first argument named "request"."""
    frame = None
    try:
        for f in inspect.stack()[1:]:
            frame = f[0]
            code = frame.f_code
            if code.co_varnames and code.co_varnames[0] == "request":
                request = frame.f_locals['request']
    finally:
        del frame
    return request

def update_session_tokens(**kwargs):
    """Update the request's session with the latest tokens since the client may have
    automatically refreshed them."""

    request = get_request()
    logger.info('request.session access_token before refreshing: {}'.format(request.session.get('access_token')))
    logger.info('request.session refresh_token before refreshing: {}'.format(request.session.get('refresh_token')))
    request.session['access_token'] = kwargs['access_token']
    request.session['refresh_token'] = kwargs['refresh_token']
    logger.info('request.session access_token after refreshing: {}'.format(request.session.get('access_token')))
    logger.info('request.session refresh_token after refreshing: {}'.format(request.session.get('refresh_token')))


def get_service_client():
    """Returns an agave client representing the service account. This client can be used to access
    the authorized endpoints such as the abaco endpoint."""
    if not settings.CALL_ACTOR:
        logger.debug("Skipping call to actor since settings.CALL_ACTOR was False.")
    service_token = os.environ.get('AGAVE_SERVICE_TOKEN')
    if not service_token:
        raise Exception("Missing SERVICE_TOKEN configuration.")
    base_url = os.environ.get('AGAVE_BASE_URL', "https://api.tacc.utexas.edu")
    return Agave(api_server=base_url, token=service_token)

def call_actor(request, user_name=None, command="START"):
    """Call the actor function to manage a user's terminal session. Assumes the request has a valid
    authentication session.
    """
    # we'll send the user's access token and base_url to the actor so for updating the
    # TerminalMetadata record
    access_token = request.session.get("access_token")
    if not user_name:
        user_name = request.session['username']
    base_url = os.environ.get('AGAVE_BASE_URL', "https://api.tacc.utexas.edu")
    if not access_token or not user_name:
        raise Exception("authentication required for calling actor.")
    logger.info("Calling actor for command: {}, user: {}".format(command, user_name))
    ag2 = get_service_client()
    # for STOP commands coming from the Admin tab, we need to use the service token to prevent the actor
    # from creating a metadata record owned by the admin user.
    if command == 'STOP':
        access_token = os.environ.get('AGAVE_SERVICE_TOKEN')
    actor_id = os.environ.get('ACTOR_ID')
    if not actor_id:
        raise Exception("Missing ACTOR_ID configuration.")
    # build a message with the basic parameters needed by the actor
    message = {'access_token': access_token,
               'user_name': user_name,
               'command': command,
               'api_server': base_url
               }
    # grab original status and update status to submitted:
    t = TerminalMetadata(user_name, ag2)
    old_status = t.get_status()
    t.set_submitted()

    # execute actor:
    try:
        rsp = ag2.actors.sendMessage(actorId=actor_id, body={'message': message})
    except Exception as e:
        msg = "Error executing actor. Execption: {}. Content: {}".format(e, get_agave_exception_content(e))
        logger.error(msg)
        if old_status == TerminalMetadata.error_status:
            t.set_error()
        elif old_status == TerminalMetadata.ready_status:
            t.set_ready()
        elif old_status == TerminalMetadata.stopped_status:
            t.set_stopped()
        elif old_status == TerminalMetadata.pending_status:
            t.set_pending()
        raise Exception(msg)
    logger.info("Called actor {}. Message: {}. Response: {}".format(actor_id, message, rsp))

def check_for_tokens(request):
    access_token = request.session.get("access_token")
    if access_token:
        return True
    return False

def check_for_terminal(request):
    """ Check to determine if a user has a terminal session submitted and submit one if not. This
    method should only be called once the user has logged in and has tokens in their session.
    """
    username = request.session.get('username')
    # first, make sure the user's directory is in place. use the service token to make these calls:
    ag2 = get_service_client()
    try:
        ag2.files.manage(systemId=AGAVE_STORAGE_SYSTEM_ID, filePath='/', body={'action': 'mkdir', 'path': username})
    except Exception as e:
        logger.error("Failed to create user directory for user {}. Exception: {}".format(username, e))

    # use the user's token to work with the metadata
    ag = get_agave_client_session(request)
    try:
        m = TerminalMetadata(username, ag)
    except IPTModelError as e:
        try:
            token_info = ag.token.token_info
        except Exception as e:
            token_info = "Unable to pull token info: {}".format(e)
        raise IPTModelError("{}. Access token used: {}".format(e.message, token_info))
    if m.value['status'] == m.pending_status or m.value['status'] == m.stopped_status:
        call_actor(request)
    return m.value

def get_agave_client(username, password):
    client_key = os.environ.get('AGAVE_CLIENT_KEY')
    client_secret = os.environ.get('AGAVE_CLIENT_SECRET')
    base_url = os.environ.get('AGAVE_BASE_URL', "https://api.tacc.utexas.edu")
    if not client_key or not client_secret:
        raise Exception("Missing OAuth client credentials.")
    return Agave(api_server=base_url, username=username, password=password, client_name="ipt", api_key=client_key,
                 api_secret=client_secret, token_callback=update_session_tokens)

def get_agave_client_tokens(access_token, refresh_token):
    client_key = os.environ.get('AGAVE_CLIENT_KEY')
    client_secret = os.environ.get('AGAVE_CLIENT_SECRET')
    base_url = os.environ.get('AGAVE_BASE_URL', "https://api.tacc.utexas.edu")
    if not client_key:
        raise Exception("Missing OAuth client key.")
    if not client_secret:
        raise Exception("Missing OAuth client secret.")
    return Agave(api_server=base_url, token=access_token, refresh_token=refresh_token, client_name="ipt",
                api_key=client_key, api_secret=client_secret, token_callback=update_session_tokens)


def get_agave_client_session(request):
    """Return an instantiated Agave client using data from an authenticated session."""
    # grab tokens for session authorization
    access_token = request.session.get("access_token")
    refresh_token = request.session.get("refresh_token")
    # token_exp = ag.token.token_info['expires_at']
    return get_agave_client_tokens(access_token, refresh_token)


def is_admin(user_name):
    return user_name in settings.ADMIN_USERS


# VIEWS

def admin(request):
    """List all current users and the status of their terminal sessions."""
    if not check_for_tokens(request):
        return redirect(reverse("login"))
    user_name = request.session.get("username")
    if not is_admin(user_name):
        return HttpResponse('Unauthorized', status=401)
    ag = get_service_client()
    if request.method == 'POST':
        # admin is requesting a change to this user. Need to first put the metadata record in status
        # SUBMITTED so that no additional changes are made.
        pending_user = request.POST.get('user')
        call_actor(request, user_name=request.POST.get('user'), command=request.POST.get('command'))
        return redirect(reverse("admin"))

    metas = ag.meta.listMetadata()
    terminals = []
    for m in metas:
        if is_ipt_meta(m):
            value = m.get('value')
            user = get_user(value.get('name'))
            action = None
            submit = None
            if (value.get('status') == TerminalMetadata.ready_status or
                value.get('status') == TerminalMetadata.error_status):
                action = 'STOP'
                submit = 'Stop'
            terminals.append({'user': user,
                              'name': value.get('name'),
                              'status': value.get('status'),
                              'url': value.get('url'),
                              'uuid': m['uuid'],
                              'action': action,
                              'submit': submit})
    return render(request, 'iptsite/admin.html',
                  context={'admin': True,
                           'terminals': terminals,
                           "loggedinusername": user_name
                           },
                  content_type='text/html')

def history(request):
    """
    This view generates the Job history page.
    """
    if not check_for_tokens(request):
        return redirect(reverse("login"))
    user_name = request.session.get("username")
    ag = get_agave_client_session(request)

    if request.method == 'GET':
        try:
            jobs = ag.jobs.list()
            context = {"jobs": jobs, "admin": is_admin(user_name), "loggedinusername": user_name}
            return render(request, 'iptsite/history.html', context, content_type='text/html')
        except Exception as e:
            # raise e
            msg = "Error uploading file. Exception: {}".format(e)
            logger.error(msg)
            messages.error(request, msg)

def run(request):
    """
    This view generates the Run page.
    """
    # if tokens for valid session aren't there, redirect user to login page
    if not check_for_tokens(request):
        return redirect(reverse("login"))
    user_name = request.session.get("username")

    context = {
        "admin": is_admin(user_name),
        "systems": SYSTEMS,
        "loggedinusername": user_name
    }

    if request.method == 'POST':
        system = request.POST.get('system')
        rcommand = request.POST.get('rcommand')
        jobq = request.POST.get('jobq')
        numcores = request.POST.get('numcores')
        numnodes = request.POST.get('numnodes')
        estrun = request.POST.get('estrun')
        allocnum = request.POST.get('allocnum')
        binary = request.POST.get('binary')
        addfiles = request.POST.get('addfiles')
        modules = request.POST.get('modules')
        rcommandargs = request.POST.get('rcommandargs')

        context['system'] = system
        context['rcommand'] = rcommand
        context['jobq'] = jobq
        context['numcores'] = numcores
        context['numnodes'] = numnodes
        context['estrun'] = estrun
        context['allocnum'] = allocnum
        context['binary'] = binary
        context['addfiles'] = addfiles
        context['modules'] = modules
        context['rcommandargs'] = rcommandargs

        if not rcommand:
            context["run_command_error"] = "Command cannot be blank"
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not jobq:
            context["job_queue_error"] = "Job Queue cannot be blank"
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not numcores:
            context["num_cores_error"] = "Number of Cores cannot be blank"
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not numnodes:
            context["num_nodes_error"] = "Number of Nodes cannot be blank"
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        # if not estrun:
        #     context["est_run_error"] = "Estimated Job Runtime cannot be blank"
        #     return render(request, 'iptsite/run.html', context, content_type='text/html')
        # if not allocnum:
        #     context = {"alloc_num_error": "Allocation Number cannot be blank"}
        #     return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not binary:
            context["binary_error"] = "Binary cannot be blank"
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        # if not run_additional_files:
        # context = {"run_additional_files_error": ""}

        # if not rcommandargs:
        #     context = {"run_command_args": "Command Args cannot be blank"}
        #     return render(request, 'iptsite/run.html', context, content_type='text/html')
        binary_path = format_path(binary)
        binary = 'agave://{}/{}/{}'.format(AGAVE_STORAGE_SYSTEM_ID, user_name, binary_path)

        job_dict = {
            "name": "{}.run.ipt".format(user_name),
            # "appId": settings.RUN_APP_VERSION,
            "inputs": {
                "binary": binary,
            },
            "nodeCount": numnodes,
            "processorsPerNode": numcores,
            "archive": True,
            "archiveSystem": AGAVE_STORAGE_SYSTEM_ID,
            "archivePath": '{}/jobs/{}/run-{}-${{JOB_ID}}'.format(
                user_name,
                datetime.now().strftime('%Y-%m-%d'),
                system),
            "parameters": {
                "command": rcommand,
                "batchQueue": jobq,
                "processorsPerNode": numcores,
                "nodeCount": numnodes,
            }
        }

        try:
            job_dict['appId'] = SYSTEMS[system]['run']['app']
        except KeyError:
            logger.error('Build app not found for {}'.format(system))

        if addfiles:
            addfiles.rstrip(',')
            supplemental_files = []
            files = addfiles.split(',')
            for f in files:
                f=f.strip()
                f=format_path(f)
                supplemental_files.append('agave://{}/{}/{}'.format(AGAVE_STORAGE_SYSTEM_ID, user_name, f))
            job_dict['inputs']['supplemental-files'] = supplemental_files
        if modules:
            modules_list = []
            mods = modules.split(',')
            for m in mods:
                m=m.strip()
                modules_list.append(m)
            job_dict['parameters']['modules'] = modules_list
        if rcommandargs:
            job_dict['parameters']['args'] = rcommandargs

        ag = get_agave_client_session(request)

        try:
            # submit job dictionary
            logger.info('Job Submission Body: {}'.format(job_dict))
            response = ag.jobs.submit(body=job_dict)
            logger.info('Job Submission Response: {}'.format(response))
            messages.success(request, 'Job {} has been submitted.'.format(response.id))
            return HttpResponseRedirect('run')
        except Exception as e:
            err_resp = e.response.json()
            err_resp['status_code'] = e.response.status_code
            logger.warning(err_resp)
            messages.error(request, "Error submitting job: {}, {}".format(e, e.response.content))
            return render(request, 'iptsite/run.html', context, content_type='text/html')

    elif request.method == 'GET':
        return render(request, 'iptsite/run.html', context, content_type='text/html')


def help(request):
    """
    This view generates the Help page.
    """
    user_name = request.session.get("username")
    context = {"admin": is_admin(user_name), "loggedinusername": user_name}
    if request.method == 'GET':
        return render(request, 'iptsite/help.html', context, content_type='text/html')
#Added by Thomas Hilton Johnson III, for quick refernece if there is a bug
#def news(request):
#    """
#    This view generates the news page.
#    """
#    user_name = request.session.get("username")
#    context = {"admin": is_admin(user_name), "loggedinusername": user_name}
#    if request.method == 'GET':
#        return render(request, 'iptsite/news.html', context, content_type='text/html')


def login(request):
    """
    This view generates the User Login page.
    """
    n = Newscollection.objects.all()
    # check if user already has a valid auth session just redirect them to terminal page
    if check_for_tokens(request):
        return redirect(reverse("terminal"))

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username:
            context = {"error": "Username cannot be blank",
                        'news': n }
            return render(request, 'iptsite/login.html', context, content_type='text/html')

        if not password:
            context = {"error": "Password cannot be blank",
                        'news': n }
            return render(request, 'iptsite/login.html', context, content_type='text/html')

        try:
            ag = get_agave_client(username, password)
        except Exception as e:
            # render login template with an error
            context = {"error": "Invalid username or password: {}".format(e),
                        'news': n }
            return render(request, 'iptsite/login.html', context, content_type='text/html')

        try:
            #user needs to have permissions on both the system and app
            service_ag = get_service_client()
            service_ag.systems.updateRoleForUser(systemId=AGAVE_STORAGE_SYSTEM_ID, username=username, body={'role': 'USER'})
            for sys in SYSTEMS:
                service_ag.systems.updateRoleForUser(systemId=SYSTEMS[sys]['build']['system'], username=username, body={'role': 'USER'})
                service_ag.systems.updateRoleForUser(systemId=SYSTEMS[sys]['run']['system'], username=username, body={'role': 'USER'})
                service_ag.apps.updateApplicationPermissions(appId=SYSTEMS[sys]['build']['app'], body={'username':username, 'permission':'EXECUTE'})
                service_ag.apps.updateApplicationPermissions(appId=SYSTEMS[sys]['run']['app'], body={'username':username, 'permission':'EXECUTE'})
        except Exception as e:
            err_resp = e.response.json()
            err_resp['status_code'] = e.response.status_code
            logger.warning('Error updating system/application permissions for {}: {}.'.format(username,err_resp))
            messages.warning(request, "Error updating system/application permissions. You may not be able to submit jobs: {}, {}".format(e, e.response.content))

        # if we are here, we successfully generated an Agave client, so get the token data:
        access_token = ag.token.token_info['access_token']
        refresh_token = ag.token.token_info['refresh_token']
        token_exp = ag.token.token_info['expires_at']

        request.session['username'] = username
        request.session['access_token'] = access_token
        request.session['refresh_token'] = refresh_token
        return redirect(reverse("terminal"))

    elif request.method == 'GET':
        return render(request, 'iptsite/login.html', { 'news': n }, content_type='text/html')

    return render(request, 'iptsite/login.html', { 'news': n }, content_type='text/html')


def logout(request):
    """
    This view allows user to logout after logging in
    """
    # log user out, end session
    # display success message ?
    # Dispatch the signal before the user is logged out so the receivers have a
    # chance to find out *who* logged out.
    user = getattr(request, 'user', None)
    if hasattr(user, 'is_authenticated') and not user.is_authenticated:
        user = None
    # user_logged_out.send(sender=user.__class__, request=request, user=user)

    # remember language choice saved to session
    # language = request.session.get(LANGUAGE_SESSION_KEY)

    request.session.flush()

    # if language is not None:
    # request.session[LANGUAGE_SESSION_KEY] = language

    if hasattr(request, 'user'):
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()

    # try:
    # 	del request.session['member_id']
    # except KeyError:
    # 	pass
    # return HttpResponse("You're logged out.")
    return redirect(reverse("login"))
    # while the user is logged in, give user option to logout (button)
    # button should be displayed at the top of the page in a nav bar on the right hand side, allowing the user to click
    # their "Account" or username and a drop down option should appear with "Log out"

    # logout button once clicked should display some message to the user saying that they are successfully logged out? Show this
    # on the login page, a simple small modal
    # or simply redirect the user back to the login page, ending their session and removing their tokens, POST method


# this login required decorator is to not allow to any
# view without authenticating
# send user to compile tab after authentication is successful
# @login_required(login_url="login/")
# home page is the compile tab, first tab
def compile(request):
    """
    This view generates the Compile page.
    """
    # if tokens for valid session aren't there, redirect to the login page
    if not check_for_tokens(request):
        return redirect(reverse("login"))
    user_name = request.session.get("username")
    context = {
        "admin": is_admin(user_name),
        "systems": SYSTEMS,
        "loggedinusername": user_name
    }

    if request.method == 'POST':

        system = request.POST.get('system')
        ccommand = request.POST.get('ccommand')
        driver = request.POST.get('driver')
        outfiles = request.POST.get('outfiles')
        commargs = request.POST.get('commargs')
        addfiles = request.POST.get('addfiles')
        modules = request.POST.get('modules')

        context['system'] = system
        context['ccommand'] = ccommand
        context['driver'] = driver
        context['outfiles'] = outfiles
        context['commargs'] = commargs
        context['addfiles'] = addfiles
        context['modules'] = modules

        if not ccommand:
            context["command_error"] = "Command cannot be blank"
            return render(request, 'iptsite/compile.html', context, content_type='text/html')
        if not driver:
            context["driver_error"] = "Driver cannot be blank"
            return render(request, 'iptsite/compile.html', context, content_type='text/html')
        if not outfiles:
            context["outfiles_error"] = "Output Files cannot be blank, please enter a.out or upload file"
            return render(request, 'iptsite/compile.html', context, content_type='text/html')

        driver_path = format_path(driver)
        driver = 'agave://{}/{}/{}'.format(AGAVE_STORAGE_SYSTEM_ID, user_name, driver_path)

        job_dict = {
            "name": "{}.build.ipt".format(user_name),
            # "appId": "ipt-build-{}-{}".format(system, settings.BUILD_APP_VERSION),
            "inputs": {
                "driver": driver,
            },
            "archive": True,
            "archiveSystem": AGAVE_STORAGE_SYSTEM_ID,
            "archivePath": '{}/jobs/{}/compile-{}-${{JOB_ID}}'.format(
                user_name,
                datetime.now().strftime('%Y-%m-%d'),
                system),
            "parameters": {
                "command": ccommand,
                "output": outfiles,
            }
        }

        try:
            job_dict['appId'] = SYSTEMS[system]['build']['app']
        except KeyError:
            logger.error('Build app not found for {}'.format(system))

        if addfiles:
            addfiles.rstrip(',')
            supplemental_files = []
            files = addfiles.split(',')
            for f in files:
                f=f.strip()
                f=format_path(f)
                supplemental_files.append('agave://{}/{}/{}'.format(AGAVE_STORAGE_SYSTEM_ID, user_name, f))
            job_dict['inputs']['supplemental-files'] = supplemental_files
        if modules:
            modules_list = []
            mods = modules.split(',')
            for m in mods:
                m=m.strip()
                modules_list.append(m)
            job_dict['parameters']['modules'] = modules_list
        if commargs:
            job_dict['parameters']['args'] = commargs

        # if job_dict['inputs']:
        #     for key, value in six.iteritems(job_dict['inputs']):
        #         parsed = urlparse(value)
        #         if parsed.scheme:
        #             job_dict['inputs'][key] = '{}://{}{}'.format(
        #                 parsed.scheme, parsed.netloc, urllib.quote(parsed.path))
        #         else:
        #             job_dict['inputs'][key] = urllib.quote(parsed.path)

        ag = get_agave_client_session(request)

        try:
            # submit job dictionary
            logger.info('Job Submission Body: {}'.format(job_dict))
            response = ag.jobs.submit(body=job_dict)
            logger.info('Job Submission Response: {}'.format(response))
            messages.success(request, 'Job {} has been submitted.'.format(response.id))
            return render(request, 'iptsite/compile.html', context)
        except Exception as e:
            err_resp = e.response.json()
            err_resp['status_code'] = e.response.status_code
            logger.warning(err_resp)
            messages.error(request, "Error submitting job: {}, {}".format(e, e.response.content))
            return render(request, 'iptsite/compile.html', context, content_type='text/html')

    elif request.method == 'GET':
        return render(request, 'iptsite/compile.html', context, content_type='text/html')


def terminal(request):
    """
    This view generates the Terminal page.
    """
    if not check_for_tokens(request):
        return redirect(reverse("login"))
    user_name = request.session.get("username")
    context = {"admin": is_admin(user_name),
               "loggedinusername": user_name}
    # if request.method == 'POST':
    #     f = request.FILES['fileToUpload']
    #     ag = get_service_client()
    #     try:
    #         rsp = ag.files.importData(systemId=AGAVE_STORAGE_SYSTEM_ID,
    #                                        filePath='/{}'.format(user_name),
    #                                        fileToUpload=f)
    #         messages.success(request, 'Your file has been queued for upload and will be available momentarily.')
    #     except Exception as e:
    #         msg = "Error uploading file. Exception: {}".format(e)
    #         logger.error(msg)
    #         messages.error(request, msg)
    try:
        meta = check_for_terminal(request)
    except IPTModelError as e:
        error = "Got an IPTModelError: {}, {}".format(e.message, e)
        logging.error(error)
        context["error"] = error
        messages.error(request, error)
        return render(request, 'iptsite/terminal.html', context, content_type='text/html')
    if meta['status'] == TerminalMetadata.pending_status:
        msg = "Please wait while your IPT terminal loads (status: {}).".format(meta['status'])
        context["url"] = ""
    elif meta['status'] == TerminalMetadata.ready_status:
        msg = "Your IPT terminal is ready."
        context["url"] = meta["url"]
    elif meta['status'] == TerminalMetadata.stopped_status:
        msg = "Your IPT terminal was stopped. We have started a new IPT terminal for you. " \
                         "Please wait while the terminal loads."
    else:
        msg = "Meta record value: {}".format(meta)
    messages.info(request, msg)
    return render(request, 'iptsite/terminal.html', context, content_type='text/html')

def webterm(request):
    """API backend for the iframe content on the terminal page."""
    if not check_for_tokens(request):
        # it should not be possible for the user to be calling the /webterm endpoint
        # without a session.
        return ""
    ag = get_agave_client_session(request)
    # check status of terminal and get url
    try:
        m = TerminalMetadata(request.session.get('username'), ag)
    except IPTModelError as e:
        try:
            token_info = ag.token.token_info
        except Exception as e:
            token_info = "Unable to pull token info: {}".format(e)
        raise IPTModelError("{}. Access token used: {}".format(e.message, token_info))
    return JsonResponse(m.value)


def create_account(request):
    """
    This is the view for the Create Account page.
    """
    # place in code, so that create account only shows when button is clicked
    if request.method == 'POST':
        return render(request, 'iptsite/create_account.html', content_type='text/html')
    # submit user entered content to database

    elif request.method == 'GET':
        return render(request, 'iptsite/create_account.html', content_type='text/html')

    # pass tokens here!

    # if user lands on create account page and already has tokens
    # redirect user to the login page to login
    # if check_for_tokens(request):
    # return redirect(reverse("login"))

    # if request.method == 'POST':
    # 	return redirect(reverse("login"))
    # elif request.method == 'GET'
    # 	return render(request, 'iptsite/create_account.html', content_type='text/html')

def foldertraverse(ag, completePath, user_name, fileList):
    userfiles = ag.files.list(systemId=AGAVE_STORAGE_SYSTEM_ID, filePath=completePath)
    for f in userfiles:
	if(f.name!="."):
	   newPath=f.path.replace('/{}'.format(user_name),"/home/ipt")
	   if(f.format == "folder"):
	       newPath+="/"
	   fileList.append(newPath)
    	   if(f.format == "folder"):
    	       foldertraverse(ag, f.path, user_name, fileList)
    return fileList

@csrf_exempt
def getdropdownvalues(request):
    user_name = request.session.get("username")
    print(user_name)

    path='/{}'.format(user_name)
    completePath=path
    path=format_path(path)
    ag = get_service_client()

    try:
    	finalfileList = foldertraverse(ag, completePath, user_name, [])
    except Exception as e:
        msg = "Error traversing folder structure. Exception: {}".format(e)
        logger.error(msg)
        return HttpResponseServerError(msg)
    return HttpResponse(json.dumps({'fileList': finalfileList}),content_type="application/json")

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def download(request, path=''):
    user_name = request.session.get("username")
    # if path.startswith('/home/ipt/'):
    #     path=path[10:]
    completePath=path.replace("/home/ipt",'/{}'.format(user_name))
    path=format_path(path)
    ag = get_service_client()

    try:
	if(path.endswith("/")):
	    pathList=foldertraverse(ag, completePath, user_name, [])
	    zipfile_paths=[]
	    if os.path.exists('{}'.format(user_name)):
		shutil.rmtree('{}'.format(user_name))
	    for files in pathList:
    	    	files=format_path(files)
		if not(files.endswith("/")):
		    rsp = ag.files.download(systemId=AGAVE_STORAGE_SYSTEM_ID,
				filePath='{}/{}'.format(user_name, files))
		directory = '{}/{}'.format(user_name, files).rsplit('/',1)[-2]
		if not os.path.exists(directory):
    		    os.makedirs(directory)
		if not(files.endswith("/")):
		    zipfile_paths.append('{}/{}'.format(user_name,files))
		    with open('{}/{}'.format(user_name, files),'w') as fileFH:
		        fileFH.write(rsp.content)

	    s = StringIO.StringIO()
	    with ZipFile(s,'w') as zip:
	    	for filename in zipfile_paths:
            	    zip.write(filename,filename.split('/',1)[1])

	    response=HttpResponse(s.getvalue())
	    response['content_type'] = 'application/zip'
    	    response['Content-Disposition'] = 'attachment; filename=%s' % '{}.zip'.format(path.rsplit('/',2)[-2])
	else:
            rsp = ag.files.download(systemId=AGAVE_STORAGE_SYSTEM_ID,
				filePath='{}/{}'.format(user_name, path))
            response = HttpResponse(rsp.content)
    	    response['content_type'] = 'application/force-download'
    	    response['Content-Disposition'] = 'attachment; filename=%s' % path.rsplit('/',1)[-1]
    except Exception as e:
        msg = "Error downloading file. Exception: {}".format(e)
        logger.error(msg)
        return HttpResponseServerError(msg)
    finally:
	if os.path.exists('{}'.format(user_name)):
	    shutil.rmtree('{}'.format(user_name))

	if os.path.exists('{}.zip'.format(path.rsplit('/',2)[-2])):
	    os.remove('{}.zip'.format(path.rsplit('/',2)[-2]))
    return response

class CustomMemoryFileUploadHandler(MemoryFileUploadHandler):
    def new_file(self, *args, **kwargs):
        args = (args[0], args[1].replace('/', '___').replace('\\', '___')) + args[2:]
        super(CustomMemoryFileUploadHandler, self).new_file(*args, **kwargs)

class CustomTemporaryFileUploadHandler(TemporaryFileUploadHandler):
    def new_file(self, *args, **kwargs):
        args = (args[0], args[1].replace('/', '___').replace('\\', '___')) + args[2:]
        super(CustomTemporaryFileUploadHandler, self).new_file(*args, **kwargs)

@csrf_exempt
def upload(request):
    # replace upload handlers. This depends on FILE_UPLOAD_HANDLERS setting. Below code handles the default in Django 1.10
    request.upload_handlers = [CustomMemoryFileUploadHandler(request), CustomTemporaryFileUploadHandler(request)]
    return uploadView(request)


def uploadView(request):
    user_name = request.session.get("username")
    checkRadio = request.POST.get('filefolder')
    if(checkRadio == "file"):
        f = request.FILES['fileToUpload']
        ag = get_service_client()
        try:
            rsp = ag.files.importData(systemId=AGAVE_STORAGE_SYSTEM_ID,
                                           filePath='/{}'.format(user_name),
                                           fileToUpload=f)
            logger.info(rsp)
        except Exception as e:
            msg = "Error uploading file. Exception: {}".format(e)
            logger.error(msg)
            return JsonResponse({'msg': msg}, status=500)

        return JsonResponse({'msg': 'Your file has been queued for upload and will be available momentarily.'})
    elif(checkRadio == "folder"):
        filesFold = request.FILES.getlist('folderToUpload')
        ag = get_service_client()
        try:
            for f in filesFold:
                sp=(f.name).split("___")
                f.name=sp[-1]
                folderNames='/'.join(sp[0:len(sp)-1])
                #filePath='/{}/{}'.format(user_name,folderNames)
                ag.files.manage(systemId=AGAVE_STORAGE_SYSTEM_ID,
                                filePath='/{}'.format(user_name),
                                body={'action': 'mkdir',
                                'path': '/{}'.format(folderNames)})
                rsp = ag.files.importData(systemId=AGAVE_STORAGE_SYSTEM_ID,
                                               filePath='/{}/{}'.format(user_name,folderNames),
                                               fileToUpload=f)
                logger.info(rsp)
        except Exception as e:
            msg = "Error uploading file. Exception: {}".format(e)
            logger.error(msg)
            return JsonResponse({'msg': msg}, status=500)
        return JsonResponse({'msg': 'Your file structure has been queued for upload and will be available momentarily.'})

def newsHistory(request):
    """
    This view generates the news history page.
    """
    user_name = request.session.get("username")

    if request.method == 'GET':
        n = Newscollection.objects.all()
        context = {
            "admin": is_admin(user_name),
            "loggedinusername": user_name,
            'news': n
        }
        return render(request, 'iptsite/newshistory.html', context)

class AddNews(CreateView):
    form_class = NewsForm
    model = Newscollection
    template_name = 'iptsite/newsForm.html'

    def get_success_url(self):
        return reverse('newsHistory')

class DeleteNews(DeleteView):
    model = Newscollection

    def get_success_url(self):
        return reverse('newsHistory')
