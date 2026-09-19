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

## 12. Complete implementation runbook

This section is the execution order for building the backend and database. Give one phase at a time to Codex or another MCP coding tool. Do not ask an agent to implement all phases in one prompt. After every phase, run its acceptance checks and commit the result.

### Phase 0: Give the coding agent project rules

Use this instruction at the start of every implementation prompt:

1. Work inside the existing Django project; do not replace the project with a new framework.
2. Read the current models, migrations, URLs, forms, views, settings, templates, and tests before editing.
3. Preserve existing working behavior unless the phase explicitly changes it.
4. Use Django ORM and migrations; never edit the SQLite or PostgreSQL database manually.
5. Use transactions for multi-table operations.
6. Keep client object-level authorization separate from staff role authorization.
7. Do not expose private documents through a public URL.
8. Do not put passwords, API keys, database credentials, or production secrets in source code.
9. Add focused tests for every new model rule, permission rule, and workflow transition.
10. Run `python manage.py check`, the relevant tests, and migration checks before reporting completion.
11. Do not delete or rewrite unrelated user changes.
12. Report changed files, migrations created, commands run, and any unresolved risks.

### Phase 1: Inspect and freeze the baseline

1. Confirm the Django version and installed packages.
2. Run `python manage.py check`.
3. Run `python manage.py showmigrations`.
4. Run the complete existing test suite.
5. Record the current database tables and migration state.
6. Record all current URL names because templates may depend on them.
7. Back up `db.sqlite3` before data migrations.
8. Confirm that `db.sqlite3`, `media/`, `.env`, and Python cache files are ignored by Git.
9. Do not change models during this phase.

Acceptance criteria:

- The project starts locally.
- Existing tests pass or known failures are documented.
- No migration is pending unexpectedly.
- A database backup exists outside the repository.

Prompt:

> Inspect this existing Django project and produce a baseline report. Run the system check, list installed apps, migration status, models, URL namespaces, current tests, and security risks. Do not edit files. End with a prioritized implementation plan for Phase 2.

### Phase 2: Configure environments and dependencies

1. Keep SQLite as the default local development database if it helps onboarding.
2. Add PostgreSQL environment configuration for staging and production.
3. Read `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, database variables, email variables, and storage variables from environment values.
4. Add separate settings behavior for development, testing, and production when the project is large enough to justify it.
5. Add packages only when required:
  - `psycopg[binary]` for PostgreSQL
  - `django-environ` or an equivalent environment loader
  - `djangorestframework` only if an API is required
  - `django-storages` and the provider SDK for object storage
  - `celery` and `redis` only when background jobs are introduced
6. Pin compatible package ranges in `requirements.txt`.
7. Add `.env.example` containing variable names only, never real values.
8. Configure static files separately from media files.

Acceptance criteria:

- `DEBUG=False` works with production-like settings.
- Missing required production settings fail clearly at startup.
- Local development still works without cloud services.
- No secret appears in Git history or tracked files.

### Phase 3: Harden authentication and accounts

1. Keep Django `User` initially to avoid an unsafe user-table migration.
2. Keep one `Profile` per user using a one-to-one relationship.
3. Add profile fields for role, account status, phone, timestamps, and permissions.
4. Create profile rows automatically when a user is created, or use an explicit account service and test it.
5. Implement client login and staff login as separate flows.
6. Reject client users from staff URLs and staff users from client-only workflows where appropriate.
7. Reject `PENDING`, `SUSPENDED`, and `CLOSED` accounts from protected login flows.
8. Add password reset and email verification before production.
9. Add login throttling or rate limiting.
10. Never use `is_staff` as the only authorization condition.
11. Prefer Django groups and permissions for new capabilities; keep current profile booleans during migration.
12. Log login, logout, failed login, account suspension, password reset, and permission failures.

Acceptance criteria:

- A client cannot access staff pages.
- A staff user cannot be treated as a client merely by changing a URL.
- Suspended accounts cannot access protected pages.
- Passwords are always hashed by Django.
- Login and account-status tests pass.

### Phase 4: Implement the normalized database

Create models in dependency order. Each model change must have a migration and focused tests.

1. Add or complete `Service` with `name`, `code`, `description`, `is_active`, and `default_due_days`.
2. Add `ServiceRequiredField` with a unique `(service, field_name)` constraint.
3. Add `Client` fields that are missing from the current project, including `updated_at`, business fields, normalized identity fields, and `created_by`.
4. Add `ClientServiceRequest` to replace service names stored in JSON.
5. Extend `TaxCase` with `case_number`, `service`, `service_request`, `priority`, `created_by`, and indexes.
6. Add `TaxCaseStatusHistory` as an append-only status transition table.
7. Extend `TaxCaseTask` with task status, assignment, creator, completion time, and timestamps.
8. Extend `ClientDocument` with case/request links, uploader, original filename, MIME type, size, checksum, and timestamps.
9. Add `DocumentRequest` for missing or corrected documents.
10. Link `TaxReturn` to a case and add creator, amendment, and uniqueness rules as required.
11. Add `Conversation`, `Message`, and `Notification` only when messaging is part of the requested release.
12. Add `AuditEvent` and preserve the existing `ActivityLog` until all consumers are migrated.
13. Add database indexes for client identity searches, case status queues, assignments, due dates, document review queues, and audit dates.
14. Use `PROTECT` or archive behavior for important business records where accidental deletion would be harmful.
15. Use `SET_NULL` for historical actor, reviewer, and assignee references.

Acceptance criteria:

- Every foreign key has an intentional `on_delete` rule.
- Every status has defined allowed values.
- Duplicate CNIC, case number, active service request, and tax return rules are enforced.
- `makemigrations --check` reports no model drift.
- Migrations apply to an empty database and a copy of the existing database.

### Phase 5: Write data migrations

1. Create or update service seed data with stable service codes.
2. Convert every value in `Client.requested_services` into a `ClientServiceRequest` row.
3. Map every current `TaxCase.service_type` value to a `Service` row.
4. Generate case numbers for existing cases.
5. Create an initial status-history row for each existing case.
6. Move non-empty `missing_or_corrected_request` values into `DocumentRequest` rows.
7. Populate document metadata for existing files when it can be calculated safely.
8. Match existing tax returns to cases only when the match is unambiguous.
9. Do not delete old fields in the same migration that copies their data.
10. Verify row counts before and after each data migration.
11. Keep a rollback plan and database backup for every production migration.
12. Remove legacy JSON fields only after the new relational fields are used everywhere.

Acceptance criteria:

- The number of clients and documents is unchanged.
- Every valid requested service has a relational row.
- Every case has a stable service and case number.
- Migration output and row-count checks are recorded.

### Phase 6: Create the service layer

Create a service module for each business area. Do not put complex workflow rules directly in templates or large views.

1. `accounts/services.py`
  - register client
  - create staff account
  - activate, suspend, or close account
  - reset or verify account state
2. `clients/services.py`
  - create client profile
  - update client profile
  - request services
  - link an existing staff-created client to a portal user
3. `cases/services.py`
  - create case
  - assign case
  - change case status
  - create task
  - complete task
  - create status history and audit event
4. `documents/services.py`
  - upload document
  - create document request
  - review document
  - replace rejected document
  - securely download document
5. `communications/services.py`
  - create conversation
  - send message
  - mark messages read
  - create notification
6. `audit/services.py`
  - write append-only audit events
  - record actor, target, request metadata, and timestamp

Every service function must:

1. Validate the input.
2. Validate the actor's permission.
3. Resolve the target object safely.
4. Execute related writes in `transaction.atomic()`.
5. Write an audit event for sensitive actions.
6. Return the created or updated object.
7. Raise clear domain errors that the view can display safely.

### Phase 7: Implement client workflows

1. Client registration must create the user, profile, client, requested services, optional document, and audit event atomically.
2. Registration must not create partial records when an upload or database write fails.
3. Existing client records must be linkable to a user without creating duplicates.
4. Client profile editing must never allow the client to change staff-managed status, assignment, internal notes, or audit data.
5. The client portal must show only the signed-in client's records.
6. Client case pages must show status, target date, requested information, approved documents, and client-visible messages.
7. Client document uploads must validate size, MIME type, extension, and ownership.
8. Client requests for additional services must create relational service-request rows.
9. Client-visible errors must not expose stack traces, database IDs unnecessarily, or internal notes.

### Phase 8: Implement staff workflows

1. Build staff client search with pagination and indexed filtering.
2. Build client detail pages with cases, documents, returns, tasks, and allowed activity history.
3. Build service-request approval and case creation.
4. Build assignment to staff users.
5. Build case status transitions with valid transition rules.
6. Build task creation, assignment, completion, and due-date filtering.
7. Build document review with approval, rejection, reviewer notes, and document requests.
8. Build tax-return creation, editing, filing-reference tracking, and status changes.
9. Build service configuration for administrators only.
10. Build staff-account creation, activation, suspension, and permission management.
11. Build reports and CSV export with authorization and audit logging.
12. Add pagination and predictable ordering to every staff list.

### Phase 9: Implement URLs, forms, and APIs

For server-rendered pages:

1. Keep public routes under `website`.
2. Keep client routes under `client` URL names.
3. Keep staff routes under `staff` URL names.
4. Use `login_required`, `staff_required`, `admin_required`, and object-level ownership checks.
5. Use Django forms for HTML forms and validate every uploaded file.
6. Use POST for create, update, delete, review, assignment, and status actions.
7. Require CSRF tokens on every browser form.
8. Return a safe redirect after successful POST requests.

For an API:

1. Use Django REST Framework and `/api/v1/` versioning.
2. Create serializers for users, clients, services, cases, tasks, documents, returns, messages, and notifications.
3. Use separate client and staff viewsets or permission classes.
4. Never accept a client ID as the authority for client ownership.
5. Use pagination, filtering, ordering, and consistent error responses.
6. Add API authentication only if a separate frontend or mobile client needs it.
7. Write API tests for authentication, ownership, permissions, validation, and response shapes.

### Phase 10: Secure document storage

1. Store document metadata in the database and file contents in private storage.
2. Generate storage keys that do not expose CNIC, email, or other sensitive information.
3. Preserve the original filename only as metadata.
4. Limit file size in Django settings and server configuration.
5. Validate extension, detected MIME type, and file signature where possible.
6. Reject executable and script file types.
7. Scan uploads for malware before making them available to staff or clients.
8. Serve downloads through an authorization check or short-lived signed URL.
9. Log every sensitive document download.
10. Do not use `static/` for client files.
11. Do not serve `MEDIA_ROOT` directly in production unless the storage layer enforces private access.
12. Define retention, replacement, and deletion rules for documents.

### Phase 11: Notifications and background work

1. Add email templates for registration, approval, document requests, document review, case assignment, status changes, and password reset.
2. Store notification records in the database so users can see unread history.
3. Send emails asynchronously after the database transaction succeeds.
4. Use an outbox or transaction-safe task dispatch so an email is not sent for a rolled-back change.
5. Add retry handling and failure logging for email jobs.
6. Add reminders for overdue document requests, case targets, and tax-return due dates.
7. Never put sensitive document contents or passwords in email messages.

### Phase 12: Reports and administration

1. Add dashboard counts for active clients, open cases, pending documents, overdue tasks, and due tax returns.
2. Filter every report by the requesting staff user's permission and allowed scope.
3. Stream large CSV exports instead of loading all rows into memory.
4. Audit every export because reports may contain personal information.
5. Add service configuration screens for service name, code, active state, required fields, and default due period.
6. Prevent deletion of services already used by cases; archive them instead.
7. Show a clear audit history for account, client, case, document, and return changes.

### Phase 13: Testing plan

Create tests in layers:

1. Model tests:
  - constraints
  - status choices
  - case number generation
  - tax-year validation
  - timestamp behavior
2. Service tests:
  - atomic registration
  - service-request creation
  - valid and invalid case transitions
  - status history creation
  - audit event creation
  - document review behavior
3. Permission tests:
  - client isolation
  - staff permission flags/groups
  - admin-only actions
  - suspended accounts
4. View/API tests:
  - GET pages
  - POST forms
  - CSRF behavior
  - redirects
  - validation errors
  - pagination and filters
5. File tests:
  - allowed file types
  - rejected file types
  - maximum size
  - private download authorization
6. Migration tests:
  - empty database migration
  - copy of current SQLite data
  - data migration row counts
7. Security tests:
  - IDOR attempts using another client ID
  - unauthorized document downloads
  - staff-to-client boundary
  - open redirect protection
  - unsafe upload names

Run at minimum:

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

### Phase 14: Deployment

1. Provision PostgreSQL.
2. Provision private object storage for media.
3. Provision email credentials and, if needed, Redis/Celery.
4. Set all environment variables in the deployment platform.
5. Set `DEBUG=False`.
6. Set exact `ALLOWED_HOSTS` and CSRF trusted origins.
7. Configure HTTPS, secure cookies, HSTS, and proxy headers.
8. Run `python manage.py migrate`.
9. Run `python manage.py collectstatic --noinput`.
10. Create the first administrator with a secure process.
11. Run smoke tests for public pages, client login, staff login, document upload, document review, case updates, and downloads.
12. Configure database backups and media backups.
13. Test restoration of both database and media backups.
14. Configure error monitoring and structured logs.
15. Use a process manager and a production WSGI/ASGI server.
16. Never run `runserver` in production.

## 13. Prompt sequence for Codex or MCP tools

Use these prompts in order. Ask the tool to stop after each prompt so that tests can be reviewed before the next phase.

### Prompt 1: Baseline

> Inspect the existing Django project for the KLA client and staff portal. Do not edit files. Report the installed apps, current models, migrations, URLs, forms, views, authentication flow, current tests, database engine, file storage, and all risks related to authorization and sensitive documents. Run `python manage.py check` and `python manage.py showmigrations`. Recommend the smallest first implementation step.

### Prompt 2: Environment configuration

> Implement production-safe Django configuration without changing user-facing behavior. Add environment-based secret key, debug, allowed hosts, database, email, and storage settings. Keep local SQLite development working. Add `.env.example`, update requirements only when necessary, and add or update `.gitignore`. Run the system check and explain every changed setting.

### Prompt 3: Database models

> Implement the normalized database models described in `BACKEND_DATABASE_BLUEPRINT.md`. Start with Service, ServiceRequiredField, ClientServiceRequest, TaxCase fields, TaxCaseStatusHistory, task fields, document metadata, DocumentRequest, and TaxReturn relationships. Preserve existing fields for compatibility. Create migrations, indexes, constraints, and focused tests. Do not remove legacy JSON fields yet. Run migration checks and tests.

### Prompt 4: Data migration

> Write safe Django data migrations that convert existing requested services, service types, case statuses, and missing-document requests into the new relational models. Do not delete source fields. Use reversible or clearly documented migrations, preserve row counts, and test against a copy of the current SQLite database. Report before-and-after counts.

### Prompt 5: Service layer

> Create transaction-safe service functions for client registration, client updates, service requests, case creation, case assignment, case status changes, task updates, document review, document requests, and tax-return updates. Enforce permissions in the service layer, create audit events, and add unit tests. Refactor existing views to call these services without changing route names.

### Prompt 6: Authorization

> Audit every client and staff URL for object-level authorization. Ensure clients can access only records belonging to their authenticated client profile, and staff actions require the correct permission or admin role. Add tests that attempt to access another client's profile, case, document, and download URL. Fix any IDOR or privilege-escalation issue found.

### Prompt 7: Documents

> Harden client document handling. Validate extension, MIME type, file signature where possible, and maximum size. Store private files outside public static assets. Add authenticated download authorization, review workflow, document requests, replacement behavior, download audit events, and tests for unauthorized access and unsafe files. Preserve existing client-visible review behavior.

### Prompt 8: Staff workflow

> Implement the staff workflow for client search, service approval, case creation, assignment, status transitions, tasks, document review, tax returns, service configuration, staff accounts, activity history, reports, and CSV export. Add pagination, query optimization, permission checks, audit events, and focused tests. Preserve existing templates and URL names unless a change is necessary.

### Prompt 9: Notifications

> Add database notifications and email events for registration, account approval, document requests, document review, case assignment, case status changes, and due-date reminders. Make delivery asynchronous only after successful transactions. Do not include passwords or private document contents in emails. Add tests for notification creation and failure handling.

### Prompt 10: Production readiness

> Review the complete KLA Django backend against the production checklist in `BACKEND_DATABASE_BLUEPRINT.md`. Fix configuration, security, backup, file-storage, query, logging, authorization, and test gaps that are within the repository scope. Run checks, migrations, tests, and a deployment smoke test. Report remaining external infrastructure tasks separately.

## 14. Definition of done

The backend and database are ready for the first production release only when all of these points are true:

1. Every database change is represented by a migration.
2. The project passes `manage.py check` and `makemigrations --check`.
3. The complete test suite passes.
4. Client records are isolated by object-level authorization.
5. Staff permissions are enforced for every management action.
6. Case status changes have an immutable history.
7. Sensitive actions create audit events.
8. Documents are private, validated, and access-controlled.
9. Registration and other multi-table workflows are atomic.
10. PostgreSQL configuration is tested.
11. Secrets are environment-based and `DEBUG=False` is supported.
12. Database and media backups have been restored successfully in a test.
13. Reports and downloads are permission-checked and audited.
14. The deployment process is documented and repeatable.
15. Any remaining limitation is written down with an owner and a planned phase.
