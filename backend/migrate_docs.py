#!/usr/bin/env python3
"""Migration script to add documents to new array format"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def migrate():
    mongo_url = os.environ.get('MONGO_URL')
    db_name = os.environ.get('DB_NAME')
    if not mongo_url or not mongo_url.strip():
        raise ValueError('MONGO_URL environment variable is required and must not be empty')
    if not db_name or not db_name.strip():
        raise ValueError('DB_NAME environment variable is required and must not be empty')

    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    count = 0
    cursor = db.clients.find({
        '$or': [
            {'income_proof_file_url': {'$ne': None}},
            {'residence_proof_file_url': {'$ne': None}}
        ]
    })
    
    async for c in cursor:
        updates = {}
        
        if c.get('income_proof_file_url') and (not c.get('income_documents') or len(c.get('income_documents', [])) == 0):
            updates['income_documents'] = [{
                'id': 'legacy-income',
                'filename': 'Income_Proof',
                'path': c['income_proof_file_url'],
                'type': 'application/pdf'
            }]
        
        if c.get('residence_proof_file_url') and (not c.get('residence_documents') or len(c.get('residence_documents', [])) == 0):
            updates['residence_documents'] = [{
                'id': 'legacy-residence',
                'filename': 'Residence_Proof',
                'path': c['residence_proof_file_url'],
                'type': 'application/pdf'
            }]
        
        if updates:
            await db.clients.update_one({'id': c['id']}, {'$set': updates})
            print(f"Migrated: {c.get('first_name', '')} {c.get('last_name', '')}")
            count += 1
    
    print(f"\nTotal migrated: {count}")

if __name__ == "__main__":
    asyncio.run(migrate())
