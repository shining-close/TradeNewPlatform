# Cross-Border Trade Supply & Demand Service Platform

A multi-role trade information and supply/demand matching platform built with **Django + MySQL**.
Enterprise users publish supply and purchase orders; administrators audit users and maintain
industry categories, logistics routes and news; users can bookmark orders and receive in-site
notifications.

> Rebuilt from an earlier **Spring + Servlet** implementation into Django — the same business
> domain implemented on two generations of stack.
>
> Coursework group project. All application code was implemented by the author.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Permission Model](#permission-model)
- [Data Models](#data-models)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Test Accounts](#test-accounts)
- [Running Tests](#running-tests)
- [Known Limitations](#known-limitations)

---

## Features

### User side (`trade` app)

| Module | Description |
|---|---|
| Home | Latest 3 supply orders, 3 purchase orders, 3 news items |
| Auth | Register, login, logout, remember-me (session expiry 7 days / 30 days) |
| Orders | Browse, search by keyword, filter by industry category, paginate; publish, edit, delete (audited enterprise users only) |
| Order detail | Full order info with associated industry and logistics |
| News | Browse by category (`policy` / `market` / `logistics`), search, detail view |
| Logistics | International logistics list with keyword search + type filter (air / sea / land) |
| Bookmarks | Bookmark/unbookmark orders and news via AJAX; deduplicated at database level |
| Notifications | In-site notification centre; auto-marks items read on view; batch delete |
| Profile | Update role, phone, company, position, nationality, avatar |
| i18n | EN / CN language switching by session |

### Admin side (`administrator` app)

| Module | Description |
|---|---|
| Dashboard | Aggregate statistics: users, enterprise users, audited enterprises, orders (supply / demand / completed), logistics, news |
| User management | Filter by role / keyword / unaudited; batch and single delete; superuser and self-deletion protection |
| User audit | Approve or reject enterprise-role applications |
| Order management | CRUD, order status transitions |
| Logistics management | CRUD with image upload and price validation |
| News management | CRUD |
| Company management | CRUD; company detail page |
| Industry category management | CRUD; 11 default categories seeded via `Industry.init_default_categories()` |

---

## Architecture

### Two independent Django apps

```
trade/          → user-facing application
administrator/  → admin backend (deliberately independent)
```

**Decision: the admin backend does not use Django's built-in Admin.** Django Admin is kept only
for low-level data maintenance under `/django-admin/`. The business admin backend is a separate app
with:

- its own URL namespace (`administrator:`)
- **its own permission decorator** (`admin_auth_required`, built on `user_passes_test`)
- its own template tree

**Rationale:** the admin and user sides have substantially different permission models, route
namespaces and template structures. Keeping them in one app scatters permission checks across view
functions; splitting them isolates permissions, routing and templates at all three layers.

### Route separation

| Prefix | App | Purpose |
|---|---|---|
| `/` | `trade` | User-facing site |
| `/admin/` | `administrator` | Business admin backend |
| `/django-admin/` | Django Admin | Native admin (data maintenance) |

---

## Permission Model

### Three roles

```python
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("visitor",    "Visitor"),
        ("enterprise", "Enterprise User"),
        ("admin",      "Administrator"),
    )
    role = models.CharField(..., default="visitor")
    is_audited = models.BooleanField(default=False)
```

| Role | Capability |
|---|---|
| **Visitor** | Browse order/news/logistics lists; operations require login |
| **Enterprise User** | Publish, edit and delete own orders; bookmark orders and news — **only after audit approval** |
| **Administrator** | Full admin backend access; manage users, orders, logistics, news, companies, industries; audit enterprise roles |

### Enterprise audit state machine

Business permissions are gated on `is_audited`, and the audit state **resets automatically when a
user changes role**:

```python
# profile view — changing role invalidates the previous audit
if user.role != role:
    user.is_audited = False      # must be re-audited
user.role = role
```

```python
# order create / edit / delete entry point
if not (request.user.is_audited and request.user.role in ("enterprise", "admin")):
    messages.error(request, "Only audited enterprise users/administrators can publish orders.")
    return redirect(...)
```

This forms a closed loop: **submit role → admin audits → business permissions granted**. A user
cannot self-promote to enterprise privileges without administrator approval.

---

## Data Models

Eight models in total.

| Model | Purpose | Notable design |
|---|---|---|
| **CustomUser** | Extends `AbstractUser` with `role`, `is_audited`, `phone`, `company`, `position`, `nationality`, `avatar` | `groups` / `user_permissions` re-declared with `related_name` to resolve reverse-accessor conflicts; `db_table = "trade_user"` |
| **Company** | Enterprise profile: name, address, phone, contact person, intro (500 chars), image | FK to `CustomUser` with `CASCADE`, nullable for standalone company records |
| **Industry** | Trade industry categories (11 defaults seeded) | `unique=True` on name; classmethod `init_default_categories()` |
| **Transport** | International logistics: name, type (air/sea/land), price, lead time, company, description, image | `price` uses `DecimalField` + `MinValueValidator(0)` with a custom `min_value` error message |
| **News** | Trade news with category (policy/market/logistics), cover image | FK to `CustomUser` as publisher, `CASCADE` |
| **Order** | Supply / purchase order: `flag` (1=supply, 2=purchase), `status`, industry FK, transport FK, `end_time`, contact phone, nationality, image or image URL | FKs use `SET_NULL` for category/logistics so deleting them does not destroy orders |
| **Collect** | Bookmark linking a user to an order **or** a news item | `unique_together` on `(user, order)` and `(user, news)` — **idempotent at database level** |
| **Notification** | In-site notification with `is_read` flag | `order` FK uses `SET_NULL` so notification history survives order deletion |

### Deletion semantics

The models deliberately distinguish `CASCADE` from `SET_NULL`:

- `CASCADE` — user-owned content (a user's orders, news, bookmarks) is removed with the user
- `SET_NULL` — **reference** data (industry category, logistics route, related order) is cleared but
  the record survives

### Notification flow

Publishing or editing an order sends notifications to:

1. the **publisher** ("your order has been published")
2. **every administrator** (`CustomUser.objects.filter(role="admin")`) — "user X published a new order, please review"

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0.3, Python 3.10+ |
| Database | MySQL 8.0+ (`utf8mb4`), via `mysqlclient` |
| Frontend | Django templates, HTML, CSS, JavaScript |
| Templating | 33 templates (shared `templates/` + per-app template trees) |
| i18n | `gettext_lazy` + `LocaleMiddleware`, EN / CN |
| Media | Pillow — avatar, company, news, order and logistics image uploads |
| Auth | Custom user model (`AUTH_USER_MODEL = 'trade.CustomUser'`) |

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/shining-close/TradeNewPlatform.git
cd TradeNewPlatform
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv

# Windows (PowerShell)
venv\Scripts\activate

# Windows (CMD)
venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the database

```sql
CREATE DATABASE trade_platform DEFAULT CHARSET utf8mb4;
```

### 5. Configure environment variables

The project reads database settings from the environment — **do not hardcode credentials in
`settings.py`**. See [Environment Variables](#environment-variables).

Create a `.env` file in the project root (or export the variables in your shell):

```bash
DB_NAME=trade_platform
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

> `DB_PASSWORD` defaults to an empty string, so a passwordless local MySQL works without a `.env`.

### 6. Apply migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create a super administrator

```bash
python manage.py createsuperuser
```

The superuser is used to bootstrap the platform: log in, then create a regular user and promote it
to `admin` role through the user management page. Subsequent administrators can log in to the admin
backend directly.

### 8. Run the development server

```bash
python manage.py runserver
```

- User site: <http://127.0.0.1:8000/>
- Admin backend: <http://127.0.0.1:8000/admin/>
- Django Admin: <http://127.0.0.1:8000/django-admin/>

---

## Environment Variables

`TradeNewPlatForm/settings.py` reads the following, each with a default:

| Variable | Default | Purpose |
|---|---|---|
| `DB_NAME` | `trade_platform` | Database name |
| `DB_USER` | `root` | Database user |
| `DB_PASSWORD` | *(empty)* | Database password |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `3306` | Database port |

> ⚠️ `SECRET_KEY` and `DEBUG` are currently hardcoded in `settings.py` for development. Before any
> production deployment, move both to environment variables and set `DEBUG = False` with an
> explicit `ALLOWED_HOSTS`.

---

## Project Structure

```
TradeNewPlatform/
├── manage.py
├── requirements.txt
├── .gitignore
├── README.md
│
├── TradeNewPlatForm/            # Django project configuration
│   ├── settings.py
│   ├── urls.py                  # Root URL conf (/, /admin/, /django-admin/)
│   ├── asgi.py
│   └── wsgi.py
│
├── trade/                       # User-facing application
│   ├── models.py                # 8 data models
│   ├── views.py                 # Auth, orders, news, logistics, bookmarks, notifications
│   ├── urls.py                  # Namespace: trade
│   ├── admin.py
│   ├── tests.py                 # 17 unit tests / 6 test classes
│   └── migrations/              # 9 migration files
│
├── administrator/               # Admin backend application (independent)
│   ├── models.py
│   ├── views.py                 # Dashboard + 6 management modules
│   ├── forms.py                 # TransportAddForm with price/image validation
│   ├── urls.py                  # Namespace: administrator
│   ├── tests.py                 # 10 unit tests / 2 test classes
│   └── templates/administrator/ # 14 admin templates
│
├── templates/                   # Shared user-facing templates (33 total)
│   ├── base.html
│   ├── index.html
│   ├── accounts/                # login, register
│   ├── order/                   # list, create, edit, detail
│   ├── news/                    # list, detail
│   ├── transport/               # list, detail
│   ├── my_orders.html
│   ├── my_collections.html
│   ├── notification_center.html
│   ├── profile.html
│   └── about.html
│
├── static/                      # CSS, JavaScript, banner images
└── media/                       # User-uploaded files (avatars, company/news/order/transport images)
```

---

## Test Accounts

For functional verification (create these accounts locally after migrating):

| Role | Behaviour |
|---|---|
| Administrator | Manages all user, order and logistics data |
| Enterprise User | Publishes, edits, views and bookmarks their own orders (requires `is_audited = True`) |
| Visitor | Browses order lists; all operations require login |

---

## Running Tests

The project contains **27 unit test cases** covering core models, permissions and business logic.

```bash
python manage.py test
```

Or by app:

```bash
python manage.py test trade
python manage.py test administrator
```

A successful run prints `OK`.

Coverage includes:

- **Role permissions** — an enterprise user accessing the admin dashboard must receive a `302`
  redirect; an anonymous visitor likewise
- **Custom user model** — role choices, default `is_audited = False`
- **Model constraints** — bookmark uniqueness, price non-negativity
- **Business logic** — bookmark toggle idempotency

---

## Known Limitations

Documented honestly for anyone reviewing or extending the project:

1. **Open redirect in language switching** — `switch_language` validates the `lang` parameter
   against a whitelist but does **not** validate the `next` parameter. A crafted
   `?lang=en&next=https://evil.com` can be used as a redirect. *Fix: validate that `next` is a
   same-site relative path.*
2. **Incorrect pagination exception handling** — `int(page)` raises `ValueError`, but the code
   catches `PageNotAnInteger` and `EmptyPage`, so neither branch ever executes. A non-numeric
   `?page=abc` therefore returns HTTP 500. *Fix: catch `ValueError`, or use
   `paginator.get_page()`.*
3. **`SECRET_KEY` and `DEBUG` hardcoded** in `settings.py`.
4. **No `locale/` directory committed** — `LANGUAGES` and `LOCALE_PATHS` are configured and the
   language-switch view works, but the compiled `.mo` files are absent, so switching to Chinese
   does not yet produce translated strings.
5. **`media/` contains test uploads** that were committed during development.
6. **Large banner images** (~6.6 MB total in `static/images/`) — these could be compressed
   substantially without visible quality loss.

---

## Acknowledgements

Rebuilt from an undergraduate Spring + Servlet implementation of the same business domain.

Notes
Ensure that the MySQL service is installed and running locally, and that the database configuration matches settings.py.
To use the image upload function, ensure the media/ directory has write permissions.
Database migration commands must be executed on the first run; otherwise, a "table does not exist" error will occur.
