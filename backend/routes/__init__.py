# API Routes Reference
# This file documents all API endpoints in the DealerCRM API
# For refactoring purposes - routes are still defined in server.py

"""
AUTHENTICATION ROUTES (/api/auth)
---------------------------------
POST /api/auth/register - Register new user (requires admin approval)
POST /api/auth/login - Login and get JWT token
GET /api/auth/me - Get current user info
GET /api/auth/users - Get all users (admin only)
PUT /api/auth/users/status - Activate/deactivate user (admin only)
PUT /api/auth/users/role - Change user role (admin only)
DELETE /api/auth/users/{user_id} - Delete user (admin only)

CLIENT ROUTES (/api/clients)
----------------------------
GET /api/clients - Get all clients (paginated, searchable)
POST /api/clients - Create new client
GET /api/clients/{client_id} - Get single client
PUT /api/clients/{client_id} - Update client
DELETE /api/clients/{client_id} - Soft delete client
GET /api/clients/deleted - Get deleted clients (admin only)
POST /api/clients/{client_id}/restore - Restore deleted client
GET /api/clients/search/phone/{phone} - Search client by phone
POST /api/clients/{client_id}/update-last-contact - Update last contact timestamp

CLIENT COMMENTS ROUTES
----------------------
GET /api/clients/{client_id}/comments - Get all comments for client
POST /api/clients/{client_id}/comments - Add comment to client
DELETE /api/clients/{client_id}/comments/{comment_id} - Delete comment

USER RECORDS ROUTES (/api/user-records)
---------------------------------------
GET /api/user-records - Get records (filtered by client_id or all)
POST /api/user-records - Create new record
GET /api/user-records/{record_id} - Get single record
PUT /api/user-records/{record_id} - Update record
DELETE /api/user-records/{record_id} - Soft delete record

RECORD COMMENTS ROUTES
----------------------
GET /api/user-records/{record_id}/comments - Get record comments
POST /api/user-records/{record_id}/comments - Add comment to record
DELETE /api/user-records/{record_id}/comments/{comment_id} - Delete comment

APPOINTMENT ROUTES (/api/appointments)
--------------------------------------
GET /api/appointments - Get all appointments
POST /api/appointments - Create appointment
PUT /api/appointments/{appointment_id}/status - Update appointment status
DELETE /api/appointments/{appointment_id} - Delete appointment

CO-SIGNER ROUTES (/api/cosigners)
---------------------------------
GET /api/cosigners/{client_id} - Get co-signers for a client
POST /api/cosigners - Create co-signer relation
DELETE /api/cosigners/{relation_id} - Remove co-signer relation

CONFIG LISTS ROUTES (/api/config-lists)
---------------------------------------
GET /api/config-lists/{category} - Get items (bank, dealer, car, id_type, poi_type, por_type)
POST /api/config-lists - Create config item (admin only)
PUT /api/config-lists/{item_id} - Update config item (admin only)
DELETE /api/config-lists/{item_id} - Delete config item (admin only)

DASHBOARD ROUTES (/api/dashboard)
---------------------------------
GET /api/dashboard/stats - Get dashboard statistics (with period filter)
GET /api/dashboard/salesperson-performance - Get performance by salesperson (admin only)

SMS ROUTES (/api/sms)
---------------------
POST /api/sms/send - Send SMS to client
GET /api/sms/inbox/{client_id} - Get SMS conversation history
POST /api/sms/inbox - Send message to inbox conversation
POST /api/sms/send-public-link - Send public form link via SMS
POST /api/sms/marketing/send - Send marketing SMS
GET /api/sms/marketing/stats - Get marketing SMS statistics
POST /webhook/twilio/sms - Twilio webhook for incoming SMS

NOTIFICATIONS ROUTES (/api/notifications)
-----------------------------------------
GET /api/notifications - Get user notifications
PUT /api/notifications/{notification_id}/read - Mark notification as read

SCHEDULER ROUTES (/api/scheduler)
---------------------------------
GET /api/scheduler/status - Get scheduler status

IMPORT ROUTES (/api/import)
---------------------------
POST /api/import/contacts - Import contacts from Excel
GET /api/import/contacts - Get imported contacts
POST /api/import/contacts/{contact_id}/opt-out - Opt out contact
POST /api/import/handle-duplicate - Handle duplicate during import

PUBLIC ROUTES (/api/public)
---------------------------
GET /api/public/appointments/{appointment_id} - Get appointment details (public)
PUT /api/public/appointments/{appointment_id} - Update appointment (public)
POST /api/public/upload-documents/{client_id} - Upload documents (public)
"""

# Note: Full refactoring to separate route files is planned for future iteration
