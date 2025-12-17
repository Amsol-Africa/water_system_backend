# Frontend-Backend Integration Guide

## 🔗 Complete Integration Steps

### Overview
This guide will connect your React frontend (port 5173) to your Django backend (port 8000).

---

## Step 1: Backend Setup (First!)

### 1.1 Start PostgreSQL & Redis
```powershell
# Make sure PostgreSQL is running
# Make sure Redis is running
```

### 1.2 Setup Backend
```powershell
cd backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run migrations (if not done)
python manage.py makemigrations
python manage.py migrate

# Create superuser (if not done)
python manage.py createsuperuser
# Email: admin@amsol.com
# Password: Admin123!

# Create a test client
python manage.py shell
```

### 1.3 Create Test Data in Django Shell
```python
from clients.models import Client
from accounts.models import User

# Create a test client
client = Client.objects.create(
    name='Test Water Company',
    paybill_number='123456',
    stronpower_company_name='stron',
    stronpower_username='0000',
    stronpower_password='stron888',
    is_active=True
)

# Create a client admin user
user = User.objects.create_user(
    email='clientadmin@test.com',
    password='Admin123!',
    first_name='Client',
    last_name='Admin',
    role='client_admin',
    client=client
)

# Create an operator user
operator = User.objects.create_user(
    email='operator@test.com',
    password='Admin123!',
    first_name='John',
    last_name='Operator',
    role='operator',
    client=client
)

print("Test data created successfully!")
exit()
```

### 1.4 Start Backend Server
```powershell
python manage.py runserver
```

**Backend should be running at:** `http://localhost:8000`

Test it: Open `http://localhost:8000/admin/` - you should see Django admin

---

## Step 2: Update Frontend Configuration

### 2.1 Update Frontend .env File
```powershell
cd frontend
```

Create/update `.env`:
```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=Amsol Water Vending
VITE_ENV=development
```

### 2.2 Update Frontend API Service

The frontend is already configured! But let's verify the key settings:

**File: `frontend/src/services/api.js`**

The API client should point to backend:
```javascript
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  // ... rest of config
})
```

### 2.3 Disable Mock API

**File: `frontend/src/services/auth.js`** (and other service files)

Change:
```javascript
const USE_MOCK = import.meta.env.MODE === 'development'
```

To:
```javascript
const USE_MOCK = false  // Force use of real API
```

Do this for ALL service files:
- `frontend/src/services/auth.js`
- `frontend/src/services/meters.js`
- `frontend/src/services/customers.js`
- `frontend/src/services/tokens.js`

---

## Step 3: Start Frontend

```powershell
cd frontend

# Install dependencies (if not done)
npm install

# Start dev server
npm run dev
```

**Frontend should be running at:** `http://localhost:5173`

---

## Step 4: Test Integration

### 4.1 Test Login
1. Open `http://localhost:5173`
2. You should see the login page
3. Try logging in with:
   - Email: `admin@amsol.com`
   - Password: `Admin123!`

**Expected Result:** You should be redirected to the dashboard

### 4.2 Check Browser Console
Press F12 to open DevTools and check:
- **Console tab**: No errors
- **Network tab**: API calls to `http://localhost:8000/api/`

### 4.3 Test API Calls

After successful login, try:
1. Navigate to "Meters" - should fetch from backend
2. Navigate to "Customers" - should fetch from backend
3. Navigate to "Tokens" - should fetch from backend

---

## Step 5: Troubleshooting Common Issues

### Issue 1: CORS Error
```
Access to XMLHttpRequest at 'http://localhost:8000/api/auth/login/' 
from origin 'http://localhost:5173' has been blocked by CORS policy
```

**Solution:**
Check `backend/amsol/settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173'
]
CORS_ALLOW_CREDENTIALS = True
```

Restart backend server after changes.

### Issue 2: 401 Unauthorized
```
{"detail": "Authentication credentials were not provided."}
```

**Solution:**
- Check if token is being sent in headers
- Check browser DevTools → Application → Local Storage
- Look for `access_token` and `refresh_token`
- Try logging out and logging in again

### Issue 3: 404 Not Found
```
GET http://localhost:8000/api/meters/ 404
```

**Solution:**
- Verify backend is running
- Check URL in browser: `http://localhost:8000/api/meters/`
- Should return JSON (might need authentication)

### Issue 4: Network Error
```
Network Error / ERR_CONNECTION_REFUSED
```

**Solution:**
- Backend server is not running
- Start backend: `python manage.py runserver`
- Check backend terminal for errors

### Issue 5: Empty Data
You login successfully but see no data.

**Solution:**
Create test data:
```powershell
python manage.py shell
```

```python
from meters.models import Meter
from customers.models import Customer
from clients.models import Client

client = Client.objects.first()

# Create test meters
Meter.objects.create(
    meter_id='58100000001',
    client=client,
    meter_type='Water Meter',
    location='Westlands',
    status='active'
)

Meter.objects.create(
    meter_id='58100000002',
    client=client,
    meter_type='Water Meter',
    location='CBD',
    status='active'
)

# Create test customers
Customer.objects.create(
    client=client,
    customer_id='CUST-001',
    name='John Doe',
    phone='+254712345678',
    email='john@example.com'
)

Customer.objects.create(
    client=client,
    customer_id='CUST-002',
    name='Jane Smith',
    phone='+254798765432',
    email='jane@example.com'
)

print("Test data created!")
exit()
```

---

## Step 6: Verify Integration Checklist

### Backend Checks
- [ ] PostgreSQL running
- [ ] Redis running (optional for now)
- [ ] Backend server running on port 8000
- [ ] Can access Django admin: `http://localhost:8000/admin/`
- [ ] Superuser created
- [ ] Test client created
- [ ] CORS configured correctly

### Frontend Checks
- [ ] Frontend running on port 5173
- [ ] `.env` file has `VITE_API_URL=http://localhost:8000/api`
- [ ] Mock API disabled in service files
- [ ] Can access login page
- [ ] No console errors (F12)

### Integration Checks
- [ ] Can login with valid credentials
- [ ] Token stored in localStorage
- [ ] Dashboard loads after login
- [ ] Can navigate to Meters page
- [ ] Can navigate to Customers page
- [ ] API calls visible in Network tab
- [ ] No CORS errors

---

## Step 7: Create More Test Data

### Using Django Admin
1. Go to `http://localhost:8000/admin/`
2. Login with superuser credentials
3. Add more:
   - Clients
   - Users
   - Meters
   - Customers

### Using Django Shell
```python
python manage.py shell

from meters.models import Meter, MeterAssignment
from customers.models import Customer
from clients.models import Client

client = Client.objects.first()

# Create 10 test meters
for i in range(1, 11):
    Meter.objects.create(
        meter_id=f'5810000000{i}',
        client=client,
        meter_type='Water Meter',
        location=f'Location {i}',
        status='active'
    )

# Create 10 test customers
for i in range(1, 11):
    Customer.objects.create(
        client=client,
        customer_id=f'CUST-{str(i).zfill(3)}',
        name=f'Customer {i}',
        phone=f'+25471234567{i}',
        email=f'customer{i}@example.com'
    )

print("Test data created!")
```

---

## Step 8: Test Full Workflow

### 8.1 Create a Meter
1. Login to frontend
2. Go to "Meters"
3. Click "Add Meter"
4. Fill form:
   - Meter ID: `TEST-METER-001`
   - Type: `Water Meter`
   - Location: `Test Location`
5. Click "Create"

**Check:**
- Meter appears in list
- Check backend Django admin to verify

### 8.2 Create a Customer
1. Go to "Customers"
2. Click "Add Customer"
3. Fill form:
   - Customer ID: `TEST-CUST-001`
   - Name: `Test Customer`
   - Phone: `+254712345678`
4. Click "Create"

**Check:**
- Customer appears in list
- Check Django admin

### 8.3 Issue a Token (Mock Stronpower)
1. Go to "Tokens"
2. Click "Issue Token"
3. Select meter and customer
4. Enter amount: `1000`
5. Click "Issue"

**Note:** This will call the real Stronpower API. If Stronpower is not available, you'll get an error. We'll add mock/test mode next.

---

## Step 9: Optional - Add Test Mode

If Stronpower API is not available, add test mode:

**File: `backend/integrations/stronpower_service.py`**

Add at the top:
```python
from django.conf import settings

TEST_MODE = settings.DEBUG and not settings.STRONPOWER_BASE_URL
```

In each method, add:
```python
def vending_meter(self, ...):
    if TEST_MODE:
        # Return mock token
        import random
        import string
        token = ''.join(random.choices(string.digits, k=20))
        return True, token, ""
    
    # Real API call
    # ... existing code
```

---

## Step 10: Monitoring & Debugging

### Backend Logs
Watch backend terminal for:
- API requests
- Errors
- Database queries

### Frontend Logs
Browser console (F12) shows:
- API calls
- Errors
- State changes

### Network Monitoring
Browser DevTools → Network tab:
- See all API calls
- Check request/response
- Verify status codes

### Database Monitoring
Django admin or database client:
- Verify data is saved
- Check relationships
- Monitor queries

---

## 🎉 Success Indicators

You'll know integration is successful when:

✅ Frontend loads without errors  
✅ Can login and see dashboard  
✅ Meters list loads from backend  
✅ Customers list loads from backend  
✅ Can create new meter (saves to DB)  
✅ Can create new customer (saves to DB)  
✅ Token issuance calls Stronpower  
✅ No CORS errors  
✅ No authentication errors  
✅ Data persists across page refreshes  

---

## 📝 Quick Reference

### Start Both Servers

**Terminal 1 - Backend:**
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

### Test URLs
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api/`
- Django Admin: `http://localhost:8000/admin/`
- API Docs: `http://localhost:8000/api/docs/`

### Test Credentials
```
System Admin:
Email: admin@amsol.com
Password: Admin123!

Client Admin:
Email: clientadmin@test.com
Password: Admin123!

Operator:
Email: operator@test.com
Password: Admin123!
```

---

## 🔧 Advanced Configuration

### Production Setup

**Backend `.env`:**
```env
DEBUG=False
ALLOWED_HOSTS=your-domain.com
SECRET_KEY=your-production-secret-key
```

**Frontend `.env`:**
```env
VITE_API_URL=https://api.your-domain.com/api
```

### SSL/HTTPS

Backend settings:
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

### Common Commands

```bash
# Check backend is running
curl http://localhost:8000/health/

# Check API endpoint
curl http://localhost:8000/api/meters/

# Test login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@amsol.com","password":"Admin123!"}'
```

### Logs Location
- Backend: Terminal output
- Frontend: Browser console (F12)
- Django: `backend/logs/amsol.log` (when configured)

---

**Integration complete! You now have a fully connected full-stack application! 🎊**