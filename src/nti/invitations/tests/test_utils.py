#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import has_length
from hamcrest import assert_that

import time

import BTrees

import fudge

from zope import component

from zope.intid.interfaces import IIntIds

from nti.invitations.index import create_invitations_catalog

from nti.invitations.interfaces import InvitationActorError
from nti.invitations.interfaces import IInvitationsContainer
from nti.invitations.interfaces import InvitationExpiredError

from nti.invitations.model import Invitation
from nti.invitations.model import UserInvitation
from nti.invitations.model import install_invitations_container

from nti.invitations.utils import is_actionable
from nti.invitations.utils import get_invitations
from nti.invitations.utils import accept_invitation
from nti.invitations.utils import get_invitations_ids
from nti.invitations.utils import get_invitation_actor
from nti.invitations.utils import get_sent_invitations
from nti.invitations.utils import get_pending_invitations
from nti.invitations.utils import get_expired_invitations
from nti.invitations.utils import has_pending_invitations
from nti.invitations.utils import delete_expired_invitations
from nti.invitations.utils import get_expired_invitation_ids
from nti.invitations.utils import get_pending_invitation_ids
from nti.invitations.utils import get_random_invitation_code

from nti.invitations.tests import InvitationLayerTest


class TestUtils(InvitationLayerTest):

    def create_invitations(self):
        catalog = create_invitations_catalog(family=BTrees.family64)
        i1 = Invitation(code=u'bleach',
                        receiver=u'ichigo',
                        sender=u'aizen',
                        accepted=False,
                        site=u"dataserver2",
                        expiryTime=0.0)
        catalog.index_doc(1, i1)

        i2 = Invitation(code=u'bleach2',
                        receiver=u'ichigo',
                        sender=u'aizen',
                        accepted=False,
                        site=u"dataserver2",
                        expiryTime=time.time() - 2000)
        catalog.index_doc(2, i2)

        i3 = Invitation(code=u'bleach3',
                        receiver=u'ichigo',
                        sender=u'aizen',
                        accepted=False,
                        site=u"dataserver2",
                        expiryTime=time.time() + 1000)
        catalog.index_doc(3, i3)
        return catalog, (i1, i2, i3)

    def test_get_invitations_ids(self):
        catalog, _ = self.create_invitations()
        invitations = get_invitations_ids(catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(receivers="aizen", catalog=catalog)
        assert_that(invitations, has_length(0))

        invitations = get_invitations_ids(receivers="ichigo", catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(senders="ichigo", catalog=catalog)
        assert_that(invitations, has_length(0))

        invitations = get_invitations_ids(senders="aizen", catalog=catalog)
        assert_that(invitations, has_length(3))

        invitations = get_invitations_ids(sites="xzy", catalog=catalog)
        assert_that(invitations, has_length(0))

        invitations = get_invitations_ids(sites="dataserver2", catalog=catalog)
        assert_that(invitations, has_length(3))

    def test_get_pending_invitations(self):
        catalog, _ = self.create_invitations()

        result = get_pending_invitation_ids("ichigo", catalog=catalog)
        assert_that(result, has_length(2))
        assert_that(sorted(result), is_([1, 3]))

        result = get_pending_invitation_ids("aizen", catalog=catalog)
        assert_that(result, has_length(0))

        result = get_expired_invitation_ids(catalog=catalog)
        assert_that(result, has_length(1))
        assert_that(sorted(result), is_([2]))

        result = get_expired_invitation_ids("ichigo", catalog=catalog)
        assert_that(result, has_length(1))
        assert_that(sorted(result), is_([2]))

        result = get_expired_invitation_ids("aizen", catalog=catalog)
        assert_that(result, has_length(0))

    def test_get_random_invitation_code(self):
        code = get_random_invitation_code()
        assert_that(code, has_length(14))

    def test_get_invitation_actor(self):
        invitation = UserInvitation(code='bleach',
                                    receiver='ichigo',
                                    sender='aizen',
                                    accepted=True)
        assert_that(get_invitation_actor(invitation), is_(none()))

    def test_is_actionable(self):
        invitation = UserInvitation(code='bleach',
                                    receiver='ichigo',
                                    sender='aizen',
                                    accepted=True)
        assert_that(is_actionable(invitation), is_(True))

    def test_invitations(self):
        i4 = UserInvitation(code='i4',
                            receiver='toshiro',
                            sender='aizen',
                            site="dataserver2",
                            accepted=False)

        class MockInt(object):
            def queryObject(self, uid):
                return i4 if uid == 4 else None

        intids = MockInt()
        gsm = component.getGlobalSiteManager()
        gsm.registerUtility(intids, IIntIds)

        catalog = create_invitations_catalog(family=BTrees.family64)
        assert_that(has_pending_invitations(catalog=catalog),
                    is_(False))

        catalog, _ = self.create_invitations()
        catalog.index_doc(4, i4)

        assert_that(get_invitations("dataserver2", "toshiro", catalog=catalog),
                    has_length(1))

        assert_that(get_pending_invitations(("toshiro",), catalog=catalog),
                    has_length(1))

        assert_that(has_pending_invitations(catalog=catalog),
                    is_(True))

        gsm.unregisterUtility(intids, IIntIds)

    def test_expired_invitations(self):
        catalog, invs = self.create_invitations()

        class MockInt(object):
            def queryObject(self, uid):
                return invs[uid - 1]

            def register(self, obj):
                pass

        intids = MockInt()
        gsm = component.getGlobalSiteManager()
        gsm.registerUtility(intids, IIntIds)

        assert_that(get_expired_invitations(('ichigo',), catalog=catalog),
                    has_length(1))

        container = install_invitations_container(component, intids)
        for invitation in invs:
            container.add(invitation)

        assert_that(delete_expired_invitations(catalog=catalog),
                    has_length(1))

        gsm.unregisterUtility(intids, IIntIds)
        gsm.unregisterUtility(container, IInvitationsContainer)

    def test_get_sent_invitations(self):
        catalog, invs = self.create_invitations()

        class MockInt(object):
            def queryObject(self, uid):
                return invs[uid - 1]

        intids = MockInt()
        gsm = component.getGlobalSiteManager()
        gsm.registerUtility(intids, IIntIds)

        assert_that(get_sent_invitations(('aizen',), catalog=catalog),
                    has_length(3))

        assert_that(get_sent_invitations('ichigo', catalog=catalog),
                    has_length(0))

        gsm.unregisterUtility(intids, IIntIds)

    @fudge.patch("nti.invitations.utils.get_invitation_actor")
    def test_accept_invitation(self, mock_ga):
        _, invs = self.create_invitations()
        valid, expired = invs[:2]  # expired
        with self.assertRaises(InvitationExpiredError):
            accept_invitation('ichigo', expired)

        mock_ga.is_callable().returns(None)
        with self.assertRaises(InvitationActorError):
            accept_invitation('ichigo', valid)

        fake_actor = fudge.Fake()
        fake_actor.provides("accept").returns(True)
        mock_ga.is_callable().returns(fake_actor)
        assert_that(accept_invitation('ichigo', valid),
                    is_(True))
