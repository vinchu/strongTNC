"""
Unit tests for the django app cygnet are specified in this file

    run using 'python manage.py test cygapp'
"""

from django.test import TestCase
from cygapp.policies import *
import cygapp.models as m


def setupTestData():
    device = m.Device(value='def', description='Test Device')
    device.save()
    
    g1 = m.Group(name='ROOT')
    g1.save()
    g11 = m.Group(name='B1.1', parent=g1)
    g11.save()
    g12 = m.Group(name='L1.2', parent=g1)
    g12.save()
    g13 = m.Group(name='B1.3', parent=g1)
    g13.save()
    g111 = m.Group(name='B1.1.1', parent=g11)
    g111.save()
    g1111 = m.Group(name='L1.1.1.1', parent=g111)
    g1111.save()
    g1112 = m.Group(name='L1.1.1.2', parent=g111)
    g1112.save()
    g131 = m.Group(name='L1.3.1', parent=g13)
    g131.save()
    g132 = m.Group(name='L1.3.2', parent=g13)
    g132.save()

    device.groups.add(g1112)
    device.groups.add(g131)
    device.save()

    policies = []
    policies.append(m.Policy(name='bash',type=1,argument='/bin/bash',fail=3,noresult=0))
    policies.append(m.Policy(name='usrbin',type=2,argument='/usr/bin/',fail=4,noresult=1))
    policies.append(m.Policy(name='ports',type=3,argument='0-1024',fail=0,noresult=0))

    for p in policies:
        p.save()


class CygappTest(TestCase):
    def test_file_basics(self):
        """
        Tests basic file properties in different formats.
        """
        f = m.File(name='grep')
        d = m.Directory(path='/')
        d.save()
        f.directory=d
        f.save()

        h = m.File.objects.get(pk=1)
        self.assertEqual('{"id": 1, "dir": "/", "name": "grep"}', h.__json__())

    def test_getGroupSet(self):
        setupTestData()
        device = m.Device.objects.get(value='def')

        groups = device.getGroupSet()
        self.assertEqual(6, len(groups))

        device.groups.add(m.Group.objects.get(name='B1.1.1'))
        device.groups.add(m.Group.objects.get(name='L1.3.2'))
        
        groups = device.getGroupSet()
        self.assertEqual(7, len(groups))

    def test_getWorkItems(self):
        setupTestData()

        g = m.Group.objects.get(name='B1.1.1')
        p = m.Policy.objects.get(name='bash')
        e = m.Enforcement(group=g, policy=p, max_age=3)
        e.save()

        g = m.Group.objects.get(name='L1.3.1')
        p = m.Policy.objects.get(name='usrbin')
        e = m.Enforcement(group=g, policy=p, max_age=2)
        e.save()

        device = m.Device.objects.get(value='def')
        device.createWorkItems()

        items = m.WorkItems.objects.filter(device=device)
        self.assertEqual(2, len(items))

    def test_isDueFor(self):
        raise NotImplementedError 
        

        

        
    def test_imv_login(self):
        import simIMV as imv

        imv.run_test_case()


