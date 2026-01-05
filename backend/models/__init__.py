# Backend Models Reference
# This file documents all Pydantic models used in the DealerCRM API
# For refactoring purposes - models are still defined in server.py

"""
USER MODELS
-----------
- UserCreate: email, password, name, phone (optional)
- UserActivate: user_id, is_active
- UserRoleUpdate: user_id, role
- UserLogin: email (or username), password
- UserResponse: id, email, name, role, phone, created_at

CLIENT MODELS
-------------
- ClientCreate: first_name, last_name, phone, email, address, apartment
- ClientResponse: id, first_name, last_name, phone, email, address, apartment, 
                  id_uploaded, income_proof_uploaded, last_record_date, created_at, 
                  created_by, is_deleted

USER RECORD MODELS
------------------
- UserRecordCreate: 
    - ID fields: has_id, id_type (DL, Passport, Matricula, etc.)
    - POI fields: has_poi, poi_type (Cash, Company Check, Personal Check, etc.)
    - Other checks: ssn, itin, self_employed
    - POR fields: has_por, por_types[] (Agua, Luz, Gas, Internet, etc.)
    - Bank: bank, bank_deposit_type (Deposito Directo, No deposito directo)
    - Down Payment: down_payment_type (Cash, Tarjeta, Trade), down_payment_cash, down_payment_card
    - Trade-in: trade_make, trade_model, trade_year, trade_title, trade_miles, trade_plate, trade_estimated_value
    - Other: auto, credit, auto_loan, dealer, finance_status, vehicle_make, vehicle_year, 
             sale_month, sale_day, sale_year
    - Legacy: dl, checks, down_payment

- UserRecordResponse: Same fields + id, salesperson_id, salesperson_name, created_at, 
                      is_deleted, previous_record_id, opportunity_number

APPOINTMENT MODELS
------------------
- AppointmentCreate: user_record_id, client_id, date, time, dealer, language, change_time
- AppointmentResponse: id, user_record_id, client_id, salesperson_id, date, time, dealer,
                       language, change_time, status, link_sent_at, reminder_count, created_at

CO-SIGNER MODELS
----------------
- CoSignerRelationCreate: buyer_client_id, cosigner_client_id
- CoSignerRelationResponse: id, buyer_client_id, cosigner_client_id, created_at

CONFIG MODELS
-------------
- ConfigListItem: name, category (bank, dealer, car, id_type, poi_type, por_type)
- ConfigListItemResponse: id, name, category, created_at, created_by

SMS MODELS
----------
- SMSMessageResponse: client_id, twilio_sid, from_number, to_number, body, direction, timestamp, is_read

DATABASE COLLECTIONS
--------------------
- users: User accounts (admin, vendedor)
- clients: Customer information
- user_records: Sales opportunity records
- appointments: Scheduled appointments
- cosigner_relations: Links between buyers and co-signers
- config_lists: Configurable dropdown options
- sms_messages: SMS conversation history
- client_comments: Notes/reviews for clients
- record_comments: Notes for individual records
- notifications: In-app notifications
- imported_contacts: Marketing contacts from imports
- sms_logs: SMS sending history
"""

# Note: Full refactoring to separate files is planned for future iteration
# Current architecture keeps all code in server.py for simplicity
