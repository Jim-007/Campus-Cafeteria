# Campus Cafeteria Online Food Ordering System

Django project for CSE 451 Software Engineering. Students pre-order food, pick a time slot, pay, and track the order. Staff prepare orders from a live queue. The owner manages the menu and reads sales reports.

## Quick start (about 3 minutes)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000 and sign in with a demo account (password for all: `Demo@12345`):

| Account | Role | Lands on |
|---|---|---|
| `demo_student` | Student | Menu, cart, my orders |
| `demo_staff` | Cafeteria Staff | Live order queue |
| `demo_owner` | Cafeteria Owner (Admin) | Sales report, manage menu, order queue |

To make your own administrator: `python manage.py createsuperuser` (it gets the Administrator role, which can do everything the owner can, plus the Django admin at `/admin/`).

If you ran an earlier version of this project, delete `db.sqlite3` first, then run `migrate` again.

## Roles and registration

On the registration page the user chooses **Student**, **Cafeteria Staff** or **Cafeteria Owner (Admin)**.
Staff and owner accounts need the cafeteria access code, so a student cannot make themselves an owner.
The code is `CAFE2026`. Change `STAFF_ACCESS_CODE` in `cafeteria/settings.py` before the demo.
After sign in, each role is sent to its own page and sees only its own menu links.

## Requirements and where they live

| Req | What it does | Code |
|---|---|---|
| FR1 | Register with a role | `accounts/forms.py`, `accounts/views.py` |
| FR2 | Login, logout, role-based access | `accounts/decorators.py`, `accounts/views.py` |
| FR3 | Menu with search and filters | `menu/views.py` |
| FR4 | Cart and place order | `orders/cart.py`, `orders/views.py`, `orders/services.py` |
| FR5 | Pickup time slots, slot limits | `orders/slots.py` |
| FR6 | Order history and reorder | `orders/views.py` |
| FR7 | Payment (counter or simulated online), refunds | `orders/services.py` |
| FR8 | Owner adds, edits, hides, deletes items | `menu/views.py`, `menu/forms.py` |
| FR9 | Staff queue and status control | `kitchen/views.py` |
| FR10 | Staff alerts for new orders | `kitchen/notifications.py`, `static/js/refresh.js` |
| FR11 | Live order tracking and alerts for students | `orders/views.py`, `templates/orders/_status.html` |
| FR12 | Sales report and CSV export | `menu/reports.py` |

## Architecture

Django MVT (Model-View-Template, Django's form of MVC) plus a **service layer**:
`models.py` holds the data, `views.py` handles requests, `templates/` is the screen, and
`orders/services.py` holds the business rules (stock checks, slot limits, status order, refunds) so views stay thin.

## Order and payment rules

- Status order: Placed, Accepted, Preparing, Ready for Pickup, Collected. Any open order can be Cancelled with a reason.
- A student can cancel only while the order is Placed. Staff can cancel until it is collected.
- Cancelling returns the stock and refunds a paid payment.
- Online payment is simulated: the pay page has **Pay now** and **Simulate failed payment**. A failure cancels the order. Online orders show to staff only after they are paid.
- Counter payments become Paid when staff press **Handed over**.
- Slots are created automatically for the next 4 hours in 30-minute steps (`SLOT_*` settings), each with a maximum number of orders.
- `python manage.py cancel_no_shows` cancels orders not collected 10 minutes after their slot started.

## Tests

```
python manage.py test
```
63 tests cover normal cases, boundaries (full slot, exact stock), invalid input, access control and failures.

## Team rules

1. Never commit to `main`. Branch names: `feature/fr<number>-<name>`.
2. Commit messages start with the requirement, for example `FR4: add cart view`.
3. Open a pull request and get one review before merging.
4. Every function has a docstring and every feature has a test.
