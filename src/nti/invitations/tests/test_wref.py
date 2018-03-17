#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that

import pickle

import fudge

from zope import component

from nti.invitations.interfaces import IInvitationsContainer

from nti.invitations.model import UserInvitation
from nti.invitations.model import install_invitations_container

from nti.invitations.tests import InvitationLayerTest

from nti.invitations.wref import InvitationWeakRef

from nti.wref.interfaces import IWeakRef


class TestWref(InvitationLayerTest):

    def test_refs(self):
        intids = fudge.Fake().provides('register')
        container = install_invitations_container(component, intids)
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        container.add(invitation)
        # check adapter
        wref = IWeakRef(invitation, None)
        assert_that(wref, is_not(none()))
        # check call
        assert_that(wref(), is_(invitation))
        # check str/repr
        str(wref)
        repr(wref)
        # check pickable
        value = pickle.dumps(wref)
        assert_that(pickle.loads(value), is_(InvitationWeakRef))
        # check sort
        fragor = UserInvitation(code='fragor',
                                receiver='ichigo',
                                sender='aizen',
                                accepted=True)
        fragor = IWeakRef(fragor)
        assert_that(sorted([fragor, wref]),
                    is_([wref, fragor]))
        # clean up
        component.getGlobalSiteManager().unregisterUtility(
            container, IInvitationsContainer
        )
