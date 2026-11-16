"""API test cases for Orbit Eats. Start the API first (python app.py), then:
    python test_api.py
Requires the sample data from orbit_eats_tests.sql (employees, products, ingredients).
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = os.getenv('API_URL', 'http://127.0.0.1:8000')
TOKEN = os.getenv('API_TOKEN', 'token-secreto-123')
AUTH = {'Authorization': f'Bearer {TOKEN}'}
results = []


def check(test_id, description, condition):
    results.append(condition)
    print(f"{'PASS' if condition else 'FAIL'}  {test_id}  {description}")


# Unique email so the script can be run more than once
email = f'test{int(time.time())}@mail.com'
customer = {'first_name': 'Carla', 'last_name': 'Mena', 'address': 'Calle Larga 5',
            'phone': '0987654321', 'email': email}

# ---------- NFR-02 / TC-10: authentication ----------
r1 = requests.get(f'{BASE}/customers')
r2 = requests.get(f'{BASE}/customers', headers={'Authorization': 'Bearer wrong'})
r3 = requests.get(f'{BASE}/customers', headers=AUTH)
check('TC-10', 'no token -> 401, wrong token -> 401, valid token -> 200',
      r1.status_code == 401 and r2.status_code == 401 and r3.status_code == 200)

# ---------- Customers CRUD (FR-01) ----------
r = requests.post(f'{BASE}/customers', json=customer, headers=AUTH)
check('API-01', 'POST /customers creates a customer (201)', r.status_code == 201)
cid = r.json().get('customer_id')

r = requests.post(f'{BASE}/customers', json=customer, headers=AUTH)
check('API-02', 'POST /customers with a repeated email -> 409', r.status_code == 409)

r = requests.post(f'{BASE}/customers', json={'first_name': 'Sin datos'}, headers=AUTH)
check('API-03', 'POST /customers with missing fields -> 400', r.status_code == 400)

r = requests.get(f'{BASE}/customers/{cid}', headers=AUTH)
check('API-04', 'GET /customers/<id> returns the customer', r.status_code == 200 and r.json()['email'] == email)

r = requests.put(f'{BASE}/customers/{cid}', json={'phone': '0999999999'}, headers=AUTH)
check('API-05', 'PUT /customers/<id> updates only the phone', r.status_code == 200 and r.json()['phone'] == '0999999999')

# ---------- Products (CHECK constraint) ----------
r = requests.post(f'{BASE}/products', json={'name': 'Bad', 'base_price': -1, 'category': 'x'}, headers=AUTH)
check('API-06', 'POST /products with a negative price -> 400', r.status_code == 400)

# ---------- Orders (FR-02, FR-06) ----------
order = {'customer_id': cid, 'delivery_address': 'Calle Larga 5',
         'items': [{'product_id': 2, 'quantity': 3}]}
r = requests.post(f'{BASE}/orders', json=order, headers=AUTH)
body = r.json()
price = float(requests.get(f'{BASE}/products/2', headers=AUTH).json()['base_price'])
check('API-07', 'POST /orders saves the lines and total = quantity x price',
      r.status_code == 201 and len(body['details']) == 1 and float(body['total']) == round(3 * price, 2))
oid = body['order_id']

r = requests.patch(f'{BASE}/orders/{oid}', json={'status': 'lost'}, headers=AUTH)
check('API-08', 'PATCH /orders/<id> with an invalid status -> 400', r.status_code == 400)

r = requests.patch(f'{BASE}/orders/{oid}', json={'status': 'preparing', 'employee_id': 1}, headers=AUTH)
check('API-09', 'PATCH /orders/<id> changes status and assigns employee',
      r.status_code == 200 and r.json()['status'] == 'preparing')

r = requests.post(f'{BASE}/orders', json={**order, 'customer_id': 999999}, headers=AUTH)
check('API-10', 'POST /orders for a customer that does not exist -> 409', r.status_code == 409)

r = requests.delete(f'{BASE}/orders/{oid}', headers=AUTH)
check('API-11', 'DELETE /orders/<id> marks the order as cancelled', r.json()['status'] == 'cancelled')

# ---------- Recipes and stock (FR-03, FR-04) ----------
r = requests.get(f'{BASE}/products/1/recipe', headers=AUTH)
check('API-12', 'GET /products/1/recipe lists its ingredients', r.status_code == 200 and len(r.json()) >= 1)

r = requests.get(f'{BASE}/ingredients/low-stock', headers=AUTH)
check('API-13', 'GET /ingredients/low-stock only returns stock < minimum',
      all(float(i['current_stock']) < float(i['minimum_stock']) for i in r.json()))

# ---------- NFR-01 / TC-09: 20 orders at the same time ----------
def send_order(_):
    start = time.perf_counter()
    resp = requests.post(f'{BASE}/orders', json=order, headers=AUTH)
    return resp.status_code, time.perf_counter() - start

with ThreadPoolExecutor(max_workers=20) as pool:
    answers = list(pool.map(send_order, range(20)))
slowest = max(seconds for _, seconds in answers)
check('TC-09', f'20 simultaneous orders -> all 201, slowest {slowest:.2f} s (< 2 s)',
      all(code == 201 for code, _ in answers) and slowest < 2)

# ---------- Clean up the test customer's data is not needed: orders keep history ----------
print(f'\n{sum(results)}/{len(results)} tests passed')
