# Backend Project — Allocation & Labels Challenge

The core business is the fulfillment process of our customers' orders.
For this challenge, we want to evaluate your ability to model and implement a realistic logistics workflow in Python, involving inventory allocation by units of measure (UoM).

## 🧭 Objectives

**Time expectation**: We really care about your time, and we expect you to spend no more than 4 hrs in total to implementing your solution. You can split that time into 2 consecutive days if that is better for you. If you run out of time, please stop what you are doing and document what you would do if you had been given more time.

Your goals in this exercise are divided into 2 main parts:

### Goal 1 — Orders Creation

Implement a `POST /orders/create` endpoint that:

- Creates a new order and allocates its line items based on available inventory.
- Fails with an error (400 or 422) if there are not enough units to fully allocate the requested quantities.

**Input example**

```
{
  "customer_id": 1,
  "line_items": [
    { "sku": "tshirt-blue", "quantity": 2500 }
  ]
}
```

**Expected behavior**

The endpoint must:

- Perform reasonable validations
- Create the order.
- Allocate inventory following Goal 2 rules.
- Deduct inventory accordingly.
- Return a JSON response with the created order_id.

### Goal 2 — Allocation Rules

The allocation algorithm must:

- Use the largest available Unit of Measure (UoM) first.
- Priority: pallet → case → each (or NULL meaning eaches)
- Always prefer full UoM units (whole pallets/cases).
- Convert UoMs using the mapping from the uom_products table.
- Stop and return an error if inventory cannot satisfy the full requested quantity (no partial allocations).

**Example**

Given:

```
product_inventory:

customer_id	sku	uom	quantity	location_identifier
1	tshirt-blue	NULL	1000	loc-1
1	tshirt-blue	pallet	10	loc-2
```

```
uom_products:

customer_id	sku	uom	ea_qty
1	tshirt-blue	pallet	1200
```

Order payload:
```
{"customer_id": 1, "line_items": [{"sku": "tshirt-blue", "quantity": 2500}]}
```

Expected allocations:

```
order_id	customer_id	sku	location_identifier	quantity	uom
1	1	tshirt-blue	loc-2	2400	pallet
1	1	tshirt-blue	loc-1	100	NULL
```

## 🧩 Starting Point

The codebase is organized in a basic **layered / DDD structure**:

```
app/
├── api/
│   └── app.py                 # Flask routes (HTTP interface layer)
├── domain/
│   ├── allocation.py          # Allocation algorithm (core business logic)
│   └── exceptions.py          # Domain exceptions (OutOfStock)
├── infrastructure/
│   ├── db.py                  # Engine, session factory
│   └── models.py              # SQLAlchemy ORM models
├── services/
│   └── order_service.py       # Order creation use case (orchestration)
└── prestart.py                # One-time DB init for container startup
```

- **`domain/`** — Pure business logic and domain exceptions. The allocation algorithm lives here but is **not implemented** yet.
- **`services/`** — Application-level orchestration. `order_service.py` ties together order creation and allocation.
- **`infrastructure/`** — ORM models and database access.
- **`api/`** — Flask HTTP layer. Routes live here.

The endpoint in `app/api/app.py` is wired up but unfinished — it has intentional issues for you to find and fix.

Your job is to:

1. **Implement the allocation algorithm** in `domain/allocation.py` → `allocate_line_item()` following Goal 2 rules.
2. **Fix the endpoint** so that valid requests succeed and invalid or unfulfillable ones fail cleanly, without leaving the database in an inconsistent state.

A comprehensive test suite is provided. Run the tests to see which ones pass and which ones fail. Use the failing tests as a guide to drive your implementation.

## ✅ Definition of Done

All provided tests pass, plus:

- [ ] `POST /orders/create` creates an order and returns its `order_id` on success.
- [ ] Allocations are persisted and correctly linked to the order.
- [ ] Inventory quantities are deducted after allocation.
- [ ] Orders that cannot be fully allocated are rejected with an appropriate error response.
- [ ] Invalid payloads are rejected with an appropriate error response.
- [ ] No partial allocations — all-or-nothing per order.

Choosing the right HTTP status codes and response shapes is part of the exercise.

### Bonus

1. Write additional tests covering edge cases not already in the suite.
2. Improve the design where you think it helps — and be ready to explain why each change earns its keep.

## 🧩 Tech Stack

- Flask (API)
- SQLAlchemy (ORM)
- MySQL (DB)
- Pytest (tests)
- Docker & docker-compose (environment)

## 🧱 Database Tables

```
orders	Stores order headers
order_line_items	Line items with SKU and quantity (in eaches)
product_inventory	Inventory by SKU, UoM, and location
uom_products	Defines conversion ratios from UoMs to eaches
allocations	Records how inventory was allocated per order line item
```

## ⚙️ How to Run

**build and start containers**
```
docker compose build
docker compose up -d
```

## 🧪 Testing

Create a local environment with:

```sh
python3.11 -m venv .venv && source .venv/bin/activate
```

Run the tests locally with pytest:

```sh
pip install -r requirements.txt
PYTHONPATH=. pytest -v
```

Some tests pass and some fail out of the box. Your goal is to make the whole suite pass — use the failing tests to understand the expected behavior, and add your own where the suite is thin.

Notes:
- Tests use an in-memory SQLite database via fixtures in `tests/conftest.py` to avoid requiring MySQL.
- The tests add the `app/` folder to `sys.path` so modules like `db`, `models`, and `app` can be imported directly as they are inside the container.
- Seed helpers (`seed_inventory`, `seed_uom`) are available in `conftest.py` — use them in any additional tests you write.


## 🤖 AI guideline

We welcome and encourage the use of modern development tools, including AI. As part of your submission, please include a short paragraph in your PR description detailing your preferred AI setup for tackling this challenge and how you utilized it. We are interested in how you leverage these tools to enhance your workflow. Please note that during our follow-up call, we may ask you to share your screen and walk us through a small live implementation example to discuss your approach.


## 💬 Communication & Clarifications

You have a Slack channel with us to clarify any blocker.
And you also have been introduced to the business, which will guide you to make your owns design decisions. Please document those.
This spec intentionally omits some business details.
We'll evaluate your both your judgment and communication as part of the review.


## ✅ Submission

Please submit your work via a Pull Request including:
- Your implementation and tests.
- Use the PR description to list and briefly explain your solution, the assumptions you made, and what you would improve.

### 📞 After You Submit

Let us know on the Slack channel, so we can coordinate the next steps.

Good luck, and have fun! 🚀
