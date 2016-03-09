#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_property

from zope import component

from nti.invitations.interfaces import IInvitations

from nti.invitations.utility import PersistentInvitations

import nti.testing.base

ZCML_STRING = """
<configure 	xmlns="http://namespaces.zope.org/zope"
			xmlns:zcml="http://namespaces.zope.org/zcml"
			xmlns:invite="http://nextthought.com/ntp/invite"
			i18n_domain='nti.dataserver'>

	<include package="zope.component" />
	<include package="zope.annotation" />

	<include package="z3c.baseregistry" file="meta.zcml" />

	<include package="." file="meta.zcml" />

	<invite:joinCommunities
				code="NextThought"
			 	entities="NextThought" />
</configure>
"""

class TestZcml(nti.testing.base.ConfiguringTestBase):

	def test_registration(self):
		invitations = PersistentInvitations()
		component.getGlobalSiteManager().registerUtility(invitations, IInvitations)

		self.configure_string(ZCML_STRING)

		invitation = invitations.getInvitationByCode("NextThought")
		assert_that(invitation, is_not(none()))
		assert_that(invitation, has_property('code', 'NextThought'))
		assert_that(invitation, has_property('entities', ['NextThought']))
