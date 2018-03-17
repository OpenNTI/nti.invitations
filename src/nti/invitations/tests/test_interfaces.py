#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from zope.dottedname import resolve as dottedname


class TestInterfaces(unittest.TestCase):

    def test_import(self):
        dottedname.resolve('nti.invitations.interfaces')

    def test_events(self):
        from nti.invitations.interfaces import InvitationSentEvent
        event = InvitationSentEvent(object(), 'user')
        assert_that(event, has_property('user', is_('user')))

        from nti.invitations.interfaces import InvitationAcceptedEvent
        event = InvitationAcceptedEvent(object(), 'user')
        assert_that(event, has_property('user', is_('user')))

        from nti.invitations.interfaces import InvitationValidationError
        error = InvitationValidationError("myInvitation")
        assert_that(error, has_property('invitation', is_('myInvitation')))
