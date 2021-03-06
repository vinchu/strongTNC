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
Provides CRUD for devices
"""

import re
from datetime import datetime
from django.http import HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.translation import ugettext_lazy as _
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from models import Device, Group, Product, Session, Result, Policy

@require_GET
@login_required
def devices(request):
    """
    All devices
    """
    context = {}
    context['title'] = _('Devices')
    context['count'] = Device.objects.count()
    devices = Device.objects.all().order_by('description')

    context['devices'] = paginate(devices, request)
    return render(request, 'tncapp/devices.html', context)

@require_GET
@login_required
def device(request, deviceID):
    """
    Device detail view
    """
    try:
        device = Device.objects.get(pk=deviceID)
    except Device.DoesNotExist:
        device = None
        messages.error(request, _('Device not found!'))

    context = {}
    context['title'] = _('Devices')
    context['count'] = Device.objects.count()
    devices = Device.objects.all().order_by('description')

    context['devices'] = paginate(devices, request)

    if device:
        context['device'] = device
        members = device.groups.all().order_by('name')
        context['members'] = members
        context['products'] = Product.objects.all().order_by('name')

        groups = Group.objects.exclude(id__in = members.values_list('id',
            flat=True))
        context['groups'] = groups
        context['title'] = _('Device ') + device.description

    return render(request, 'tncapp/devices.html', context)

@require_GET
@login_required
def add(request):
    """
    Add new device
    """
    context = {}
    context['title'] = _('New device')
    context['count'] = Device.objects.count()
    context['groups'] = Group.objects.all().order_by('name')
    context['products'] = Product.objects.all().order_by('name')
    devices = Device.objects.all().order_by('description')
    context['devices'] = paginate(devices, request)
    context['device'] = Device()
    return render(request, 'tncapp/devices.html', context)

@require_POST
@login_required
def save(request):
    """
    Insert/update a device
    """
    deviceID = request.POST['deviceId']
    if not (deviceID == 'None' or re.match(r'^\d+$', deviceID)):
        return HttpResponse(status=400)

    members = []
    if request.POST['memberlist'] != '':
        members = request.POST['memberlist'].split(',')

    for member in members:
        if not re.match(r'^\d+$', member):
            return HttpResponse(status=400)

    value = request.POST['value'].lower()
    if not re.match(r'^[a-f0-9]+$', value):
        return HttpResponse(status=400)

    description = request.POST['description']
    if not re.match(r'^[\S ]{0,50}$', description):
        return HttpResponse(status=400)

    productID = request.POST['product']
    if not re.match(r'^\d+$', productID):
        return HttpResponse(status=400)

    try:
        product = Product.objects.get(pk=productID)
    except Product.DoesNotExist:
        return HttpResponse(status=400)

    if deviceID == 'None':
        device = Device.objects.create(value=value, description=description,
                product=product, created=datetime.today())
    else:
        device = get_object_or_404(Device, pk=deviceID)
        device.value = value
        device.description = description
        device.product = product
        device.save()

    if members:
        device.groups.clear()
        members = Group.objects.filter(id__in=members)
        for member in members:
            device.groups.add(member)

        device.save()

    messages.success(request, _('Device saved!'))
    return redirect('/devices/%d' % device.id)

@require_POST
@login_required
def delete(request, deviceID):
    """
    Delete a device
    """
    device = get_object_or_404(Device, pk=deviceID)
    device.delete()

    messages.success(request, _('Device deleted!'))
    return redirect('/devices')

@require_GET
@login_required
def search(request):
    """
    Filter devices
    """
    context = {}
    context['title'] = _('Devices')
    context['count'] = Device.objects.count()
    devices = Device.objects.all().order_by('description')

    q = request.GET.get('q', None)
    if q != '':
        context['query'] = q
        devices = Device.objects.filter(Q(description__icontains=q)|Q(value__icontains=q))
    else:
        return redirect('/devices')

    context['devices'] = paginate(devices, request)
    return render(request, 'tncapp/devices.html', context)

def paginate(items, request):
    """
    Paginated browsing
    """
    paginator = Paginator(items, 50) # Show 50 devices per page
    page = request.GET.get('page')
    try:
        devices = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        devices = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        devices = paginator.page(paginator.num_pages)

    return devices

@require_GET
@login_required
def report(request, deviceID):
    """
    Generate device report for given device
    """
    device = get_object_or_404(Device, pk=deviceID)

    context = {}
    context['device'] = device
    context['title'] = _('Report for ') + str(device)

    sessions = Session.objects.filter(device=device).order_by('-time')
    context['session_count'] = len(sessions)
    context['definition_set'] = list(device.groups.all())
    context['inherit_set'] = list(device.get_inherit_set())

    if context['session_count'] > 0:
        context['sessions'] = []
        for session in sessions[:50]:
            context['sessions'].append((session,
                Policy.action[session.recommendation]))

        session = sessions.latest('time')
        context['last_session'] = session.time
        context['last_user'] = session.identity.data
        context['last_result'] = Policy.action[session.recommendation]
    else:
        context['last_session'] = _('Never')
        context['last_user'] = _('No one')
        context['last_result'] = _('N/A')

    enforcements = []
    for group in context['definition_set'] + context['inherit_set']:
        for e in group.enforcements.all():
            try:
                result =  Result.objects.filter(
                        session__device=device,policy=e.policy).latest()
                enforcements.append((e, Policy.action[result.recommendation],
                    device.is_due_for(e)))
            except Result.DoesNotExist:
                enforcements.append((e, _('N/A'), True))

    context['enforcements'] = enforcements

    return render(request, 'tncapp/device_report.html', context)

@require_GET
@login_required
def session(request, sessionID):
    """
    View details for a device-session
    """
    session = get_object_or_404(Session, pk=sessionID)

    context = {}
    context['session'] = session
    context['title'] = _('Session details')
    context['recommendation'] = Policy.action[session.recommendation]

    context['results'] = []
    for result in session.results.all():
        context['results'].append((result, Policy.action[result.recommendation]))

    return render(request, 'tncapp/session.html', context)
