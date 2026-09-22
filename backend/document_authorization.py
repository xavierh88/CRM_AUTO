"""Client document policy. No CRM search, notification or SOLD exceptions."""

ROLES = {"admin", "bdc_manager", "bdc", "telemarketer", "salesperson", "demo"}
MANAGERS = {"bdc_manager", "bdc"}
DOCUMENT_FIELDS = {
    "id_documents", "income_documents", "residence_documents",
    "id_file_url", "income_proof_file_url", "residence_proof_file_url",
    "id_uploaded", "income_proof_uploaded", "residence_proof_uploaded",
}


async def can_access_documents(db, user, client, action="read"):
    if not isinstance(action, str) or action not in {"read", "write", "delete"} or not isinstance(user, dict):
        return False
    role, user_id = user.get("role"), user.get("id")
    if not isinstance(role, str) or role not in ROLES or not isinstance(user_id, str) or not user_id:
        return False
    if not isinstance(client, dict) or not isinstance(client.get("id"), str) or not client["id"]:
        return False

    # Demo uses the normal CRM path, but only for fictional records
    # belonging to its own isolated dealer tenant and identity.
    if user.get('is_demo') or role in ('demo', 'DEMO') or user_id.startswith('demo-'):
        dealer_id = user.get('dealer_id')
        return (
            isinstance(dealer_id, str)
            and bool(dealer_id)
            and client.get('dealer_id') == dealer_id
            and client.get('created_by') == user_id
        )
    if role == "admin":
        return True
    owner_id = client.get("created_by")
    if not isinstance(owner_id, str) or not owner_id:
        return False
    if role in MANAGERS:
        # Existing normal supervision is all known non-admin owners.
        owner = await db.users.find_one({"id": owner_id}, {"role": 1})
        if isinstance(owner, dict) and isinstance(owner.get("role"), str) and owner["role"] in ROLES - {"admin"}:
            return True
    elif owner_id == user_id:
        return True
    collaborators = client.get("collaboration_users")
    return action == "read" and isinstance(collaborators, list) and user_id in collaborators


async def redact_documents(db, user, client):
    if await can_access_documents(db, user, client):
        return client
    return {key: value for key, value in client.items() if key not in DOCUMENT_FIELDS}
