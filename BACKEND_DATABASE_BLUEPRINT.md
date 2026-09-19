# Khan Law Associates Backend and Database Blueprint

This document describes the backend that fits the current Django project and the database structure needed for a complete client/staff tax-services portal.

## 1. Recommended architecture

Use a modular Django monolith first. It is simpler to deploy and is sufficient for this portal.

```text
Browser
  |
  +-- Public website: website app
  +-- Client portal: accounts app
  +-- Staff portal: dashboard app
  |
Django URL routing
  |
Views or API endpoints
  |
Forms/serializers -> service layer -> models
  |
PostgreSQL database + private object/file storage
```

Recommended production components:

- Django 5.x
- PostgreSQL instead of SQLite in production
- Django sessions for the server-rendered portal
- Django REST Framework only if a separate mobile/JavaScript client is required
- Private object storage for client documents, such as S3-compatible storage
- Celery and Redis later for email, reminders, virus scanning, and report generation
- Django admin for technical administration, not as the client-facing portal

Keep business rules in service functions, for example `register_client()`, `review_document()`, `assign_case()`, and `change_case_status()`. Views should authenticate the request, validate input, call the service, and render or redirect.

## 2. Current project structure

The current code already contains these areas:

- `accounts`: login, registration, `Profile`, client portal, client document upload
- `dashboard`: clients, documents, tax cases, tax returns, tasks, services, reports, staff management, activity logs
- `website`: public home, about, services, and contact pages
- Django `User`: username/password identity and staff flags
- SQLite: suitable for local development only

Current relationships:

```text
User 1---1 Profile
User 1---0..1 Client
Client 1---many ClientDocument
Client 1---many TaxCase
Client 1---many TaxReturn
TaxCase 1---many TaxCaseTask
User 1---many assigned TaxCase
User 1---many reviewed ClientDocument
Client/TaxCase/User 1---many ActivityLog
```

The current `Client.requested_services` and `Service.required_registration_fields` JSON fields work for an MVP, but important workflow data should become relational tables as the system grows.

## 3. Core database tables

### 3.1 `auth_user`

Use Django's built-in user table initially.

Important fields:

- `id` bigint primary key
- `username` unique login identifier
- `email`
- `password` hashed by Django; never store plain passwords
- `first_name`, `last_name`
- `is_active`
- `is_staff`, `is_superuser`
- `date_joined`, `last_login`

For a new production system, a custom user model with email login is preferable. If existing data must be preserved, keep the current `User` model and plan a later migration carefully.

### 3.2 `accounts_profile`

One row per user.

- `id` primary key
- `user_id` unique foreign key to `auth_user`
- `role`: `CLIENT`, `STAFF`, or `ADMIN`
- `account_status`: `PENDING`, `ACTIVE`, `SUSPENDED`, or `CLOSED`
- `phone`
- `avatar` optional private/public image reference
- `can_manage_clients`
- `can_manage_documents`
- `can_manage_tax_work`
- `created_at`, `updated_at`
- `last_login_ip` optional security field

Do not rely only on `is_staff`. Every protected view should check both role and account status.

### 3.3 `dashboard_client`

The legal/business client profile. This is separate from authentication so staff-created clients can exist before portal access is created.

- `id` primary key
- `user_id` nullable unique foreign key to `auth_user`
- `full_name`
- `cnic` or national identity number, unique after normalization
- `phone`
- `email`
- `address`
- `business_name`
- `business_type`
- `business_details`
- `ntn`
- `tax_information`
- `status`: `NEW`, `UNDER_REVIEW`, `INFORMATION_PENDING`, `IN_PROGRESS`, `COMPLETED`, `ARCHIVED`
- `created_at`, `updated_at`
- `created_by_id` foreign key to the staff user who created it

Normalize CNIC and phone before saving. Store the display value and, if necessary, a normalized search value.

### 3.4 `service`

A configurable service offered by the firm.

- `id` primary key
- `name` unique
- `code` unique, for example `NTN_REGISTRATION`
- `description`
- `is_active`
- `default_due_days`
- `created_at`, `updated_at`

### 3.5 `service_required_field`

Replaces the list-like configuration inside `Service.required_registration_fields` when validation becomes complex.

- `id` primary key
- `service_id` foreign key
- `field_name`: `full_name`, `cnic`, `phone`, `email`, `address`, `business_details`, `ntn`, or `tax_information`
- `is_required`
- unique constraint on `(service_id, field_name)`

### 3.6 `client_service_request`

Records which services a client requested. This replaces `Client.requested_services` JSON.

- `id` primary key
- `client_id` foreign key
- `service_id` foreign key
- `status`: `REQUESTED`, `APPROVED`, `DECLINED`, `CANCELLED`, `COMPLETED`
- `requested_at`
- `approved_at` nullable
- `approved_by_id` nullable staff foreign key
- `notes`
- unique constraint on `(client_id, service_id, active state)` as appropriate

### 3.7 `tax_case`

The operational work item for one client and one service. The current `TaxCase` is already close to this model.

- `id` primary key
- `case_number` unique human-readable identifier, such as `KLA-2026-000123`
- `client_id` foreign key
- `service_id` foreign key
- `service_request_id` nullable foreign key
- `assigned_to_id` nullable staff foreign key
- `status`: `NEW`, `UNDER_REVIEW`, `INFORMATION_PENDING`, `PROCESSING`, `FILING`, `COMPLETED`, `CANCELLED`
- `priority`: `LOW`, `NORMAL`, `HIGH`, `URGENT`
- `opened_date`
- `target_date` nullable
- `completed_date` nullable
- `notes`
- `created_at`, `updated_at`

Add indexes on `(client_id, status)`, `(assigned_to_id, status)`, and `(target_date, status)`.

### 3.8 `tax_case_status_history`

Never lose status history by overwriting only the current status.

- `id` primary key
- `case_id` foreign key
- `old_status` nullable
- `new_status`
- `changed_by_id` foreign key to `auth_user`
- `comment`
- `created_at`

Every case status change should create both a history row and an audit event inside one database transaction.

### 3.9 `tax_case_task`

A checklist item under a case.

- `id` primary key
- `case_id` foreign key
- `title`
- `details`
- `assigned_to_id` nullable staff foreign key
- `status`: `TODO`, `IN_PROGRESS`, `DONE`, `CANCELLED`
- `due_date` nullable
- `completed_at` nullable
- `created_by_id`
- `created_at`, `updated_at`

### 3.10 `client_document`

Metadata for a private uploaded file. Keep the file outside the database; store only its storage key and metadata.

- `id` primary key
- `client_id` foreign key
- `case_id` nullable foreign key
- `uploaded_by_id` foreign key
- `title`
- `document_type`: `IDENTITY`, `TAX`, `FINANCIAL`, `LEGAL`, `OTHER`
- `storage_key` or Django `FileField`
- `original_filename`
- `mime_type`
- `file_size`
- `checksum`
- `review_status`: `PENDING`, `APPROVED`, `REJECTED`, `REPLACED`
- `reviewer_notes` visible to the client
- `uploaded_at`, `updated_at`
- `reviewed_by_id` nullable
- `reviewed_at` nullable

Use a separate `document_request` table for missing/corrected documents rather than overloading one text field.

### 3.11 `document_request`

- `id` primary key
- `client_id` foreign key
- `case_id` nullable foreign key
- `created_by_id` staff foreign key
- `title`
- `instructions`
- `status`: `OPEN`, `SUBMITTED`, `ACCEPTED`, `CANCELLED`
- `due_date` nullable
- `resolved_at` nullable
- `created_at`, `updated_at`

A submitted `ClientDocument` may reference the request that it satisfies.

### 3.12 `tax_return`

A filing record, preferably linked to the relevant case.

- `id` primary key
- `client_id` foreign key
- `case_id` nullable foreign key
- `tax_type`: `INCOME_TAX` or `SALES_TAX`
- `tax_year` with a validated format such as `2025-2026`
- `due_date` nullable
- `filing_reference`
- `status`: `DRAFT`, `INFORMATION_PENDING`, `IN_REVIEW`, `FILED`, `COMPLETED`
- `notes`
- `created_by_id`
- `created_at`, `updated_at`

Add a unique constraint for `(client_id, tax_type, tax_year)` unless amended returns are supported. If amendments are required, add `version` and `is_amended`.

### 3.13 `conversation` and `message`

Add these if staff and clients need communication inside the portal.

`conversation`:

- `id`
- `client_id`
- `case_id` nullable
- `created_at`, `updated_at`
- `is_closed`

`message`:

- `id`
- `conversation_id`
- `sender_id`
- `body`
- `attachment_id` nullable
- `read_at` nullable
- `created_at`

Do not use email as the source of truth for case communication. Email can be a notification channel.

### 3.14 `notification`

- `id`
- `recipient_id`
- `notification_type`
- `title`
- `body`
- `url`
- `read_at` nullable
- `created_at`

### 3.15 `audit_event`

Replace or extend the current `ActivityLog` for compliance-grade auditing.

- `id`
- `actor_id` nullable, because deleted/system users are possible
- `client_id` nullable
- `case_id` nullable
- `event_type`
- `object_type`
- `object_id`
- `description`
- `metadata` JSON for non-sensitive technical context
- `ip_address` nullable
- `user_agent` nullable
- `created_at`

Audit events should be append-only. Do not allow ordinary staff users to edit or delete them.

## 4. Relationship summary

```text
User
  +-- Profile
  +-- Client (optional)
  +-- assigned TaxCases
  +-- reviewed Documents
  +-- AuditEvents

Client
  +-- ClientServiceRequests -- Service -- ServiceRequiredFields
  +-- TaxCases -- TaxCaseStatusHistory
  |             +-- TaxCaseTasks
  |             +-- TaxReturns
  |             +-- DocumentRequests
  |             +-- Documents
  +-- Documents
  +-- Conversations -- Messages
  +-- Notifications
  +-- AuditEvents
```

Use `CASCADE` for child workflow records that have no meaning without their parent case. Use `SET_NULL` for actor/assignee/reviewer fields so historical records survive account deletion. Prefer archive flags over deleting clients or cases.

## 5. Backend modules

Suggested Django apps as the system grows:

- `accounts`: authentication, profiles, roles, password reset, account lifecycle
- `clients`: client profile and service requests
- `cases`: tax cases, statuses, assignments, tasks, returns
- `documents`: uploads, private downloads, reviews, document requests
- `communications`: conversations, messages, notifications, email events
- `audit`: append-only audit events and activity history
- `website`: public content and contact inquiries
- `reports`: staff-only dashboards, CSV/PDF exports

The existing `dashboard` app can remain as the UI app during the first phase. Split it only when models and ownership become difficult to maintain.

## 6. URL and endpoint design

Server-rendered routes can continue using the current names. Organize them by ownership:

```text
/                         public website
/about/
/services/
/contact/
/client/login/
/client/register/
/client/portal/
/client/profile/
/client/documents/
/client/cases/<case_id>/
/client/cases/<case_id>/messages/
/staff/
/staff/clients/
/staff/clients/<client_id>/
/staff/cases/
/staff/cases/<case_id>/
/staff/documents/
/staff/documents/<document_id>/review/
/staff/reports/
/staff/administration/
```

If an API is needed, use versioned resources:

```text
/api/v1/auth/me/
/api/v1/clients/me/
/api/v1/clients/me/documents/
/api/v1/clients/me/cases/
/api/v1/staff/clients/
/api/v1/staff/cases/
/api/v1/staff/documents/<id>/review/
/api/v1/services/
/api/v1/notifications/
```

Never accept `client_id` from a client browser to decide ownership. Resolve the client from `request.user.client_profile`, then filter every query by that client. Staff access must use explicit permission checks.

## 7. Permission matrix

| Action | Client | Staff with permission | Admin |
|---|---:|---:|---:|
| View own profile | yes | yes | yes |
| Edit own personal fields | yes | no/controlled | yes |
| View own cases/documents | yes | yes | yes |
| Upload own documents | yes | yes | yes |
| Review documents | no | documents permission | yes |
| Create/edit clients | no | clients permission | yes |
| Assign cases | no | tax-work permission | yes |
| Change case status | no | tax-work permission | yes |
| Manage staff accounts | no | no | yes |
| Configure services | no | no | yes |
| View audit history | own activity only | authorized scope | all |

Use Django permissions and groups for long-term flexibility. Keep the current profile booleans only as a transitional compatibility layer.

## 8. Important backend rules

1. Wrap registration, case creation, review, assignment, and status changes in `transaction.atomic()`.
2. Validate uploaded content by size, extension, MIME type, and preferably antivirus scan. Never trust the filename extension alone.
3. Serve private documents through an authenticated download view or short-lived signed URL. Do not expose the media directory publicly in production.
4. Add CSRF protection to every browser POST and use POST for delete/status actions.
5. Use `select_related` and `prefetch_related` on portal and dashboard pages to avoid N+1 queries.
6. Add pagination to clients, documents, cases, logs, and messages.
7. Normalize and unique-check CNIC, email, phone, case numbers, and tax-year combinations.
8. Do not expose internal staff notes to clients. Store client-visible notes separately where possible.
9. Log authentication events, permission failures, document access, exports, and all workflow changes.
10. Configure secure cookies, HTTPS, HSTS, `SECURE_PROXY_SSL_HEADER`, allowed hosts, password validators, and rate limiting before deployment.
11. Move `SECRET_KEY`, database credentials, email credentials, and storage credentials into environment variables.
12. Back up PostgreSQL and uploaded files independently; test restoration, not just backup creation.

## 9. Migration path from the current code

1. Keep the current models and deploy the MVP safely with PostgreSQL.
2. Add `updated_at`, `created_by`, `case_number`, `priority`, and indexes to existing workflow tables.
3. Add `Service.code` and migrate service names to stable codes.
4. Create `ClientServiceRequest` rows from each value in `Client.requested_services`.
5. Add `service_id` to `TaxCase` and map existing `service_type` values to `Service` rows.
6. Create `TaxCaseStatusHistory` rows for current statuses, then update the case service to write history on every transition.
7. Create `DocumentRequest` and migrate non-empty `missing_or_corrected_request` values into open requests.
8. Add storage metadata and private download handling for existing documents.
9. Link existing `TaxReturn` rows to cases where a reliable match exists; leave `case_id` nullable when it does not.
10. Add audit events for new changes, then backfill only the events that can be reconstructed reliably.
11. Replace JSON reads in forms/views with relational queries.
12. Remove old JSON fields only after a verified backup and a release in which the new fields are authoritative.

Use data migrations for steps 4, 5, and 7. Test migrations against a copy of the real SQLite data before production.

## 10. Minimum production checklist

- PostgreSQL configured and migrations applied
- Environment-based secrets and `DEBUG=False`
- HTTPS and secure session/CSRF cookies
- Private media storage and authenticated downloads
- File size/type validation and malware scanning
- Email verification and password reset
- Staff account approval and account suspension
- Object-level authorization tests for every client route
- Database, media, and restoration backups
- Pagination, indexes, and query-count checks
- Audit trail for sensitive actions
- Automated tests for registration, login separation, client isolation, document review, case transitions, and permissions
- Error monitoring and structured application logs

## 11. Testing priorities

The highest-value tests are:

- A client cannot view another client's profile, case, document, or download URL.
- A client cannot call a staff URL by changing the URL or HTTP method.
- Suspended and pending accounts cannot log in to protected areas.
- A staff member without a permission cannot perform that operation.
- Document review stores reviewer, timestamp, status, and client-visible feedback.
- Every case status transition creates exactly one history record and audit event.
- Registration is atomic: a failed supporting-document save must not leave a partial account/client record.
- Duplicate CNIC, duplicate active service requests, and duplicate tax returns are rejected.
- Uploaded files cannot escape the configured storage path or be downloaded without authorization.

This structure preserves the current application while giving it a normalized workflow model, stronger access control, private document handling, and a reliable history of tax work.
