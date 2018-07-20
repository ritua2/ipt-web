from django import forms
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.utils.html import escape
from nocaptcha_recaptcha.fields import NoReCaptchaField

from pytas.http import TASClient
import re
import logging


logger = logging.getLogger(__name__)

ELIGIBLE = 'Eligible'
INELIGIBLE = 'Ineligible'
REQUESTED = 'Requested'
# PI_ELIGIBILITY = (
#     ('', 'Choose One'),
#     (ELIGIBLE, ELIGIBLE),
#     (INELIGIBLE, INELIGIBLE),
#     (REQUESTED, REQUESTED),
# )
#
#
# USER_PROFILE_TITLES = (
#     ('', 'Choose one'),
#     ('Center Non-Researcher Staff', 'Center Non-Researcher Staff'),
#     ('Center Researcher Staff', 'Center Researcher Staff'),
#     ('Faculty', 'Faculty'),
#     ('Government User', 'Government User'),
#     ('Graduate Student', 'Graduate Student'),
#     ('High School Student', 'High School Student'),
#     ('High School Teacher', 'High School Teacher'),
#     ('Industrial User', 'Industrial User'),
#     ('Unaffiliated User', 'Unaffiliated User'),
#     ('Nonprofit User', 'Nonprofit User'),
#     ('NSF Graduate Research Fellow', 'NSF Graduate Research Fellow'),
#     ('Other User', 'Other User'),
#     ('Postdoctorate', 'Postdoctorate'),
#     ('Undergraduate Student', 'Undergraduate Student'),
#     ('Unknown', 'Unknown'),
#     ('University Non-Research Staff', 'University Non-Research Staff'),
#     ('University Research Staff', 'University Research Staff (excluding postdoctorates)'),
# )
# ETHNICITY_OPTIONS = (
#     ('', 'Choose one'),
#     ('Decline', 'Decline to Identify'),
#     ('White', 'White'),
#     ('Asian', 'Asian'),
#     ('Black or African American', 'Black or African American'),
#     ('Hispanic or Latino', 'Hispanic or Latino'),
#     ('American Indian or Alaska Native', 'American Indian or Alaska Native'),
#     ('Native Hawaiian or Other Pacific Islander', 'Native Hawaiian or Other Pacific Islander'),
#     ('Two or more races', 'Two or more races, not Hispanic')
# )
#
# GENDER_OPTIONS = (
#     ('', 'Choose one'),
#     ('Decline', 'Decline to Identify'),
#     ('Male', 'Male'),
#     ('Female', 'Female'),
#     ('Other', 'Other'),
# )
#
# PROFESSIONAL_LEVEL_OPTIONS = (
#     ('Undergraduate Student', 'Undergraduate Student'),
#     ('Graduate Student', 'Graduate Student'),
#     ('Postdoctoral Researcher', 'Postdoctoral Researcher'),
#     ('Faculty or Researcher', 'Faculty or Researcher'),
#     ('Staff (support, administration, etc)', 'Staff (support, administration, etc)'),
#     ('Practicing Engineer or Architect', 'Practicing Engineer or Architect'),
#     ('Other', 'Other (Please describe in your interests above)')
# )



def get_institution_choices():
    tas = TASClient()
    institutions_list = tas.institutions()
    return (('', 'Choose one'),) + tuple((c['id'], c['name']) for c in institutions_list)


# def get_department_choices(institutionId):
#     tas = TASClient()
#     departments_list = tas.get_departments(institutionId)
#     return (('', 'Choose one'),) + tuple((c['id'], c['name']) for c in departments_list)
#

def get_country_choices():
    tas = TASClient()
    countries_list = tas.countries()
    return (('', 'Choose one'),) + tuple((c['id'], c['name']) for c in countries_list)


class EmailConfirmationForm(forms.Form):
    code = forms.CharField(
            label='Enter Your Activation Code',
            required=True,
            error_messages={
                'required': 'Please enter the activation code you received via email.'
            })

    username = forms.CharField(
            label='Enter Your TACC Username',
            required=True)

    password = forms.CharField(
            widget=forms.PasswordInput,
            label='Enter Your TACC Password',
            required=True)


def check_password_policy(user, password, confirmPassword):
    """
    Checks the password for meeting the minimum password policy requirements:
    * Must be a minimum of 8 characters in length
    * Must contain characters from at least three of the following: uppercase letters,
      lowercase letters, numbers, symbols
    * Must NOT contain the username or the first or last name from the profile

    Returns:
        A boolean value indicating if the password meets the policy,
        An error message string or None
    """
    if password != confirmPassword:
        return False, 'The password provided does not match the confirmation.'

    if len(password) < 8:
        return False, 'The password provided is too short. Please review the password criteria.'

    char_classes = 0
    for cc in ['[a-z]', '[A-Z]', '[0-9]', '[^a-zA-Z0-9]']:
        if re.search(cc, password):
            char_classes += 1

    if char_classes < 3:
        return False, 'The password provided does not meet the complexity requirements.'

    pwd_without_case = password.lower()
    if user['username'].lower() in pwd_without_case:
        return False, 'The password provided must not contain parts of your name or username.'

    if user['firstName'].lower() in pwd_without_case or \
        user['lastName'].lower() in pwd_without_case:
        return False, 'The password provided must not contain parts of your name or username.'

    return True, None


# class ChangePasswordForm(forms.Form):
#
#     current_password = forms.CharField(widget=forms.PasswordInput)
#     new_password = forms.CharField(widget=forms.PasswordInput)
#     confirm_new_password = forms.CharField(
#         widget=forms.PasswordInput,
#         help_text='Passwords must meet the following criteria:<ul>'
#                   '<li>Must not contain your username or parts of your full name;</li>'
#                   '<li>Must be a minimum of 8 characters in length;</li>'
#                   '<li>Must contain characters from at least three of the following: '
#                   'uppercase letters, lowercase letters, numbers, symbols</li></ul>')
#
#     def __init__(self, *args, **kwargs):
#         self._username = kwargs.pop('username')
#         super(ChangePasswordForm, self).__init__(*args, **kwargs)
#
#     def clean(self):
#         cleaned_data = self.cleaned_data
#         reset_link = reverse('designsafe_accounts:password_reset')
#         tas = TASClient()
#         current_password_correct = tas.authenticate(self._username,
#                                                     cleaned_data['current_password'])
#         if current_password_correct:
#             tas_user = tas.get_user(username=self._username)
#             pw = cleaned_data['new_password']
#             confirm_pw = cleaned_data['confirm_new_password']
#             valid, error_message = check_password_policy(tas_user, pw, confirm_pw)
#             if not valid:
#                 self.add_error('new_password', error_message)
#                 self.add_error('confirm_new_password', error_message)
#                 raise forms.ValidationError(error_message)
#         else:
#             err_msg = mark_safe(
#                 'The current password you provided is incorrect. Please try again. '
#                 'If you do not remember your current password you can '
#                 '<a href="%s" tabindex="-1">reset your password</a> with an email '
#                 'confirmation.' % reset_link)
#             self.add_error('current_password', err_msg)
#
#     def save(self):
#         cleaned_data = self.cleaned_data
#         tas = TASClient()
#         tas.change_password(self._username, cleaned_data['current_password'],
#                             cleaned_data['new_password'])


class PasswordResetRequestForm(forms.Form):
    username = forms.CharField(label='Enter Your TACC Username', required=True)


class PasswordResetConfirmForm(forms.Form):
    code = forms.CharField(label='Reset Code', required=True)
    username = forms.CharField(label='Enter Your TACC Username', required=True)
    password = forms.CharField(widget=forms.PasswordInput, label='New Password', required=True)
    confirmPassword = forms.CharField(
        widget=forms.PasswordInput,
        label='Confirm New Password',
        required=True,
        help_text='Passwords must meet the following criteria:<ul>'
                  '<li>Must not contain your username or parts of your full name;</li>'
                  '<li>Must be a minimum of 8 characters in length;</li>'
                  '<li>Must contain characters from at least three of the following: '
                  'uppercase letters, lowercase letters, numbers, symbols</li></ul>')

    def clean(self):
        cleaned_data = self.cleaned_data
        username = cleaned_data.get('username')

        try:
            tas = TASClient()
            user = tas.get_user(username=username)
        except:
            msg = 'The username provided does not match an existing user.'
            self.add_error('username', msg)
            raise forms.ValidationError(msg)

        password = cleaned_data.get('password')
        confirmPassword = cleaned_data.get('confirmPassword')

        valid, error_message = check_password_policy(user, password, confirmPassword)
        if not valid:
            self.add_error('password', error_message)
            self.add_error('confirmPassword', '')
            raise forms.ValidationError(error_message)


# class TasUserProfileAdminForm(forms.Form):
#     """
#     Admin Form for TAS User Profile. Adds a field to trigger a password reset
#     on the User's behalf.
#     """
#     firstName = forms.CharField(label="First name")
#     lastName = forms.CharField(label="Last name")
#     email = forms.EmailField()
#     reset_password = forms.BooleanField(
#         required=False,
#         label="Reset user's password",
#         help_text="Check this box to reset the user's password. The user will be "
#             "notified via email with instructions to complete the password reset."
#        )


class UserRegistrationForm(forms.Form):
    firstName = forms.CharField(label='First name')
    lastName = forms.CharField(label='Last name')
    email = forms.EmailField()
    institutionId = forms.ChoiceField(
        label='Institution', choices=(),
        error_messages={'invalid': 'Please select your affiliated institution'},
        widget=forms.Select(attrs={"onchange":'institution_not_listed()'}))
    institution = forms.CharField(
        label='Institution name',
        help_text='If your institution is not listed, please provide the name of the '
                  'institution as it should be shown here.',
        required=False,
                                      )
    countryId = forms.ChoiceField(
        label='Country of residence', choices=(),
        error_messages={'invalid': 'Please select your Country of residence'})
    citizenshipId = forms.ChoiceField(
        label='Country of citizenship', choices=(),
        error_messages={'invalid': 'Please select your Country of citizenship'})

    username = forms.RegexField(
        label='Username',
        help_text='Usernames must be 3-8 characters in length, start with a letter, and '
                  'can contain only lowercase letters, numbers, or underscore.',
        regex='^[a-z][a-z0-9_]{2,7}$')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')
    confirmPassword = forms.CharField(
        label='Confirm Password', widget=forms.PasswordInput,
        help_text='Passwords must meet the following criteria:<ul>'
                  '<li>Must not contain your username or parts of your full name;</li>'
                  '<li>Must be a minimum of 8 characters in length;</li>'
                  '<li>Must contain characters from at least three of the following: '
                  'uppercase letters, lowercase letters, numbers, symbols</li></ul>')
    # captcha = NoReCaptchaField()

    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['institutionId'].choices = get_institution_choices()
        self.fields['institutionId'].choices += (('-1', 'My Institution is not listed'),)

        data = self.data or self.initial

        self.fields['countryId'].choices = get_country_choices()
        self.fields['citizenshipId'].choices = get_country_choices()

    def clean(self):
        username = self.cleaned_data.get('username')
        firstName = self.cleaned_data.get('firstName')
        lastName = self.cleaned_data.get('lastName')
        password = self.cleaned_data.get('password')
        confirmPassword = self.cleaned_data.get('confirmPassword')

        if username and firstName and lastName and password and confirmPassword:
            valid, error_message = check_password_policy(self.cleaned_data,
                                                         password,
                                                         confirmPassword)
            if not valid:
                self.add_error('password', error_message)
                self.add_error('confirmPassword', '')
                raise forms.ValidationError(error_message)

    def save(self, source='IPT', pi_eligibility=INELIGIBLE):
        data = self.cleaned_data
        data['source'] = source
        data['piEligibility'] = pi_eligibility

        safe_data = data.copy()
        safe_data['password'] = safe_data['confirmPassword'] = '********'

        logger.info('Attempting new user registration: %s' % safe_data)

        tas_user = TASClient().save_user(None, data)

        return tas_user
