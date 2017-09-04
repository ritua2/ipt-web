import os

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

from agavepy.agave import Agave
from django.shortcuts import render, redirect, reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse

from models import is_ipt_meta, get_user, TerminalMetadata, IPTError, IPTModelError


def get_agave_exception_content(e):
    """Check if an Agave exception has content"""
    try:
        return e.response.content
    except Exception:
        return ""

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
    logger.info("Called actor. Message: {}. Response: {}".format(message, rsp))

def check_for_tokens(request):
    access_token = request.session.get("access_token")
    if access_token:
        return True
    return False

def check_for_terminal(request):
    """ Check to determine if a user has a terminal session submitted and submit one if not. This
    method should only be called once the user has logged in and has tokens in their session.
    """
    ag = get_agave_client_session(request)
    try:
        m = TerminalMetadata(request.session.get('username'), ag)
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
                 api_secret=client_secret)

def get_agave_client_tokens(access_token, refresh_token):
    client_key = os.environ.get('AGAVE_CLIENT_KEY')
    client_secret = os.environ.get('AGAVE_CLIENT_SECRET')
    base_url = os.environ.get('AGAVE_BASE_URL', "https://api.tacc.utexas.edu")
    if not client_key:
        raise Exception("Missing OAuth client key.")
    if not client_secret:
        raise Exception("Missing OAuth client secret.")
    return Agave(api_server=base_url, token=access_token, refresh_token=refresh_token, client_name="ipt",
                 api_key=client_key, api_secret=client_secret)

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
                           'terminals': terminals},
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
            context = {"jobs": jobs, "admin": is_admin(user_name)}
            return render(request, 'iptsite/history.html', context, content_type='text/html')

        except Exception as e:
            raise e

def run(request):
    """
    This view generates the Run page.
    """
    # if tokens for valid session aren't there, redirect user to login page
    if not check_for_tokens(request):
        return redirect(reverse("login"))
    user_name = request.session.get("username")
    context = {"admin": is_admin(user_name)}

    if request.method == 'POST':

        rcommand = request.POST.get('rcommand')
        jobq = request.POST.get('jobq')
        numcores = request.POST.get('numcores')
        numnodes = request.POST.get('numnodes')
        estrun = request.POST.get('estrun')
        allocnum = request.POST.get('allocnum')
        bin = request.POST.get('bin')
        run_additional_files = request.POST.get('run_additional_files')
        rcommandargs = request.POST.get('rcommandargs')

        if not rcommand:
            context = {"run_command_error": "Command cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not jobq:
            context = {"job_queue_error": "Job Queue cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not numcores:
            context = {"num_cores_error": "Number of Cores cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not numnodes:
            context = {"num_nodes_error": "Number of Nodes cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not estrun:
            context = {"est_run_error": "Estimated Job Runtime cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not allocnum:
            context = {"alloc_num_error": "Allocation Number cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        if not bin:
            context = {"binary_error": "Binary cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')
        # if not run_additional_files:
        # context = {"run_additional_files_error": ""}

        if not rcommandargs:
            context = {"run_command_args": "Command Args cannot be blank"}
            return render(request, 'iptsite/run.html', context, content_type='text/html')

        run_job = {  # "" : rcommand,
                     "batchQueue": jobq,  # . . .  # "" : numcores,
                     "nodeCount": numnodes,
                     "maxRunTime": estrun,  # "" : allocnum,  # "" : binary,
                     "args": rcommandargs,

        }
    elif request.method == 'GET':
        return render(request, 'iptsite/run.html', context, content_type='text/html')


def help(request):
    """
    This view generates the Help page.
    """
    user_name = request.session.get("username")
    context = {"admin": is_admin(user_name)}
    if request.method == 'GET':
        return render(request, 'iptsite/help.html', context, content_type='text/html')


# @check_for_tokens
def login(request):
    """
    This view generates the User Login page.
    """
    # check if user already has a valid auth session just redirect them to terminal page
    if check_for_tokens(request):
        return redirect(reverse("terminal"))

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username:
            context = {"error": "Username cannot be blank"}
            return render(request, 'iptsite/login.html', context, content_type='text/html')

        if not password:
            context = {"error": "Password cannot be blank"}
            return render(request, 'iptsite/login.html', context, content_type='text/html')

        try:
            ag = get_agave_client(username, password)
        except Exception as e:
            # render login template with an error
            context = {"error": "Invalid username or password: {}".format(e)}
            return render(request, 'iptsite/login.html', context, content_type='text/html')
        # if we are here, we successfully generated an Agave client, so get the token data:
        access_token = ag.token.token_info['access_token']
        refresh_token = ag.token.token_info['refresh_token']
        token_exp = ag.token.token_info['expires_at']

        request.session['username'] = username
        request.session['access_token'] = access_token
        request.session['refresh_token'] = refresh_token
        return redirect(reverse("terminal"))

    elif request.method == 'GET':
        return render(request, 'iptsite/login.html', content_type='text/html')

    return render(request, 'iptsite/login.html', content_type='text/html')


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
    context = {"admin": is_admin(user_name)}

    if request.method == 'POST':

        ccommand = request.POST.get('ccommand')
        driver = request.POST.get('driver')
        outfiles = request.POST.get('outfiles')
        commargs = request.POST.get('commargs')

        if not ccommand:
            context = {"command_error": "Command cannot be blank"}
            return render(request, 'iptsite/compile.html', context, content_type='text/html')
        if not driver:
            context = {"driver_error": "Driver cannot be blank"}
            return render(request, 'iptsite/compile.html', context, content_type='text/html')
        if not outfiles:
            context = {"outfiles_error": "Output Files cannot be blank, please enter a.out or upload file"}
            return render(request, 'iptsite/compile.html', context, content_type='text/html')
        if not commargs:
            context = {"commargs_error": "Args cannot be blank"}
            return render(request, 'iptsite/compile.html', context, content_type='text/html')

        app_version = os.environ.get("AGAVE_IPT_BUILD", "0.1.0")

        # ORIGINAL
        job_dict = {
        "jobName": "ipt-build-{}",
        "appId": "ipt-build-dev-{}".format(app_version),
        "executionSystem": "dev.ipt.build.execute",
        "parameters": {
        "command": ccommand,
        "output": outfiles,
        "args": commargs,
        "modules": "$MODULES_STR", }
        }

        ag = get_agave_client_session(request)
        try:
            # submit job dictionary
            job = ag.jobs.submit(body=job_dict)  # getting 400, bad request
            return render(request, 'iptsite/compile.html', content_type)

        except Exception as e:
            # import pdb; pdb.set_trace
            context = {"compile_error": "Error submitting job: {}, {}".format(e, e.response.content)}
            return render(request, 'iptsite/compile.html', context, content_type='text/html')

        # modal should display immediately after submit is clicked and job is compiling in background
        # check history tab for updated status on your job
        #

    elif request.method == 'GET':
        return render(request, 'iptsite/compile.html', context, content_type='text/html')

    # populate dictionary with values received from user form
    """
    try:
        ag = get_agave_client(username, password)
    except Exception as e:
        # render login template with an error
        context = {"error": "Invalid username or password: {}".format(e)}
        return render(request, 'iptsite/login.html', context, content_type='text/html')
    """


def terminal(request):
    """
    This view generates the Terminal page.
    """
    if not check_for_tokens(request):
        return redirect(reverse("login"))
    user_name = request.session.get("username")
    context = {"admin": is_admin(user_name)}

    try:
        meta = check_for_terminal(request)
    except IPTModelError as e:
        # todo - logging/exception handling
        error = "Got an IPTModelError: {}, {}".format(e.message, e)
        context["error"] = error
        return render(request, 'iptsite/terminal.html', context, content_type='text/html')
    if meta['status'] == TerminalMetadata.pending_status:
        context["msg"] = "Please wait while your IPT terminal loads (status: {}).".format(meta['status'])
        context["url"] = ""
    elif meta['status'] == TerminalMetadata.ready_status:
        context["msg"] = "Your IPT terminal is ready."
        context["url"] = meta["url"]
    elif meta['status'] == TerminalMetadata.stopped_status:
        context["msg"] = "Your IPT terminal was stopped. We have started a new IPT terminal for you." \
                         "Please wait while the terminal loads."
    else:
        context["msg"] = "Meta record value: {}".format(meta)
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
















