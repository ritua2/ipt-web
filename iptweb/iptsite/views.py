import os
# pull in entire package
from agavepy.agave import Agave 
# pull in python class

from django.shortcuts import render, redirect, reverse
from django.contrib.auth import authenticate, login, logout
# from django.contrib.auth.decorators import login_required


def check_for_tokens(request):
	access_token = request.session.get("access_token")
	if access_token:
		return True
	return False


# Create your views here.

def history(request):
	"""
	This view generates the Job history page.
	"""
	if not check_for_tokens(request):
		return redirect(reverse("login"))
	# context = {}
	# check errors, and convert the response to a "jobs" dictionary.
	#jobs = [{"uname": "tzmatt", "id": "123", "name": "test", "status": "RUNNING", "start": "July 6 2017 9:47 AM", "end": "None", "type": "RUN"}, 
	#{"id": "456", "name": "test2", "status": "FINISHED", "start": "July 7 2017 10:18 AM", "end": "July 7 2017 11:01 AM", "type": "BUILD"}]
	if request.method == 'GET':
		# grab tokens for session authorization
		access_token = request.session.get("access_token") #token from agave that represents the username and the oauth client
		refresh_token = request.session.get("refresh_token") #actual access token only lasts 4 hours, when expired -> token_expires
		# token_exp = ag.token.token_info['expires_at']
		ag = get_agave_client_tokens(access_token, refresh_token)

		request.session['access_token'] = access_token
		request.session['refresh_token'] = refresh_token
		
		try:
			jobs = ag.jobs.list()
			# for job in jobs:
			# 	print(job.id, '  ', job.status, '  ', job.created, '   ', job.owner, '   ', job.name)
			# print jobs[0]
			
			# for job in jobs:
			# 	print job.id, job.status, job.name, job.startTime, job.endTime
			context = {"jobs": jobs}
			return render(request, 'iptsite/history.html', context, content_type='text/html')

		except Exception as e:
			raise e
		# 	# import pdb; pdb.set_trace
		# 	response = getattr(e, 'response', None)
		# 	if response:
		# 		message = response.content
		# 	else:
		# 		message = e.message
		# 	context = {"history_error": "Error viewing history: {}, {}".format(type(e), message)}
		# 	return render(request, 'iptsite/history.html', context, content_type='text/html')

	# modal should display immediately after submit is clicked and job is compiling in background
	# check history tab for updated status on your job
	# print (jobs.id, '', jobs.name, '')

	# render the history template, passing in the jobs dictionary.
	# return render(request, 'iptsite/history.html', context, content_type='text/html')

def run(request):
	"""
	This view generates the Run page.
	"""
	# if tokens for valid session aren't there, redirect user to login page
	if not check_for_tokens(request):
		return redirect(reverse("login"))
	context = {}

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
		# 	context = {"run_additional_files_error": ""}

		if not rcommandargs:
			context = {"run_command_args": "Command Args cannot be blank"}
			return render(request, 'iptsite/run.html', context, content_type='text/html')
		
		run_job = {
			# "" : rcommand,
			"batchQueue" : jobq,
			# . . .
			# "" : numcores,
			"nodeCount" : numnodes,
			"maxRunTime" : estrun,
			# "" : allocnum,
			# "" : binary,
			"args" : rcommandargs,

		}
	elif request.method == 'GET':
		return render(request, 'iptsite/run.html', context, content_type='text/html')


def help(request):
	"""
	This view generates the Help page.
	"""
	if request.method == 'GET':
		return render(request, 'iptsite/help.html', content_type='text/html')

def get_agave_client(username, password):
	client_key = os.environ.get('AGAVE_CLIENT_KEY')
	client_secret = os.environ.get('AGAVE_CLIENT_SECRET')
	base_url = os.environ.get('AGAVE_BASE_URL', "https://api.tacc.utexas.edu")
	if not client_key or not client_secret:
		raise Exception("Missing OAuth client credentials.")
	return Agave(api_server=base_url, username=username, password=password, client_name="ipt", api_key=client_key, api_secret=client_secret)

def get_agave_client_tokens(access_token, refresh_token):
	client_key = os.environ.get('AGAVE_CLIENT_KEY')
	client_secret = os.environ.get('AGAVE_CLIENT_SECRET')
	base_url = os.environ.get('AGAVE_BASE_URL', "https://api.tacc.utexas.edu")
	if not client_key or not client_secret:
		raise Exception("Missing OAuth client credentials.")
	return Agave(api_server=base_url, token=access_token, refresh_token=refresh_token, client_name="ipt", api_key=client_key, api_secret=client_secret)

# @check_for_tokens
def login(request):
	"""
	This view generates the User Login page.
	"""
	# check if user already has a valid auth session
	# and just redirect them to e.g. compile page, if so.
	# LOGIN_REDIRECT_URL = '/compile' # means compile view
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
		access_token = ag.token.token_info['access_token'] #token from agave that represents the username and the oauth client
		refresh_token = ag.token.token_info['refresh_token'] #actual access token only lasts 4 hours, when expired -> token_expires
		token_exp = ag.token.token_info['expires_at']

		request.session['access_token'] = access_token
		request.session['refresh_token'] = refresh_token		
		return redirect(reverse("terminal"))	
	
	elif request.method == 'GET':
		return render(request, 'iptsite/login.html', content_type='text/html')


	# otherise, if request.method == POST this means the user
	# has submitted the login form, so check the credentials
	# and get an Agave acceess token.
	# ...
	# instantiate an Agave object:

	# try to get a token using the username and password
 #    try:
 #    	ag = Agave(base_url, client_key, client_secret), username, password)
	# except Exception:
	# 	return render(request, 'iptsite/login.html', context={'error': 'Invalid username/passwor'}, content_type='text/html')
	# if thia call worked, 
	# 1) get the access token and put it in the session.
    # 2) redirect to the compile page
	# . . .
	# otherwise, it is a GET request, so just show the login page:
	# ...
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
	# 	request.session[LANGUAGE_SESSION_KEY] = language

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
	context = {}
	
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
			"parameters" : { 
				"command" : ccommand,
				"output" : outfiles,   
				"args" : commargs,
				"modules" : "$MODULES_STR",}
		}

		# grab tokens for session authorization
		access_token = request.session.get("access_token") #token from agave that represents the username and the oauth client
		refresh_token = request.session.get("refresh_token") #actual access token only lasts 4 hours, when expired -> token_expires
		# token_exp = ag.token.token_info['expires_at']
		ag = get_agave_client_tokens(access_token, refresh_token)

		request.session['access_token'] = access_token
		request.session['refresh_token'] = refresh_token

		try:
			# submit job dictionary
			job = ag.jobs.submit(body=job_dict) #getting 400, bad request
			return render(request, 'iptsite/compile.html', content_type)

		except Exception as e:
			# import pdb; pdb.set_trace
			context = {"compile_error": "Error submitting job: {}, {}".format(e, e.response.content)}
			return render(request, 'iptsite/compile.html', context, content_type='text/html')

		# modal should display immediately after submit is clicked and job is compiling in background
		# check history tab for updated status on your job
		# 

	elif request.method == 'GET':
		return render(request, 'iptsite/compile.html', content_type='text/html')

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
	# Add these 2 lines of code after Terminal tab testing is complete to ensure
	# that no unauthorized user can access this page.
	# if not check_for_tokens(request):
	# 	return redirect(reverse("login"))
	
	if request.method == 'GET':

		# TESTING HERE

		return render(request, 'iptsite/terminal.html', content_type='text/html')

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
	# 	return redirect(reverse("login"))
	
	# if request.method == 'POST':
	# 	return redirect(reverse("login"))
	# elif request.method == 'GET'
	# 	return render(request, 'iptsite/create_account.html', content_type='text/html')
















