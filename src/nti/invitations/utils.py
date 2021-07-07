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
from nti.invitations.index import IX_MIMETYPE
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
    if value is None:
        return None
    if isinstance(value, six.string_types):
        value = value.split(sep)
    value = set(value)
    value.discard(None)
    return value


def get_random_invitation_code():
    s = str(uuid.uuid4()).split('-')[-1].upper()
    result = s[0:4] + '-' + s[4:8] + '-' + s[8:]
    return text_(result)


def get_invitation_actor(invitation, user=None):
    actor = component.queryMultiAdapter((invitation, user), IInvitationActor)
    if actor is None:
        actor = IInvitationActor(invitation, None)
    return actor


def is_actionable(obj):
    return IActionableInvitation.providedBy(obj)


def get_invitations(sites=None,
                    receivers=None,
                    senders=None,
                    catalog=None,
                    mimeTypes=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_invitation_intids(sites=sites,
                                    receivers=receivers,
                                    senders=senders,
                                    catalog=catalog,
                                    mimeTypes=mimeTypes)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def get_invitation_intids(receivers=None,
                          senders=None,
                          sites=None,
                          now=None,
                          catalog=None,
                          mimeTypes=None,
                          accepted=False,
                          expired=False):
    """
    Get invitation intids by site and mimetype. By default, 
    pending invitations (not accepted and not expired) are returned.
    """
    receivers = safe_iterable(receivers)
    senders = safe_iterable(senders)
    mimeTypes = safe_iterable(mimeTypes)
    sites = safe_iterable(sites)
    catalog = get_invitations_catalog() if catalog is None else catalog
    now = time.time() if not now else now
    
    query = {IX_ACCEPTED: {'any_of': (accepted,)}}
    for name, values in ((IX_RECEIVER, receivers),
                         (IX_SENDER, senders),
                         (IX_MIMETYPE, mimeTypes),
                         (IX_SITE, sites)):
        if values is not None:
            query[name] = {'any_of': values}
    
    if accepted:
        # Accepted
        result = catalog.apply(query)
    elif expired:
        query[IX_EXPIRYTIME] = {'between': (60, now)}
        result = catalog.apply(query)
    else:
        # Pending
        query[IX_EXPIRYTIME] = {'any_of': (0,)}
        # pending no expiry
        no_expire_ids = catalog.apply(query) or LFSet()
        # pending with expiration
        query[IX_EXPIRYTIME] = {'between': (now, MAX_TS)}
        in_between_ids = catalog.apply(query) or LFSet()
        # return union
        result = catalog.family.IF.multiunion([no_expire_ids, in_between_ids])
    return result
get_pending_invitation_ids = get_invitation_intids


def get_pending_invitations(receivers=None,
                            sites=None,
                            now=None,
                            catalog=None,
                            mimeTypes=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_pending_invitation_ids(receivers=receivers,
                                         sites=sites,
                                         now=now,
                                         catalog=catalog,
                                         mimeTypes=mimeTypes)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def get_accepted_invitations(receivers=None,
                             sites=None,
                             now=None,
                             catalog=None,
                             mimeTypes=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_invitation_intids(receivers=receivers,
                                    sites=sites,
                                    now=now,
                                    accepted=True,
                                    catalog=catalog,
                                    mimeTypes=mimeTypes)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def has_pending_invitations(receivers=None, sites=None, now=None, catalog=None):
    intids = component.getUtility(IIntIds)
    doc_ids = get_pending_invitation_ids(receivers=receivers,
                                         sites=sites,
                                         now=now,
                                         catalog=catalog)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            return True
    return False


def get_expired_invitation_ids(*args, **kwargs):
    return get_invitation_intids(expired=True, *args, **kwargs)


def get_expired_invitations(receivers=None,
                            sites=None,
                            now=None,
                            catalog=None,
                            mimeTypes=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_expired_invitation_ids(receivers=receivers,
                                         sites=sites,
                                         now=now,
                                         catalog=catalog,
                                         mimeTypes=mimeTypes)
    for uid in doc_ids or ():
        obj = intids.queryObject(uid)
        if is_actionable(obj):
            result.append(obj)
    return result


def delete_expired_invitations(receivers=None,
                               sites=None,
                               now=None,
                               catalog=None,
                               mimeTypes=None):
    result = []
    container = component.getUtility(IInvitationsContainer)
    invitations = get_expired_invitations(receivers=receivers,
                                          sites=sites,
                                          now=now,
                                          catalog=catalog,
                                          mimeTypes=mimeTypes)
    for invitation in invitations:
        if container.remove(invitation):
            result.append(invitation)
    return result


def get_sent_invitation_ids(senders,
                            sites=None,
                            accepted=False,
                            catalog=None,
                            mimeTypes=None):

    senders = safe_iterable(senders)
    mimeTypes = safe_iterable(mimeTypes)
    sites = safe_iterable(sites)

    catalog = get_invitations_catalog() if catalog is None else catalog
    query = {
        IX_ACCEPTED: {'any_of': (accepted,)},
    }

    for name, values in ((IX_SENDER, senders),
                         (IX_MIMETYPE, mimeTypes),
                         (IX_SITE, sites)):
        if values is not None:
            query[name] = {'any_of': values}

    expired_ids = catalog.apply(query) or LFSet()
    return expired_ids


def get_sent_invitations(senders,
                         sites=None,
                         accepted=False,
                         catalog=None,
                         mimeTypes=None):
    result = []
    intids = component.getUtility(IIntIds)
    doc_ids = get_sent_invitation_ids(senders,
                                      sites,
                                      accepted,
                                      catalog,
                                      mimeTypes)
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
        invitation.acceptedTime = time.time()
        invitation.receiver = getattr(user, 'username', user)  # update
        notify(InvitationAcceptedEvent(invitation, user))
        result = True
    return result
