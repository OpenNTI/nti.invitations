#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import none
from hamcrest import all_of
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from nti.testing.matchers import validly_provides
from nti.testing.matchers import verifiably_provides

import fudge

from zope import component

from nti.externalization.tests import externalizes

from nti.invitations.interfaces import IUserInvitation
from nti.invitations.interfaces import IInvitationsContainer
from nti.invitations.interfaces import DuplicateInvitationCodeError

from nti.invitations.model import UserInvitation
from nti.invitations.model import InvitationsContainer
from nti.invitations.model import install_invitations_container

from nti.invitations.tests import InvitationLayerTest


class TestModel(InvitationLayerTest):

    def test_valid_interface(self):
        assert_that(UserInvitation(), verifiably_provides(IUserInvitation))

    @fudge.patch('nti.invitations.model.getSite')
    def test_external(self, mock_gs):
        fake_site = fudge.Fake().has_attr(__name__=u'anime')
        mock_gs.is_callable().returns(fake_site)

        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        assert_that(invitation,
                    externalizes(all_of(has_entry('code', 'bleach'),
                                        has_entry('receiver', 'ichigo'),
                                        has_entry('sender', 'aizen'),
                                        has_entry('site', 'anime'),
                                        has_entry('accepted', is_(True)),
                                        has_entry('expiryTime', is_(0)))))

        assert_that(invitation, validly_provides(IUserInvitation))

    def test_misc(self):
        fragor = UserInvitation(code='fragor',
                                receiver='ichigo',
                                sender='aizen',
                                accepted=True)

        assert_that(fragor.is_expired(), is_(False))
        fragor.expiryTime = 10
        assert_that(fragor.is_expired(), is_(True))

        assert_that(fragor.is_email(), is_(False))
        fragor.receiver = u'ichigo@bleach.org'
        assert_that(fragor.is_email(), is_(True))

        shikai = UserInvitation(code='shikai',
                                receiver='zangetzu',
                                sender='ichigo',
                                accepted=True)
        assert_that(sorted([shikai, fragor]),
                    is_([fragor, shikai]))

    def test_container(self):
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        container = InvitationsContainer()
        container.add(invitation)
        assert_that(container, has_length(is_(1)))
        assert_that(invitation, has_property('code', is_not(none())))

        # Duplicate
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigoxxx',
                                    sender=u'aizenxxx',
                                    accepted=False)
        with self.assertRaises(DuplicateInvitationCodeError):
            container.add(invitation)

        container.remove(invitation)
        assert_that(container, has_length(is_(0)))

    @fudge.patch('nti.invitations.model.get_random_invitation_code')
    def test_random_code(self, mock_rc):
        invitation = UserInvitation(code=u'bleach',
                                    receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        container = InvitationsContainer()
        container.add(invitation)

        mock_rc.is_callable().returns('bleach').next_call().returns('enemy')
        invitation = UserInvitation(receiver=u'ichigo',
                                    sender=u'aizen',
                                    accepted=True)
        container.add(invitation)
        assert_that(invitation, has_property('code', is_('enemy')))

        assert_that(container.remove('enemy', False), is_(True))

    def test_install_container(self):
        intids = fudge.Fake().provides('register')
        container = install_invitations_container(component, intids)
        assert_that(container, is_not(none()))
        component.getGlobalSiteManager().unregisterUtility(
            container, IInvitationsContainer
        )
