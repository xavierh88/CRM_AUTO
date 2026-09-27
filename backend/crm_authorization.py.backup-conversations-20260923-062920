"""CRM object ownership policy shared by direct access, lists and aggregates.

Accepted collaborators can read; owners and managers of known non-admin owners
can write. Child objects inherit access from their client, never from a supplied
salesperson, search filter, notification or SOLD state.
"""
from fastapi import HTTPException
from document_authorization import can_access_documents
from runtime_security import ROLES, is_demo_identity

CLIENT_CHILDREN = {'user_records', 'appointments', 'client_comments', 'sms_logs',
                   'email_logs', 'sms_conversations', 'public_links'}
SCOPED_COLLECTIONS = CLIENT_CHILDREN | {'clients', 'record_comments', 'cosigner_relations', 'imported_contacts'}
MAX_SCOPE_OBJECTS = 10000


class CRMAccess:
    def __init__(self, db, user):
        self.db, self.user = db, user
        self._scopes = {}

    def _identity(self):
        role, uid = self.user.get('role'), self.user.get('id')
        if not isinstance(role, str) or role not in ROLES or not isinstance(uid, str) or not uid:
            raise HTTPException(403, 'CRM access denied')

        # Demo uses the real CRM code path, but only inside its isolated
        # fictional dealer tenant.
        if is_demo_identity(self.user):
            dealer_id = self.user.get('dealer_id')
            if not isinstance(dealer_id, str) or not dealer_id:
                raise HTTPException(403, 'Demo dealer scope unavailable')

        return role, uid

    async def require(self, collection, object_id, action='read'):
        role, uid = self._identity()
        if not isinstance(object_id, str) or not object_id:
            raise HTTPException(404, 'CRM object not found')
        obj = await getattr(self.db, collection).find_one({'id': object_id}, {'_id': 0})
        if not obj or (obj.get('is_deleted') and role != 'admin'):
            raise HTTPException(404, 'CRM object not found')
        allowed = False
        if collection == 'clients':
            allowed = await can_access_documents(self.db, self.user, obj, action)
        elif collection in CLIENT_CHILDREN:
            await self.require('clients', obj.get('client_id'), action)
            allowed = True
        elif collection == 'record_comments':
            await self.require('user_records', obj.get('record_id'), action)
            allowed = role == 'admin' or not obj.get('admin_only')
        elif collection == 'cosigner_relations':
            await self.require('clients', obj.get('buyer_client_id'), action)
            await self.require('clients', obj.get('cosigner_client_id'), action)
            allowed = True
        elif collection == 'imported_contacts':
            allowed = role == 'admin' or obj.get('imported_by') == uid
        if not allowed:
            raise HTTPException(404, 'CRM object not found')
        return obj

    async def _ids(self, collection, query):
        # Bound the Mongo $in payload; fail closed instead of truncating scope.
        rows = await getattr(self.db, collection).find(query, {'id': 1, '_id': 0}).to_list(MAX_SCOPE_OBJECTS + 1)
        if len(rows) > MAX_SCOPE_OBJECTS:
            raise HTTPException(503, 'CRM scope too large; narrow access before retrying')
        return [row['id'] for row in rows if isinstance(row.get('id'), str)]

    async def scope(self, collection, action='read'):
        role, uid = self._identity()
        if collection not in SCOPED_COLLECTIONS:
            raise HTTPException(403, 'Unsupported CRM collection')
        if role == 'admin':
            return {}
        key = (collection, action)
        if key in self._scopes:
            return self._scopes[key]
        active = {'is_deleted': {'$ne': True}}
        if collection == 'clients':
            if is_demo_identity(self.user):
                dealer_id = self.user.get('dealer_id')
                scope = {'$and': [
                    active,
                    {'dealer_id': dealer_id},
                    {'created_by': uid},
                ]}
                self._scopes[key] = scope
                return scope
            if role in {'bdc_manager', 'bdc'}:
                owners = await self._ids('users', {'role': {'$in': sorted(ROLES - {'admin'})}})
                owner = {'created_by': {'$in': owners}}
            else:
                owner = {'created_by': uid}
            ownership = [owner]
            if action == 'read':
                ownership.append({'collaboration_users': uid, 'created_by': {'$type': 'string', '$ne': ''}})
            scope = {'$and': [active, {'$or': ownership}]}
        elif collection == 'imported_contacts':
            scope = {'imported_by': uid}
        else:
            clients = await self._ids('clients', await self.scope('clients', action))
            if collection in CLIENT_CHILDREN:
                scope = {'$and': [active, {'client_id': {'$in': clients}}]}
            elif collection == 'cosigner_relations':
                scope = {'$and': [active, {'buyer_client_id': {'$in': clients}, 'cosigner_client_id': {'$in': clients}}]}
            else:
                records = await self._ids('user_records', {'client_id': {'$in': clients}, **active})
                scope = {'record_id': {'$in': records}, 'admin_only': {'$ne': True}}
        self._scopes[key] = scope
        return scope

    async def query(self, collection, query, action='read'):
        return {'$and': [query, await self.scope(collection, action)]}

    async def same_client(self, collection, object_id, client_id, action='write'):
        obj = await self.require(collection, object_id, action)
        if obj.get('client_id') != client_id:
            raise HTTPException(400, 'Related objects must belong to the same client')
        return obj
