from authlib.integrations.django_client import OAuth
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.dispatch import receiver
from authlib.integrations.django_client import token_update
import json

AUTH_PROVIDER = settings.AUTH_PROVIDER
USER_GROUPS_MEMBERSHIP = settings.USER_GROUPS_MEMBERSHIP
AUTH_TOKEN_MAPPING = settings.AUTH_TOKEN_MAPPING

oauth = OAuth()
oauth.register(name=AUTH_PROVIDER,)

# Instead of defining an update_token method and passing it into OAuth registry,
# it is also possible to use signals to listen for token updates
@receiver(token_update)
def on_token_update(sender, name, token, refresh_token=None, access_token=None, **kwargs):
    if refresh_token:
        item = OAuth2Token.find(name=name, refresh_token=refresh_token)
    elif access_token:
        item = OAuth2Token.find(name=name, access_token=access_token)
    else:
        return

    # update old token
    item.access_token = token['access_token']
    item.refresh_token = token.get('refresh_token')
    item.expires_at = token['expires_at']
    item.save()

def sso(request):
    # build a full authorize callback uri
    redirect_uri = request.build_absolute_uri('/authorize')
    # Redirect user to Auth website (PingID for instance)
    #  where login form may be shown + MFA
    if AUTH_PROVIDER == 'pingid':
        return oauth.pingid.authorize_redirect(request, redirect_uri)
    else:
        return oauth.entra_id.authorize_redirect(request, redirect_uri)

def user_logout(request):
    
    """
    Revoke token to be added?
    """
    
    logout(request)
    return redirect('/')

def authorize(request):
    
    usergroups = []
    
    if AUTH_PROVIDER == 'pingid':
        token = oauth.pingid.authorize_access_token(request)
    else: # (assuming Entra ID is the auth provider)
        token = oauth.entra_id.authorize_access_token(request)

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
