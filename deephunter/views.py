from django.http import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User, Group
from connectors.utils import is_connector_enabled
from notifications.utils import add_error_notification

# Dynamically import all connectors
import importlib
import pkgutil
import plugins
all_connectors = {}
for loader, module_name, is_pkg in pkgutil.iter_modules(plugins.__path__):
    module = importlib.import_module(f"plugins.{module_name}")
    all_connectors[module_name] = module

AUTH_PROVIDER = settings.AUTH_PROVIDER

def sso(request):
    # build a full authorize callback uri
    redirect_uri = request.build_absolute_uri('/authorize')
    # Redirect user to Auth website (PingID for instance) where login form may be shown + MFA
    if is_connector_enabled(AUTH_PROVIDER):
        return all_connectors.get(AUTH_PROVIDER).sso(request, redirect_uri)
    else:
        add_error_notification(f"{AUTH_PROVIDER} connector is not enabled.")
        return HttpResponseRedirect('/')

def user_logout(request):
    """
    Revoke token to be added?
    """
    logout(request)
    return redirect('/')

def check_groups():
    """
    Ensure that all groups defined in settings exist in the local DB, or create them.
    If groups exist in the DB but are not defined in settings anymore, they are not deleted.
    """

    if not is_connector_enabled(AUTH_PROVIDER):
        add_error_notification(f"{AUTH_PROVIDER} connector is not enabled.")
        return HttpResponseRedirect('/')

    USER_GROUPS_MEMBERSHIP = all_connectors.get(AUTH_PROVIDER).get_user_groups_membership()
    for group_name in USER_GROUPS_MEMBERSHIP.keys():
        group, created = Group.objects.get_or_create(name=group_name)

def authorize(request):
    
    check_groups()
    usergroups = []
    token = all_connectors.get(AUTH_PROVIDER).get_token(request)
    AUTH_TOKEN_MAPPING = all_connectors.get(AUTH_PROVIDER).get_token_mapping()
    USER_GROUPS_MEMBERSHIP = all_connectors.get(AUTH_PROVIDER).get_user_groups_membership()
    
    ### for debugging purposes
    ### It will stop and show the content of the token
    #return HttpResponse("<pre>{}</pre>".format(json.dumps(token, indent=4)))
    
    if AUTH_TOKEN_MAPPING['groups'] in token['userinfo']:
        # Groups can be string or list. This makes sure that whatever type, we make it a list
        if type(token['userinfo'][AUTH_TOKEN_MAPPING['groups']]) == str:
            usergroups = [token['userinfo'][AUTH_TOKEN_MAPPING['groups']]]
        else:
            usergroups = token['userinfo'][AUTH_TOKEN_MAPPING['groups']]
    
    if usergroups:

        # Search for matching groups
        matching_groups = {k: v for k, v in USER_GROUPS_MEMBERSHIP.items() if v in usergroups}

        # if user is member of 1 of the reference groups, access granted
        if matching_groups:
            # we search if the user is already in the local DB
            user = User.objects.filter(username=token['userinfo'][AUTH_TOKEN_MAPPING['username']])

            if AUTH_TOKEN_MAPPING['username'] in token['userinfo']:
                username = token['userinfo'][AUTH_TOKEN_MAPPING['username']]
            else:
                username = ''
            
            if AUTH_TOKEN_MAPPING['first_name'] in token['userinfo']:
                first_name = token['userinfo'][AUTH_TOKEN_MAPPING['first_name']]
            else:
                first_name = ''
            
            if AUTH_TOKEN_MAPPING['last_name'] in token['userinfo']:
                last_name = token['userinfo'][AUTH_TOKEN_MAPPING['first_name']]
            else:
                last_name = ''
            
            if AUTH_TOKEN_MAPPING['email'] in token['userinfo']:
                email = token['userinfo'][AUTH_TOKEN_MAPPING['email']]
            else:
                email = ''
            
            if user:
                # If user already exists, profile updated
                user = get_object_or_404(User, username=username)
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.is_active = True
                user.is_staff = True
                user.save()
            else:
                # User is granted access but does not exist yet
                user = User(
                    username = username,
                    first_name = first_name,
                    last_name = last_name,
                    email = email,
                    is_active = True,
                    is_staff = True
                )
                user.save()
                        
            # Add user to relevant group (viewer and/or manager)
            for matching_group in matching_groups:
                group = get_object_or_404(Group, name=matching_group)
                group.user_set.add(user)
            
            # login user
            login(request, user)
        return HttpResponseRedirect('/')    
    else:
        return HttpResponseRedirect('/')
