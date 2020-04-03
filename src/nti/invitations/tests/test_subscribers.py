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
from hamcrest import has_property

from zope.event import notify

from nti.invitations.interfaces import InvitationSentEvent

from nti.invitations.model import UserInvitation

from nti.invitations.tests import InvitationLayerTest


class TestSubscribers(InvitationLayerTest):

    def test_time(self):
        shikai = UserInvitation(code='shikai',
                                receiver='zangetzu',
                                sender='ichigo',
                                acceptedTime=90)
        assert_that(shikai, has_property('sent', is_(none())))
        notify(InvitationSentEvent(shikai, 'zangetzu'))
        assert_that(shikai, has_property('sent', is_not(none())))
