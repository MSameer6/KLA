# Khan Law Associates portal

## Run locally

Open PowerShell in this folder and run:

```powershell
py -3.14 -m pip install -r requirements.txt
py -3.14 manage.py migrate
py -3.14 manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

## First accounts

- Register staff at `http://127.0.0.1:8000/staff/register/`.
- Register a client at `http://127.0.0.1:8000/client/register/`.
- In **Staff → Clients**, create the client record using the exact same email as their client account. Documents and tax-return progress will then appear in that client's portal.

## Included features

- Staff client CRUD, document upload/download/delete, tax-return creation/editing, reporting and CSV export.
- Client-specific document downloads and tax-return status display.
- SQLite database configuration for a no-setup local start.
