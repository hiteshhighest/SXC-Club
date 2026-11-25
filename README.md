# SXC Clubs

A club and campus community platform for St. Xavier's College, Kathmandu. It uses Django REST Framework, PostgreSQL (SQLite fallback for local setup), React, TypeScript, Vite and Tailwind CSS. The interface uses the requested SXC Clubs palette and is responsive from mobile through desktop.

## Project layout

```text
backend/       Django project, REST API, migrations, tests and admin command
frontend/      React + TypeScript + Vite client
docker-compose.yml  Local PostgreSQL service
```

## Local setup

Requirements: Python 3.11+, Node 20.19+ (or 22.12+), npm. PostgreSQL can be supplied locally or started with Docker Compose.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For the quickest local start, leave `DATABASE_URL` unset and Django uses `backend/db.sqlite3`. For PostgreSQL, start `docker compose up -d db` from the repository root, then set `DATABASE_URL=postgresql://sxcclubs:local-dev-password@localhost:5432/sxcclubs` in the backend environment. Set `DJANGO_SECRET_KEY` to a private random value before sharing or deploying the app. Do not put backend secrets in frontend variables.

```powershell
python manage.py migrate
python manage.py create_first_admin
python manage.py runserver
```

The API is at `http://localhost:8000/api/`; Django admin is at `/django-admin/`. Local password reset messages are printed to the runserver terminal. Configure SMTP environment variables and a trusted sender for real email delivery. There is intentionally no public account registration.

### Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. By default the client calls `http://localhost:8000/api`. For another API host, create `frontend/.env.local` with `VITE_API_URL=https://your-api.example/api` and add that origin to backend `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

### Build and test

```powershell
cd frontend
npm run build
cd ..\backend
python manage.py check
python manage.py test clubs
```

## Authentication and access

Students sign in at `/` and administrators sign in at `/admin`. The API enforces the split: student credentials cannot open the administrator session, and administrator credentials cannot use student sign-in. Accounts are provisioned by an administrator; there is no public sign-up page. Django's password validators and password hashing are enabled. API sessions use HttpOnly cookies, `SameSite=Lax`, and CSRF checks on unsafe requests. Production mode enables secure session and CSRF cookies. Login and API request throttles are configured in Django REST Framework.

Administrators are Django staff/superusers. Bootstrap the first administrator using `python manage.py create_first_admin`; the command refuses to create another superuser if one already exists. Password reset uses Django's token generator; set an SMTP backend in production. The reset request response does not reveal whether an email exists.

From the admin dashboard, use **Create club account** to create a student login and its club membership together. The transaction rolls both records back if either save fails. To manage records directly, use Django Admin at `/django-admin/`: create or edit the Django user, then create a `ClubMembership` with the club, role and explicit permission list. The standard Django user table stores a secure password hash; never insert a plain-text password directly into the database.

Club memberships hold a role label and a separate list of permission keys. Role names never imply permissions. Join codes are generated with cryptographically secure randomness; only a SHA-256 digest and final four-character hint are stored. The full code is returned once at creation. Redemption locks the code row inside a transaction and checks expiry, revocation, use limit and existing membership before consuming it.

The backend is the authority for club membership and permissions. The API filters club-scoped queries, checks action permissions, prevents non-admins from granting permissions they do not already hold, and does not let role-label edits change permission keys.

## API guide

All routes are under `/api/`. JSON errors use DRF validation responses. List routes use page-number pagination (20 results per page; response has `count`, `next`, `previous`, `results`). Unsafe requests require the session CSRF token in `X-CSRFToken`; fetch `/api/csrf/` first. File endpoints accept multipart form data.

| Area | Routes | Access |
|---|---|---|
| Session | `POST auth/login/`, `POST auth/admin-login/`, `POST auth/logout/`, `GET auth/student/me/`, `GET auth/admin/me/` | Separate student and staff login; remaining routes require the matching session |
| Password | `POST auth/password-reset/`, `POST auth/password-reset/confirm/` | Public, throttled; reset response is generic |
| Dashboard | `GET dashboard/` | Signed-in user; own clubs only |
| Clubs | `GET clubs/`, `GET clubs/{id}/`, `GET clubs/{id}/dashboard/` | Active club directory; private dashboard requires sign-in |
| Club changes | `POST clubs/`, `PATCH clubs/{id}/`, `DELETE clubs/{id}/` | Admins create, archive, restore, or permanently delete clubs; club permission for other edits. Deletion removes memberships, events, announcements, join codes, and notifications |
| Members | `GET clubs/{id}/members/`, `PATCH clubs/{id}/members/{membership}/role/`, `DELETE clubs/{id}/members/{membership}/remove/` | Membership permissions; supports `search`, `role`, and `page` filters |
| Join codes | `POST join-codes/create/`, `GET join-codes/`, `POST join-codes/{id}/revoke/`, `POST join-codes/redeem/` | Club-specific permission or admin; redemption requires a signed-in account |
| Events | `/clubs/{id}/events/` list/create/retrieve/update/delete; detail actions `publish/`, `unpublish/` | Published events are visible publicly; writes and non-published data require club permissions |
| Announcements | `/clubs/{id}/announcements/` list/create/retrieve/update/delete; detail action `publish/` | Only published announcements appear publicly |
| Notifications | `GET notifications/`, `POST notifications/{id}/read/`, `POST notifications/read_all/` | Own notifications only |
| Permissions | `GET permissions/` | Public permission catalog; grants still require club authorization |
| Administration | `GET admin/stats/`, `GET admin/users/`, `DELETE admin/users/{id}/`, `POST admin/users/create/`, `POST admin/accounts/`, `GET activity/` | Admin only; deleting a student removes memberships and notifications while preserving authored events and announcements |

### Permission keys

Events: `events.view`, `events.create`, `events.edit`, `events.delete`, `events.publish`, `events.unpublish`.

Announcements: `announcements.view`, `announcements.create`, `announcements.edit`, `announcements.delete`, `announcements.publish`, `announcements.unpublish`.

Membership: `members.view`, `members.invite`, `members.remove`, `members.change_role`.

Club administration: `club.edit`, `club.resources`, `join_codes.generate`, `join_codes.revoke`, `executives.permissions`.

The join-code creation payload includes `club`, `role_name`, `permissions`, optional `max_uses`, and optional ISO-8601 `expires_at`. The response includes the full `code` exactly once. Permission keys are validated against this documented set.

## Data and safety notes

All datetimes are timezone-aware and use `Asia/Kathmandu` for display and server defaults. Uploaded files are limited to 5 MB, images are checked by Django, and announcement attachments are restricted to common document/image extensions. Media storage is local by default and should be moved to protected storage before deployment. In production, use HTTPS, set a strong secret key and configure allowed hosts, CSRF origins, SMTP and PostgreSQL backups. Add the college-provided logo as `frontend/public/sxc-logo.png`; the interface will pick it up automatically. No unofficial logo is bundled.
