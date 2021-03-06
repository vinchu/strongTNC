#
# Copyright (C) 2013 Marco Tanner
# Copyright (C) 2013 Stefan Rohner
# HSR University of Applied Sciences Rapperswil
#
# This file is part of strongTNC.  strongTNC is free software: you can
# redistribute it and/or modify it under the terms of the GNU Affero General
# Public License as published by the Free Software Foundation, either version 3
# of the License, or (at your option) any later version.
#
# strongTNC is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with strongTNC.  If not, see <http://www.gnu.org/licenses/>.
#

"""
General views like overview and site-wide search
"""

import re
from datetime import datetime, timedelta
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth import (authenticate, login as django_login, logout as
        django_logout)
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import (require_GET, require_safe,
        require_http_methods)
from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _
from models import Session, Result, Action, Enforcement, Device, Group, Package, Product, Policy

@require_GET
@login_required
def overview(request):
    """
    Main page
    """
    return render(request, 'tncapp/overview.html')

@require_safe
def start_session(request):
    """
    Initializes a new session and creates workitems according to policy
    """

    purge_dead_sessions()

    sessionID = request.GET.get('sessionID', '')
    if not re.match(r'^[0-9]+$', sessionID):
        return HttpResponse(status=400)

    try:
        session = Session.objects.get(pk=sessionID)
    except Session.DoesNotExist:
        return HttpResponse(status=404)

    device = session.device

    if not device.created:
        #This is a new device
        device.created = datetime.today()

        if device.product.default_groups.all():
            for group in device.product.default_groups.all():
                device.groups.add(group)
        else:
            #If no default groups for OS are specified
            device.groups.add(Group.objects.get(pk=1))

        device.save()

    device.create_work_items(session)

    return HttpResponse(content='')

@require_safe
def end_session(request):
    """
    End session and process results
    """
    sessionID = request.GET.get('sessionID', -1)

    try:
        session = Session.objects.get(pk=sessionID)
    except Session.DoesNotExist:
        return HttpResponse(status=404)

    generate_results(session)

    return HttpResponse(status=200)

@require_GET
def statistics(request):
    """
    Statistics view
    """
    context = {}
    context['title'] = _('Statistics')
    context['sessions'] = Session.objects.count()
    context['results'] = Result.objects.count()
    context['enforcements'] = Enforcement.objects.count()
    context['devices'] = Device.objects.count()
    context['packages'] = Package.objects.count()
    context['products'] = Product.objects.count()
    context['OSranking'] = Product.objects.annotate(num=
            Count('devices__id')).order_by('-num')

    context['rec_count_session'] = Session.objects.values('recommendation').annotate(
            num=Count('recommendation')).order_by('-num')

    for item in context['rec_count_session']:
        item['recommendation'] = Policy.action[item['recommendation']]

    context['rec_count_result'] = Result.objects.values('recommendation').annotate(
            num=Count('recommendation')).order_by('-num')

    for item in context['rec_count_result']:
        item['recommendation'] = Policy.action[item['recommendation']]

    return render(request, 'tncapp/statistics.html', context)

@require_http_methods(('GET','POST'))
def login(request):
    """
    Login view
    """
    if request.method == 'POST':
        password = request.POST.get('password', None)
        user = authenticate(username='admin-user', password=password)
        if user is not None and user.is_active:
                django_login(request, user)
                next = request.POST.get('next_url', None)
                if next is not None:
                    return redirect(next)
                else:
                    return redirect('/overview')
        else:
            messages.error(request, _('Bad password!'))

    if request.user.is_authenticated():
        return redirect('/overview')

    context = {'next_url': request.GET.get('next', '')}
    return render(request, 'tncapp/login.html', context)

def logout(request):
    """
    Logout and redirect to login view
    """
    django_logout(request)
    messages.success(request, _('Logout successful!'))

    return render(request, 'tncapp/login.html')


#NOT views, do not need decorators

def generate_results(session):
    """
    Generates result from the sessions workitems and removes the workitems
    """
    workitems = session.workitems.all()

    for item in workitems:
        rec = item.recommendation
        if rec is None:
            rec = Action.NONE

        Result.objects.create(result=item.result, session=session,
                policy=item.enforcement.policy, recommendation=rec)

    if workitems:
        session.recommendation = max(workitems, key = lambda x:
                x.recommendation)
    else:
        session.recommendation = Action.ALLOW

    session.save()

    for item in workitems:
        item.delete()


def purge_dead_sessions():
    """
    Removes sessions that have not been ended after 7 days
    """
    MAX_AGE = 7 #days

    deadline = datetime.today() - timedelta(days=MAX_AGE)
    dead = Session.objects.filter(recommendation=None, time__lte=deadline)

    for d in dead:
        d.delete()
