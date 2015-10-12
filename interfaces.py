#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces defining the invitation system. The key class for
creating and working with invitations is :class:`IInvitation`.
The key class for registering, querying and responding to invitations is :class:`IInvitations`.
An implementation of this class should be registered as a persistent utility in the site.

.. $Id$
"""

# Regarding existing work: There's a Plone product, but it's very specific to plone and works
# only for initial registration.

# There's z3ext.principal.invite, which is interesting and possibly applicable,
# but doesn't seem to be available anymore. Some inspiration from it, though.
# See http://pydoc.net/z3ext.principal.invite/0.4.0/z3ext.principal.invite.interfaces

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

from zope import schema
from zope import interface

from zope.annotation.interfaces import IAnnotatable

from zope.container.interfaces import IContained

from zope.interface.interfaces import ObjectEvent, IObjectEvent

from zope.schema import ValidationError

from nti.dataserver_core.interfaces import IUser
from nti.dataserver_core.interfaces import ICreated
from nti.dataserver_core.interfaces import ILastModified

class IInvitation(IContained,
				  ICreated,
				  ILastModified,
				  IAnnotatable):
	"""
	An invitation from one user of the system (or the system itself)
	for another user to be able to do something.

	Invitations are initially created and registered with an
	:class:`IInvitations` utility. At some time in the future, someone
	who was invited may accept the invitation. The process of
	accepting the invitation is considered to run at the credential
	level of the creator of the invitation (thus allowing accepting
	the invitation to do things like join a group of the creator).

	Invitations may expire after a period of time and/or be good for only
	a certain number of uses. They may have a predicate that determines they are
	applicable only to certain users (for example, a list of invited users).
	"""

	# TODO: What descriptive properties, if any?
	code = interface.Attribute("A unique code that identifies this invitation within its IInvitations container.")

	def accept(user):
		"""
		Perform whatever action is required for the ``user`` to accept the invitation, including
		validating that the user is actually allowed to accept the invitation. Typically
		this means that this method has side effects.

		Once the invitation has been accepted, this should notify an :class:`IInvitationAcceptedEvent`.

		:raises InvitationExpiredError: If the invitation has expired.
		"""

class IObjectInvitation(IInvitation):
	"""
	An invitation relating to a specific object.
	"""

	object_int_id = interface.Attribute('The global intid for the object the invitation refers to.')
	object = interface.Attribute('Object')

class IInvitations(IContained,
				   IAnnotatable):
	"""
	A central registry of invitations. Intended to be used as a utility registered
	for the site.
	"""

	def registerInvitation(invitation):
		"""
		Registers the given invitation with this object. This object is responsible for
		assigning the invitation code and taking ownership of the invitation.
		"""

	def removeInvitation(invitation):
		"""
		Remove the given invitation with this object.
		"""


	def getInvitationByCode(code):
		"""
		Returns an invitation having the given code, or None if there is no
		such invitation.
		"""

class IInvitationEvent(IObjectEvent):
	"""
	An event specifically about an invitation.
	"""
	object = schema.Object(IInvitation,
						   title="The invitation.")

class IInvitationAcceptedEvent(IInvitationEvent):
	"""
	An invitation has been accepted.
	"""
	user = schema.Object(IUser,
						 title="The user that accepted the invitation.")

@interface.implementer(IInvitationAcceptedEvent)
class InvitationAcceptedEvent(ObjectEvent):

	def __init__(self, obj, user):
		super(InvitationAcceptedEvent, self).__init__(obj)
		self.user = user

class InvitationValidationError(ValidationError):
	"""
	A problem relating to the validity of an attempted action on
	an invitation.
	"""

	def __init__(self, code):
		super(InvitationValidationError, self).__init__(code)
		self.value = code

class InvitationCodeError(InvitationValidationError):
	__doc__ = _('The invitation code is not valid.')
	i18n_message = __doc__

class InvitationExpiredError(InvitationValidationError):
	__doc__ = _('The invitation code has expired.')
	i18n_message = __doc__

class IInvitationEntityFinder(interface.Interface):
	"""
	An interface for a utility to find an entity
	"""
	def find(username):
		"""
		returns the entity with the specified username
		"""
	