#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import time
import uuid
from datetime import datetime

from BTrees.LFBTree import LFSet

import six

from zope import component

from zope.event import notify

from zope.intid.interfaces import IIntIds

from nti.base._compat import text_

from nti.invitations.index import IX_SITE
from nti.invitations.index import IX_SENDER
from nti.invitations.index import IX_ACCEPTED
from nti.invitations.index import IX_RECEIVER
from nti.invitations.index import IX_EXPIRYTIME
from nti.invitations.index import get_invitations_catalog

from nti.invitations.interfaces import IInvitationActor
from nti.invitations.interfaces import InvitationActorError
from nti.invitations.interfaces import IActionableInvitation
from nti.invitations.interfaces import IInvitationsContainer
from nti.invitations.interfaces import InvitationExpiredError
from nti.invitations.interfaces import InvitationAcceptedEvent

MAX_TS = time.mktime(datetime.max.timetuple())

logger = __import__('logging').getLogger(__name__)


def safe_iterable(value, sep=','):
    if isinstance(value, six.string_types):
        value = value.split(sep)
    value = set(value or ())
    value.discard(None)
    return value or ()


def get_random_invitation_code():
    s = str(uuid.uuid4()).split('-')[-1].upper()
    result = s[0:4] + '-' + s[4:8] + '-' + s[8:]
    return text_(result)


def get_invitation_actor(invitation, user=None):
    actor = component.queryMultiAdapter((invitation, user), IInvitationActor)
    if actor is None:
        actor = IInvitationActor(invitation, None)
    return actor


def get_invitations_ids(sites=None, receivers=None, senders=None, catalog=None):
    query = {}
    catalog = get_invitations_catalog() if catalog is None else catalog
    # add sites
    sites = safe_iterable(sites)
    if sites:
        query[IX_SITE] = {'any_of': sites}
    # add senders and receivers
    for name, values in ((IX_RECEIVER, receivers), (IX_SENDER, senders)):
        if values:
            values = safe_iterable(values)
            query[name] = {'any_of': values}
    # run query if available
    if query:
        doc_ids = catalog.apply(query) or ()
    else:
        doc_ids = tuple(catalog[IX_SITE].documents_to_values.keys())
    return doc_ids


def is_actionable(obj):
    return IActionableInvitation.providedBy(obj)


def get_invitations(sites=None, receivers=None, senders=None, catalog=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_invitations_ids(sites, receivers, senders, catalog)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def get_pending_invitation_ids(receivers=None, sites=None, now=None, catalog=None):
    catalog = get_invitations_catalog() if catalog is None else catalog
    query = {
        IX_ACCEPTED: {'any_of': (False,)},
        IX_EXPIRYTIME: {'any_of': (0,)},
    }
    # check sites
    sites = safe_iterable(sites)
    if sites:
        query[IX_SITE] = {'any_of': sites}
    # check receivers
    receivers = safe_iterable(receivers)
    if receivers:
        query[IX_RECEIVER] = {'any_of': receivers}
    # pending no expiry
    no_expire_ids = catalog.apply(query) or LFSet()
    # pending with expiration
    now = time.time() if not now else now
    query[IX_EXPIRYTIME] = {'between': (now, MAX_TS)}
    in_between_ids = catalog.apply(query) or LFSet()
    # return union
    return catalog.family.IF.multiunion([no_expire_ids, in_between_ids])


def get_pending_invitations(receivers=None, sites=None, now=None, catalog=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_pending_invitation_ids(receivers, sites, now, catalog)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def has_pending_invitations(receivers=None, sites=None, now=None, catalog=None):
    intids = component.getUtility(IIntIds)
    doc_ids = get_pending_invitation_ids(receivers, sites, now, catalog)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            return True
    return False


def get_expired_invitation_ids(receivers=None, sites=None, now=None, catalog=None):
    # 60 min value w/ minute resolution
    now = time.time() - 60 if not now else now
    catalog = get_invitations_catalog() if catalog is None else catalog
    query = {
        IX_ACCEPTED: {'any_of': (False,)},
        # 60 min value w/ minute resolution
        IX_EXPIRYTIME: {'between': (60, now)},
    }
    sites = safe_iterable(sites)
    if sites:
        query[IX_SITE] = {'any_of': sites}
    receivers = safe_iterable(receivers)
    if receivers:
        query[IX_RECEIVER] = {'any_of': receivers}
    expired_ids = catalog.apply(query) or LFSet()
    return expired_ids


def get_expired_invitations(receivers=None, sites=None, now=None, catalog=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_expired_invitation_ids(receivers, sites, now, catalog)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def delete_expired_invitations(receivers=None, sites=None, now=None, catalog=None):
    result = []
    container = component.getUtility(IInvitationsContainer)
    invitations = get_expired_invitations(receivers, sites, now, catalog)
    for invitation in invitations:
        if container.remove(invitation):
            result.append(invitation)
    return result


def get_sent_invitation_ids(senders, sites=None, accepted=False, catalog=None):
    senders = safe_iterable(senders)
    catalog = get_invitations_catalog() if catalog is None else catalog
    query = {
        IX_SENDER: {'any_of': senders},
        IX_ACCEPTED: {'any_of': (accepted,)},
    }
    sites = safe_iterable(sites)
    if sites:
        query[IX_SITE] = {'any_of': sites}
    expired_ids = catalog.apply(query) or LFSet()
    return expired_ids


def get_sent_invitations(senders, sites=None, accepted=False, catalog=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_sent_invitation_ids(senders, sites, accepted, catalog)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def accept_invitation(user, invitation):
    if invitation.is_expired():
        raise InvitationExpiredError(invitation)
    actor = get_invitation_actor(invitation, user)
    if actor is None:
        raise InvitationActorError(invitation)
    result = False
    if actor.accept(user, invitation):
        invitation.accepted = True
        invitation.receiver = getattr(user, 'username', user)  # update
        notify(InvitationAcceptedEvent(invitation, user))
        result = True
    return result
