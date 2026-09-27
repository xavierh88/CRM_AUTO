# CONVERSATIONS RESEARCH — Omnichannel Communication Gateway

## Executive Summary

Dealer AI OS V2 requires an omnichannel communication gateway supporting SMS, WhatsApp, Facebook Messenger, Instagram DM, TikTok DM, and Website Chat. Dealer AI must remain the primary interface; external tools like Chatwoot serve as backend infrastructure only.

---

## Existing Project Foundation (REUSE-FIRST)

The codebase already has a provider-agnostic communication foundation in `backend/communications/`:

- **models.py**: Immutable `Message` dataclass with Channel (SMS, WHATSAPP, EMAIL, FACEBOOK, INSTAGRAM), Actor (CLIENT, HUMAN, AI, SYSTEM), Direction (INBOUND, OUTBOUND), Delivery (RECEIVED, QUEUED, SENT, DELIVERED, FAILED, BLOCKED, SIMULATED)
- **adapters.py**: Protocol-based `CommunicationProvider` with mock implementations:
  - `MockProvider` (SMS, WhatsApp, Email, Facebook, Instagram)
  - `AndroidSmsGateway` with health monitoring (ONLINE/DEGRADED/OFFLINE)
  - `WhatsAppAdapter` (WAITING_CONFIG)
  - `SocialInboundAdapter` (FACEBOOK, INSTAGRAM - INBOUND_ONLY)
- **service.py**: `CommunicationService` with idempotency, contact policy enforcement, event logging
- **policy.py**: `ContactPolicy` with consent, opt-out, quiet hours, frequency caps
- **handoff.py**: `WhatsAppHandoff` for human-first AI/human transition (60s window)
- **prequalify.py**: Mock prequalification provider integration

Frontend: `ConversationsPage.jsx` already implements multi-channel UI with conversation list, chat view, message sending, channel filtering.

Backend API: SMS inbox endpoints exist (`/inbox/{client_id}`, `/inbox/{client_id}/send`, `/inbox/{client_id}/mark-read`), but `/inbox/conversations` returns mock data only.

---

## Channel-by-Channel Analysis

### SMS / Phone (Priority: Android/Physical Phone Gateway)

**Requirement**: Twilio must NOT become primary requirement. Android SMS gateway preferred.

| Solution | License | Maintenance | Key Features |
|----------|---------|-------------|--------------|
| **textbee** (textbee/textbee) | MIT | Active (2026) | REST API, FCM push, multi-device, self-hosted, web dashboard, webhooks |
| **httpsms** (NdoleStudio/httpsms) | AGPL-3.0 | Active | Go backend, simple HTTP API, Docker, webhook support |
| **LibreSMS** (fictus/LibreSMS) | MIT | Active | .NET MAUI, Android, auto-start on boot, REST API |
| **SMSGate** (sms-gate.app) | Apache-2.0 | Active | Android 5.0+, cloud/private/local modes, no registration |
| **SelfhostSim** (ampilares/selfhostsim) | AGPL-3.0 | New (2026) | GoHighLevel-focused, NestJS API, Redis queue, FCM |

**Recommendation**: **textbee** — MIT license, active maintenance, full REST API, webhooks, multi-device support, self-hostable with Docker, web dashboard for device management. Aligns with "Android/physical phone gateway" priority.

**Integration Path**: 
1. Deploy textbee API + Android app on dealer infrastructure
2. Implement `TextBeeProvider` extending `CommunicationProvider` protocol
3. Add webhook endpoint for inbound SMS → `CommunicationService.receive()`
4. Configure `AndroidSmsGateway` health checks via textbee API

---

### WhatsApp / Facebook Messenger / Instagram DM

**Requirement**: Prefer official APIs, simple configuration. Dealer AI UI remains primary.

| Channel | Official API | Config Complexity |
|---------|--------------|-------------------|
| WhatsApp | WhatsApp Business Cloud API (Meta) | App creation, phone verification, webhook, template approval |
| Facebook Messenger | Messenger Platform (Meta) | Page access, webhook, app review for production |
| Instagram DM | Instagram Messaging API (Meta) | Professional account, Page link, webhook, app review |

**Recommendation**: Use **Meta Cloud APIs** directly (not Chatwoot as intermediary). Implement `WhatsAppProvider`, `FacebookProvider`, `InstagramProvider` extending `CommunicationProvider`. Configuration in Dealer AI Settings → Communications → Channel → Connect → Authenticate → Test → Ready.

**Note**: If no real Meta app credentials exist → mark `WAITING_CONFIG` / `NOT_CONFIGURED`, do not fake CONNECTED status.

---

### TikTok DM

**Requirement**: Only officially supported functionality.

**Status**: TikTok Business Messaging API exists but limited access. No public self-serve API as of 2026.

**Recommendation**: Implement `TikTokAdapter` with `status = 'NOT_CONFIGURED'`. Add UI placeholder. Enable only when official API access granted.

---

### Website Chat

**Requirement**: Native to Dealer AI frontend.

**Recommendation**: Implement as internal channel using WebSocket/SSE. No external provider needed. Messages route through `CommunicationService` with `Channel.WEBSITE` (add to Channel enum).

---

## Architecture: Dealer AI → Conversation Gateway → Adapters

```
Dealer AI Frontend (ConversationsPage)
        ↓ REST API
Dealer AI Backend (FastAPI)
        ↓ CommunicationService
Conversation Gateway (backend/communications/service.py)
        ↓ Channel-specific Provider Protocol
┌─────────┬─────────┬──────────┬───────────┬──────────┐
│  SMS    │WhatsApp │ Facebook │ Instagram │ Website  │
│(textbee)│(Meta)   │(Meta)    │(Meta)     │(Internal)│
└─────────┴─────────┴──────────┴───────────┴──────────┘
```

**Key Principles**:
1. Dealer AI owns the UI, conversation state, customer mapping
2. Gateway handles provider protocol translation, retry, idempotency, audit
3. Providers are swappable; add new channels without touching core logic
4. Human/AI handoff via `WhatsAppHandoff` (extendable to other channels)

---

## Implementation Plan

### Phase 1: Core Gateway (Current Sprint)
- [ ] Replace mock `/inbox/conversations` with real DB-backed multi-channel conversations
- [ ] Add `Conversation` model (channel, client_id, status, last_message, unread_count)
- [ ] Add `Message` persistence (channel, direction, actor, delivery_status, provider_id)
- [ ] Implement `GET /inbox/conversations` with filters (search, channel, status, owner)
- [ ] Implement `GET /inbox/{conversation_id}/messages` with pagination
- [ ] Implement `POST /inbox/{conversation_id}/send` via CommunicationService
- [ ] Add `POST /inbox/{conversation_id}/mark-read`
- [ ] Add `POST /inbox/{conversation_id}/handoff` (human takeover / AI release)

### Phase 2: SMS Gateway (textbee)
- [ ] Add textbee webhook endpoint (`/webhook/sms/textbee`)
- [ ] Implement `TextBeeProvider` with send/normalize_inbound
- [ ] Add device health monitoring via textbee API
- [ ] Settings UI: Communications → SMS → Connect (API key, webhook URL)

### Phase 3: WhatsApp/Meta Channels
- [ ] Add Meta webhook endpoint (`/webhook/meta`)
- [ ] Implement `WhatsAppProvider`, `FacebookProvider`, `InstagramProvider`
- [ ] Template management for WhatsApp outbound
- [ ] Settings UI: Communications → WhatsApp/FB/IG → Connect (OAuth/App credentials)

### Phase 4: AI/Human Handoff
- [ ] Integrate `WhatsAppHandoff` into ConversationService
- [ ] UI indicators: AI responding / Human active / Waiting for human
- [ ] Human takeover button, Release to AI button

### Phase 5: TikTok & Website Chat
- [ ] TikTok: placeholder adapter (NOT_CONFIGURED)
- [ ] Website Chat: WebSocket endpoint, internal provider

---

## Configuration Schema (Settings → Communications)

```json
{
  "sms": {
    "provider": "textbee",
    "api_url": "https://sms.dealer.example.com/api/v1",
    "api_key": "***",
    "webhook_url": "https://api.dealer.example.com/webhook/sms/textbee",
    "devices": [{"id": "dev1", "name": "Main Phone", "phone": "+15551234567"}]
  },
  "whatsapp": {
    "provider": "meta",
    "phone_number_id": "***",
    "access_token": "***",
    "webhook_verify_token": "***",
    "templates": [{"name": "welcome", "language": "en_US", "status": "APPROVED"}]
  },
  "facebook": { "provider": "meta", "page_id": "***", "access_token": "***", "webhook_verify_token": "***" },
  "instagram": { "provider": "meta", "page_id": "***", "access_token": "***", "webhook_verify_token": "***" },
  "tiktok": { "provider": "tiktok", "status": "NOT_CONFIGURED" },
  "webchat": { "enabled": true }
}
```

---

## Decision: Chatwoot

**NOT RECOMMENDED** as primary integration because:
1. Adds operational complexity (separate Rails app, PostgreSQL, Redis, Sidekiq)
2. Dealer AI would need to sync conversations bi-directionally
3. Chatwoot's API is designed for agent workspace, not headless gateway
4. Meta webhook handling still requires custom code for AI/human handoff
5. SMS via textbee is simpler and cheaper than Chatwoot's Twilio dependency

**Alternative**: Use Chatwoot **only** if dealer requires agent workspace UI separate from Dealer AI. For Dealer AI V2, native gateway is superior.

---

## Security & Compliance Notes

- All providers implement `ContactPolicy` (consent, opt-out, quiet hours, frequency)
- Audit trail via `CommunicationEvent` (timestamp, reason, delivery status)
- Dealer isolation enforced via `CRMAccess` on conversation/message queries
- No real external communications in demo mode (simulated delivery)
- Webhook signature validation required for all providers
- API keys stored encrypted, rotated via settings UI

---

## Files to Create/Modify

**New**:
- `backend/communications/providers/textbee.py` — TextBeeProvider implementation
- `backend/communications/providers/meta.py` — WhatsApp/Facebook/Instagram providers
- `backend/communications/conversation.py` — Conversation model & repository
- `backend/routes/inbox.py` — Multi-channel inbox endpoints
- `frontend/src/pages/ConversationsPage.jsx` — Enhance with real API, handoff UI

**Modify**:
- `backend/communications/models.py` — Add WEBSITE channel, Conversation dataclass
- `backend/communications/adapters.py` — Add provider registry
- `backend/server.py` — Register inbox routes, webhook endpoints
- `backend/seed_demo.py` — Seed fictional conversations for all channels