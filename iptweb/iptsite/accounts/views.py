from django.shortcuts import render
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render_to_response
from django.utils.translation import ugettext_lazy as _
from . import forms

from pytas.http import TASClient
from pytas.models import User as TASUser
import logging
import json
import re

logger = logging.getLogger(__name__)


@login_required
def manage_authentication(request):
    if request.method == 'POST':
        form = forms.ChangePasswordForm(request.POST, username=request.user.username)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your TACC Password has been successfully changed!')
    else:
        form = forms.ChangePasswordForm(username=request.user.username)

    context = {
        'title': 'Authentication Settings',
        'form': form
    }
    return render(request, 'iptsite/accounts/manage_auth.html', context)


def register(request):
    if request.method == 'POST':
        account_form = forms.UserRegistrationForm(request.POST)
        if account_form.is_valid():
            try:
                account_form.save()
                return HttpResponseRedirect(
                    reverse('accounts:registration_successful'))
            except Exception as e:
                logger.info('error: {}'.format(e))

                error_type = e.args[1] if len(e.args) > 1 else ''

                if 'DuplicateLoginException' in error_type:
                    err_msg = (
                        'The username you chose has already been taken. Please '
                        'choose another. If you already have an account with TACC, '
                        'please log in using those credentials.')
                    account_form._errors.setdefault('username', [err_msg])
                elif 'DuplicateEmailException' in error_type:
                    err_msg = (
                        'This email is already registered. If you already have an '
                        'account with TACC, please log in using those credentials.')
                    account_form._errors.setdefault('email', [err_msg])
                    err_msg = '%s <a href="%s">Did you forget your password?</a>' % (
                        err_msg,
                        reverse('accounts:password_reset'))
                elif 'PasswordInvalidException' in error_type:
                    err_msg = (
                        'The password you provided did not meet the complexity '
                        'requirements.')
                    account_form._errors.setdefault('password', [err_msg])
                else:

                    safe_data = account_form.cleaned_data.copy()
                    safe_data['password'] = safe_data['confirmPassword'] = '********'
                    logger.exception('User Registration Error!', extra=safe_data)
                    err_msg = (
                        'An unexpected error occurred. If this problem persists '
                        'please create a support ticket.')
                messages.error(request, err_msg)
        else:
            messages.error(request, 'There were errors processing your registration. '
                                    'Please see below for details.')
    else:
        account_form = forms.UserRegistrationForm()

    context = {
        'account_form': account_form
    }
    return render(request, 'iptsite/accounts/register.html', context)


def registration_successful(request):
    return render_to_response('iptsite/accounts/registration_successful.html')


def password_reset(request, code=None):
    if code is None:
        code = request.GET.get('code', None)

    if code is not None:
        # confirming password reset
        message = 'Confirm your password reset using the form below. Enter your TACC ' \
                  'username and new password to complete the password reset process.'

        if request.method == 'POST':
            form = forms.PasswordResetConfirmForm(request.POST)
            if _process_password_reset_confirm(request, form):
                messages.success(request, 'Your password has been reset! You can now log '
                                          'in using your new password')
                return HttpResponseRedirect(reverse('terminal'))
            else:
                messages.error(request, 'Password reset failed. '
                                        'Please see below for details.')
        else:
            form = forms.PasswordResetConfirmForm(initial={'code': code})

    else:
        # requesting password reset
        message = 'Enter your TACC username to request a password reset. If your ' \
                  'account is found, you will receive an email at the registered email ' \
                  'address with instructions to complete the password reset.'

        if request.method == 'POST':
            form = forms.PasswordResetRequestForm(request.POST)
            if _process_password_reset_request(request, form):
                form = forms.PasswordResetRequestForm()
            else:
                messages.error(request, 'Password reset request failed. '
                                        'Please see below for details.')
        else:
            form = forms.PasswordResetRequestForm()

    return render(request, 'iptsite/accounts/password_reset.html',
                  {'message': message, 'form': form})


def _process_password_reset_request(request, form):
    if form.is_valid():
        # always show success to prevent data leaks
        messages.success(request, 'Your request has been received. If an account '
                                  'matching the username you provided is found, you will '
                                  'receive an email with further instructions to '
                                  'complete the password reset process.')

        username = form.cleaned_data['username']
        logger.info('Attempting password reset request for username: "%s"', username)
        try:
            tas = TASClient()
            user = tas.get_user(username=username)
            logger.info('Processing password reset request for username: "%s"', username)
            resp = tas.request_password_reset(user['username'], source='IPT')
            logger.debug(resp)
        except Exception as e:
            logger.exception('Failed password reset request')

        return True
    else:
        return False


def _process_password_reset_confirm(request, form):
    if form.is_valid():
        data = form.cleaned_data
        try:
            tas = TASClient()
            return tas.confirm_password_reset(data['username'], data['code'],
                                              data['password'], source='IPT')
        except Exception as e:
            if len(e.args) > 1:
                if re.search('account does not match', e.args[1]):
                    form.add_error('username', e.args[1])
                elif re.search('No password reset request matches', e.args[1]):
                    form.add_error('code', e.args[1])
                elif re.search('complexity requirements', e.args[1]):
                    form.add_error('password', e.args[1])
                elif re.search('expired', e.args[1]):
                    form.add_error('code', e.args[1])
                else:
                    logger.exception('Password reset failed')
                    form.add_error('__all__', 'An unexpected error occurred. '
                                              'Please try again')
            else:
                form.add_error('__all__', 'An unexpected error occurred. '
                                          'Please try again')

    return False


def email_confirmation(request, code=None):
    context = {}
    if request.method == 'POST':
        form = forms.EmailConfirmationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            code = data['code']
            username = data['username']
            password = data['password']
            try:
                tas = TASClient()
                user = tas.get_user(username=username)
                if tas.verify_user(user['id'], code, password=password):
                    messages.success(request,
                                     'Congratulations, your account has been activated! '
                                     'You can now log in to IPT.')
                    return HttpResponseRedirect(
                        reverse('terminal'))
                else:
                    messages.error(request,
                                   'We were unable to activate your account. Please try '
                                   'again.')
                    form = forms.EmailConfirmationForm(
                        initial={'code': code, 'username': username})
            except:
                logger.exception('TAS Account activation failed')
                form.add_error('__all__',
                               'Account activation failed. Please confirm your '
                               'activation code, username and password and try '
                               'again.')
    else:
        if code is None:
            code = request.GET.get('code', '')
        form = forms.EmailConfirmationForm(initial={'code': code})

    context['form'] = form

    return render(request, 'iptsite/accounts/email_confirmation.html', context)


# def departments_json(request):
#     institution_id = request.GET.get('institutionId')
#     if institution_id:
#         tas = TASClient()
#         departments = tas.get_departments(institution_id)
#     else:
#         departments = {}
#     return HttpResponse(json.dumps(departments), content_type='application/json')
