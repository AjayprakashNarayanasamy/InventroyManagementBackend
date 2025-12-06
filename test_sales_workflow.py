#!/usr/bin/env python3
"""
Comprehensive Endpoint Tester for Inventory Management System
Tests ALL API endpoints to ensure they're working
"""

import sys
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"
TEST_DATA = {}

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"🔍 {title}")
    print("="*70)

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_warning(message):
    """Print warning message"""
    print(f"⚠️  {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ️  {message}")

def check_server():
    """Check if server is running"""
    print_header("1. SERVER CHECK")
    try:
        # Check root endpoint
        response = httpx.get("http://localhost:8000/", timeout=5)
        print_info(f"Root endpoint: {response.status_code}")
        
        # Check health endpoint
        response = httpx.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print_success(f"Server is running: {health_data}")
            
            # Check API docs
            response = httpx.get("http://localhost:8000/api/docs", timeout=5)
            if response.status_code == 200:
                print_success("API documentation available at /api/docs")
            else:
                print_warning("API docs not accessible")
            
            return True
        else:
            print_error(f"Server returned status {response.status_code}")
            return False
    except httpx.ConnectError:
        print_error("Cannot connect to server at http://localhost:8000")
        print_info("\nPlease start the server with:")
        print_info("  uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def test_public_endpoints():
    """Test endpoints that don't require authentication"""
    print_header("2. PUBLIC ENDPOINTS (No Auth Required)")
    
    endpoints = [
        ("GET", "/", "Root endpoint"),
        ("GET", "/health", "Health check"),
        ("GET", "/api/docs", "Swagger UI"),
        ("GET", "/api/redoc", "ReDoc UI"),
    ]
    
    with httpx.Client(timeout=10.0) as client:
        for method, endpoint, description in endpoints:
            try:
                if method == "GET":
                    response = client.get(f"http://localhost:8000{endpoint}")
                else:
                    response = client.request(method, f"http://localhost:8000{endpoint}")
                
                if response.status_code < 400:
                    print_success(f"{method} {endpoint}: {response.status_code} - {description}")
                else:
                    print_warning(f"{method} {endpoint}: {response.status_code} - {description}")
                    
            except Exception as e:
                print_error(f"{method} {endpoint}: Error - {str(e)[:50]}")

def authenticate():
    """Authenticate and get token"""
    print_header("3. AUTHENTICATION ENDPOINTS")
    
    with httpx.Client(timeout=10.0) as client:
        # Test login with admin
        print("\nTesting auth/login (admin)...")
        try:
            response = client.post(
                f"{BASE_URL}/auth/login",
                data={"username": "admin", "password": "Admin@123"}
            )
            
            if response.status_code == 200:
                result = response.json()
                token = result["access_token"]
                print_success(f"Admin login successful")
                TEST_DATA['admin_token'] = token
                TEST_DATA['admin_headers'] = {"Authorization": f"Bearer {token}"}
                return True
            else:
                print_warning(f"Admin login failed: {response.status_code}")
                
                # Try to register and login as test user
                print("\nCreating test user...")
                timestamp = datetime.now().timestamp()
                user_data = {
                    "email": f"test{timestamp}@example.com",
                    "username": f"testuser{timestamp}",
                    "full_name": "Test User",
                    "password": "Test@123"
                }
                
                response = client.post(f"{BASE_URL}/auth/register", json=user_data)
                if response.status_code == 201:
                    print_success(f"User registered: {user_data['username']}")
                    
                    # Login with new user
                    response = client.post(
                        f"{BASE_URL}/auth/login",
                        data={"username": user_data['username'], "password": "Test@123"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        token = result["access_token"]
                        print_success(f"Test user login successful")
                        TEST_DATA['user_token'] = token
                        TEST_DATA['user_headers'] = {"Authorization": f"Bearer {token}"}
                        return True
                else:
                    print_error(f"Registration failed: {response.text}")
                    return False
                    
        except Exception as e:
            print_error(f"Authentication error: {e}")
            return False

def test_auth_endpoints():
    """Test authentication endpoints"""
    headers = TEST_DATA.get('admin_headers') or TEST_DATA.get('user_headers')
    if not headers:
        print_error("No authentication headers available")
        return False
    
    with httpx.Client(timeout=10.0, headers=headers) as client:
        endpoints = [
            ("GET", "/auth/me", "Get current user"),
            ("POST", "/auth/logout", "Logout (placeholder)"),
        ]
        
        for method, endpoint, description in endpoints:
            try:
                if method == "GET":
                    response = client.get(f"{BASE_URL}{endpoint}")
                elif method == "POST":
                    response = client.post(f"{BASE_URL}{endpoint}")
                else:
                    response = client.request(method, f"{BASE_URL}{endpoint}")
                
                if response.status_code < 400:
                    print_success(f"{method} {endpoint}: {response.status_code}")
                elif response.status_code == 401:
                    print_warning(f"{method} {endpoint}: 401 (Unauthorized - expected for some)")
                else:
                    print_warning(f"{method} {endpoint}: {response.status_code}")
                    
            except Exception as e:
                print_error(f"{method} {endpoint}: Error - {str(e)[:50]}")

def test_category_endpoints():
    """Test category endpoints"""
    print_header("4. CATEGORY ENDPOINTS")
    
    headers = TEST_DATA.get('admin_headers') or TEST_DATA.get('user_headers')
    if not headers:
        print_error("No authentication headers available")
        return
    
    with httpx.Client(timeout=10.0, headers=headers) as client:
        # Test GET /categories
        print("\nTesting GET /categories...")
        response = client.get(f"{BASE_URL}/categories/")
        if response.status_code == 200:
            categories = response.json()
            print_success(f"GET /categories: {len(categories)} categories found")
        else:
            print_error(f"GET /categories: {response.status_code}")
        
        # Test POST /categories
        print("\nTesting POST /categories...")
        category_data = {
            "name": f"Test Category {datetime.now().timestamp()}",
            "description": "Test category description"
        }
        response = client.post(f"{BASE_URL}/categories/", json=category_data)
        if response.status_code == 201:
            TEST_DATA['category'] = response.json()
            print_success(f"POST /categories: Created category ID {TEST_DATA['category']['id']}")
            
            # Test GET /categories/{id}
            print("\nTesting GET /categories/{id}...")
            response = client.get(f"{BASE_URL}/categories/{TEST_DATA['category']['id']}")
            if response.status_code == 200:
                print_success(f"GET /categories/{{id}}: Found category")
            else:
                print_error(f"GET /categories/{{id}}: {response.status_code}")
            
            # Test PUT /categories/{id}
            print("\nTesting PUT /categories/{id}...")
            update_data = {"name": f"Updated Category {datetime.now().timestamp()}"}
            response = client.put(
                f"{BASE_URL}/categories/{TEST_DATA['category']['id']}",
                json=update_data
            )
            if response.status_code == 200:
                print_success(f"PUT /categories/{{id}}: Updated category")
            else:
                print_error(f"PUT /categories/{{id}}: {response.status_code}")
            
            # Test DELETE /categories/{id}
            print("\nTesting DELETE /categories/{id}...")
            response = client.delete(f"{BASE_URL}/categories/{TEST_DATA['category']['id']}")
            if response.status_code == 204:
                print_success(f"DELETE /categories/{{id}}: Deleted category")
            else:
                print_error(f"DELETE /categories/{{id}}: {response.status_code}")
        else:
            print_error(f"POST /categories: {response.status_code} - {response.text}")

def test_supplier_endpoints():
    """Test supplier endpoints"""
    print_header("5. SUPPLIER ENDPOINTS")
    
    headers = TEST_DATA.get('admin_headers') or TEST_DATA.get('user_headers')
    if not headers:
        print_error("No authentication headers available")
        return
    
    with httpx.Client(timeout=10.0, headers=headers) as client:
        # Test GET /suppliers
        print("\nTesting GET /suppliers...")
        response = client.get(f"{BASE_URL}/suppliers/")
        if response.status_code == 200:
            suppliers = response.json()
            print_success(f"GET /suppliers: {len(suppliers)} suppliers found")
        else:
            print_error(f"GET /suppliers: {response.status_code}")
        
        # Test POST /suppliers
        print("\nTesting POST /suppliers...")
        timestamp = datetime.now().timestamp()
        supplier_data = {
            "name": f"Test Supplier {timestamp}",
            "contact_person": "Test Contact",
            "email": f"test{timestamp}@example.com",
            "phone": "+91-9876543210"
        }
        response = client.post(f"{BASE_URL}/suppliers/", json=supplier_data)
        if response.status_code == 201:
            TEST_DATA['supplier'] = response.json()
            print_success(f"POST /suppliers: Created supplier ID {TEST_DATA['supplier']['id']}")
            
            # Test GET /suppliers/{id}
            print("\nTesting GET /suppliers/{id}...")
            response = client.get(f"{BASE_URL}/suppliers/{TEST_DATA['supplier']['id']}")
            if response.status_code == 200:
                print_success(f"GET /suppliers/{{id}}: Found supplier")
            else:
                print_error(f"GET /suppliers/{{id}}: {response.status_code}")
            
            # Test PUT /suppliers/{id}
            print("\nTesting PUT /suppliers/{id}...")
            update_data = {"contact_person": "Updated Contact"}
            response = client.put(
                f"{BASE_URL}/suppliers/{TEST_DATA['supplier']['id']}",
                json=update_data
            )
            if response.status_code == 200:
                print_success(f"PUT /suppliers/{{id}}: Updated supplier")
            else:
                print_error(f"PUT /suppliers/{{id}}: {response.status_code}")
            
            # Test GET /suppliers/search
            print("\nTesting GET /suppliers/search...")
            response = client.get(f"{BASE_URL}/suppliers/search?search_term=Test")
            if response.status_code == 200:
                print_success(f"GET /suppliers/search: Search working")
            else:
                print_warning(f"GET /suppliers/search: {response.status_code}")
            
            # Test DELETE /suppliers/{id}
            print("\nTesting DELETE /suppliers/{id}...")
            response = client.delete(f"{BASE_URL}/suppliers/{TEST_DATA['supplier']['id']}")
            if response.status_code == 204:
                print_success(f"DELETE /suppliers/{{id}}: Deleted supplier")
            else:
                print_error(f"DELETE /suppliers/{{id}}: {response.status_code}")
        else:
            print_error(f"POST /suppliers: {response.status_code} - {response.text}")

def test_product_endpoints():
    """Test product endpoints"""
    print_header("6. PRODUCT ENDPOINTS")
    
    headers = TEST_DATA.get('admin_headers') or TEST_DATA.get('user_headers')
    if not headers:
        print_error("No authentication headers available")
        return
    
    with httpx.Client(timeout=10.0, headers=headers) as client:
        # First create category and supplier for product
        print("\nCreating test category and supplier for products...")
        
        # Create category
        timestamp = datetime.now().timestamp()
        category_data = {
            "name": f"Product Test Cat {timestamp}",
            "description": "For product testing"
        }
        response = client.post(f"{BASE_URL}/categories/", json=category_data)
        if response.status_code != 201:
            print_error("Failed to create test category")
            return
        category = response.json()
        
        # Create supplier
        supplier_data = {
            "name": f"Product Test Supplier {timestamp}",
            "contact_person": "Product Test Contact",
            "email": f"product{timestamp}@example.com"
        }
        response = client.post(f"{BASE_URL}/suppliers/", json=supplier_data)
        if response.status_code != 201:
            print_error("Failed to create test supplier")
            # Clean up category
            client.delete(f"{BASE_URL}/categories/{category['id']}")
            return
        supplier = response.json()
        
        # Test GET /products
        print("\nTesting GET /products...")
        response = client.get(f"{BASE_URL}/products/")
        if response.status_code == 200:
            products = response.json()
            print_success(f"GET /products: {len(products)} products found")
        else:
            print_error(f"GET /products: {response.status_code}")
        
        # Test POST /products
        print("\nTesting POST /products...")
        product_data = {
            "sku": f"TEST-SKU-{timestamp}",
            "name": f"Test Product {timestamp}",
            "description": "Test product description",
            "category_id": category['id'],
            "supplier_id": supplier['id'],
            "cost_price": 100.00,
            "selling_price": 150.00,
            "current_stock": 50,
            "min_stock_level": 10,
            "max_stock_level": 100
        }
        response = client.post(f"{BASE_URL}/products/", json=product_data)
        if response.status_code == 201:
            TEST_DATA['product'] = response.json()
            print_success(f"POST /products: Created product ID {TEST_DATA['product']['id']}")
            
            # Test GET /products/{id}
            print("\nTesting GET /products/{id}...")
            response = client.get(f"{BASE_URL}/products/{TEST_DATA['product']['id']}")
            if response.status_code == 200:
                print_success(f"GET /products/{{id}}: Found product")
            else:
                print_error(f"GET /products/{{id}}: {response.status_code}")
            
            # Test GET /products/sku/{sku}
            print("\nTesting GET /products/sku/{sku}...")
            response = client.get(f"{BASE_URL}/products/sku/{product_data['sku']}")
            if response.status_code == 200:
                print_success(f"GET /products/sku/{{sku}}: Found product by SKU")
            else:
                print_warning(f"GET /products/sku/{{sku}}: {response.status_code}")
            
            # Test PUT /products/{id}
            print("\nTesting PUT /products/{id}...")
            update_data = {"name": f"Updated Product {datetime.now().timestamp()}"}
            response = client.put(
                f"{BASE_URL}/products/{TEST_DATA['product']['id']}",
                json=update_data
            )
            if response.status_code == 200:
                print_success(f"PUT /products/{{id}}: Updated product")
            else:
                print_error(f"PUT /products/{{id}}: {response.status_code}")
            
            # Test GET /products/search
            print("\nTesting GET /products/search...")
            response = client.get(f"{BASE_URL}/products/search?search_term=Test")
            if response.status_code == 200:
                print_success(f"GET /products/search: Search working")
            else:
                print_warning(f"GET /products/search: {response.status_code}")
            
            # Test GET /products/low-stock
            print("\nTesting GET /products/low-stock...")
            response = client.get(f"{BASE_URL}/products/low-stock")
            if response.status_code == 200:
                print_success(f"GET /products/low-stock: Working")
            else:
                print_warning(f"GET /products/low-stock: {response.status_code}")
            
            # Test GET /products/out-of-stock
            print("\nTesting GET /products/out-of-stock...")
            response = client.get(f"{BASE_URL}/products/out-of-stock")
            if response.status_code == 200:
                print_success(f"GET /products/out-of-stock: Working")
            else:
                print_warning(f"GET /products/out-of-stock: {response.status_code}")
            
            # Test GET /products/inventory/summary
            print("\nTesting GET /products/inventory/summary...")
            response = client.get(f"{BASE_URL}/products/inventory/summary")
            if response.status_code == 200:
                summary = response.json()
                print_success(f"GET /products/inventory/summary: Working")
                print(f"   Total Products: {summary.get('total_products', 'N/A')}")
            else:
                print_warning(f"GET /products/inventory/summary: {response.status_code}")
            
            # Test PATCH /products/{id}/stock
            print("\nTesting PATCH /products/{id}/stock...")
            stock_data = {"quantity": 10, "notes": "Test stock addition"}
            response = client.patch(
                f"{BASE_URL}/products/{TEST_DATA['product']['id']}/stock",
                json=stock_data
            )
            if response.status_code == 200:
                print_success(f"PATCH /products/{{id}}/stock: Stock updated")
            else:
                print_error(f"PATCH /products/{{id}}/stock: {response.status_code}")
            
            # Test DELETE /products/{id}
            print("\nTesting DELETE /products/{id}...")
            response = client.delete(f"{BASE_URL}/products/{TEST_DATA['product']['id']}")
            if response.status_code == 204:
                print_success(f"DELETE /products/{{id}}: Product marked inactive")
            else:
                print_error(f"DELETE /products/{{id}}: {response.status_code}")
                
        else:
            print_error(f"POST /products: {response.status_code} - {response.text}")
        
        # Clean up category and supplier
        print("\nCleaning up test category and supplier...")
        client.delete(f"{BASE_URL}/suppliers/{supplier['id']}")
        client.delete(f"{BASE_URL}/categories/{category['id']}")

def test_sales_endpoints():
    """Test sales endpoints"""
    print_header("7. SALES ENDPOINTS")
    
    headers = TEST_DATA.get('admin_headers') or TEST_DATA.get('user_headers')
    if not headers:
        print_error("No authentication headers available")
        return
    
    with httpx.Client(timeout=15.0, headers=headers) as client:
        # First create test data for sales
        print("\nCreating test data for sales...")
        
        # Create category
        timestamp = datetime.now().timestamp()
        category_data = {
            "name": f"Sales Test Cat {timestamp}",
            "description": "For sales testing"
        }
        response = client.post(f"{BASE_URL}/categories/", json=category_data)
        if response.status_code != 201:
            print_error("Failed to create test category for sales")
            return
        category = response.json()
        
        # Create supplier
        supplier_data = {
            "name": f"Sales Test Supplier {timestamp}",
            "contact_person": "Sales Test Contact",
            "email": f"sales{timestamp}@example.com"
        }
        response = client.post(f"{BASE_URL}/suppliers/", json=supplier_data)
        if response.status_code != 201:
            print_error("Failed to create test supplier for sales")
            client.delete(f"{BASE_URL}/categories/{category['id']}")
            return
        supplier = response.json()
        
        # Create product
        product_data = {
            "sku": f"SALES-SKU-{timestamp}",
            "name": f"Sales Test Product {timestamp}",
            "description": "For sales testing",
            "category_id": category['id'],
            "supplier_id": supplier['id'],
            "cost_price": 50.00,
            "selling_price": 75.00,
            "current_stock": 100,
            "min_stock_level": 10,
            "max_stock_level": 200
        }
        response = client.post(f"{BASE_URL}/products/", json=product_data)
        if response.status_code != 201:
            print_error("Failed to create test product for sales")
            client.delete(f"{BASE_URL}/suppliers/{supplier['id']}")
            client.delete(f"{BASE_URL}/categories/{category['id']}")
            return
        product = response.json()
        
        # Test GET /sales
        print("\nTesting GET /sales...")
        response = client.get(f"{BASE_URL}/sales/")
        if response.status_code == 200:
            sales = response.json()
            print_success(f"GET /sales: {len(sales)} sales found")
        else:
            print_error(f"GET /sales: {response.status_code}")
        
        # Test POST /sales
        print("\nTesting POST /sales...")
        sale_items = [
            {
                "product_id": product['id'],
                "quantity": 2,
                "unit_price": 75.00,
                "tax_rate": 18.0,
                "discount_percent": 5.0
            }
        ]
        
        sale_data = {
            "customer_name": "Sales Test Customer",
            "payment_method": "cash",
            "status": "completed",
            "items": sale_items
        }
        
        response = client.post(f"{BASE_URL}/sales/", json=sale_data)
        if response.status_code == 201:
            TEST_DATA['sale'] = response.json()
            print_success(f"POST /sales: Created sale ID {TEST_DATA['sale']['id']}")
            print(f"   Sale Number: {TEST_DATA['sale']['sale_number']}")
            print(f"   Total: ${TEST_DATA['sale']['grand_total']}")
            
            # Test GET /sales/{id}
            print("\nTesting GET /sales/{id}...")
            response = client.get(f"{BASE_URL}/sales/{TEST_DATA['sale']['id']}")
            if response.status_code == 200:
                print_success(f"GET /sales/{{id}}: Found sale")
            else:
                print_error(f"GET /sales/{{id}}: {response.status_code}")
            
            # Test GET /sales/number/{number}
            print("\nTesting GET /sales/number/{number}...")
            response = client.get(f"{BASE_URL}/sales/number/{TEST_DATA['sale']['sale_number']}")
            if response.status_code == 200:
                print_success(f"GET /sales/number/{{number}}: Found sale by number")
            else:
                print_warning(f"GET /sales/number/{{number}}: {response.status_code}")
            
            # Test GET /sales/dashboard/summary
            print("\nTesting GET /sales/dashboard/summary...")
            response = client.get(f"{BASE_URL}/sales/dashboard/summary")
            if response.status_code == 200:
                summary = response.json()
                print_success(f"GET /sales/dashboard/summary: Working")
                print(f"   Total Sales: {summary.get('total_sales', 'N/A')}")
            else:
                print_warning(f"GET /sales/dashboard/summary: {response.status_code}")
            
            # Test GET /sales/dashboard/daily
            print("\nTesting GET /sales/dashboard/daily...")
            response = client.get(f"{BASE_URL}/sales/dashboard/daily?days=7")
            if response.status_code == 200:
                daily = response.json()
                print_success(f"GET /sales/dashboard/daily: {len(daily)} days of data")
            else:
                print_warning(f"GET /sales/dashboard/daily: {response.status_code}")
            
            # Test GET /sales/reports/by-product
            print("\nTesting GET /sales/reports/by-product...")
            response = client.get(f"{BASE_URL}/sales/reports/by-product")
            if response.status_code == 200:
                report = response.json()
                print_success(f"GET /sales/reports/by-product: Report generated")
            else:
                print_warning(f"GET /sales/reports/by-product: {response.status_code}")
            
            # Test GET /sales/reports/top-products
            print("\nTesting GET /sales/reports/top-products...")
            response = client.get(f"{BASE_URL}/sales/reports/top-products?limit=5")
            if response.status_code == 200:
                print_success(f"GET /sales/reports/top-products: Working")
            else:
                print_warning(f"GET /sales/reports/top-products: {response.status_code}")
            
            # Test POST /sales/{id}/cancel
            print("\nTesting POST /sales/{id}/cancel...")
            response = client.post(f"{BASE_URL}/sales/{TEST_DATA['sale']['id']}/cancel")
            if response.status_code == 200:
                print_success(f"POST /sales/{{id}}/cancel: Sale cancelled")
            else:
                print_warning(f"POST /sales/{{id}}/cancel: {response.status_code} - May already be cancelled")
            
            # Test PUT /sales/{id} (for draft sales)
            print("\nTesting PUT /sales/{id}...")
            update_data = {"customer_name": "Updated Customer Name"}
            response = client.put(
                f"{BASE_URL}/sales/{TEST_DATA['sale']['id']}",
                json=update_data
            )
            # This might fail if sale is not in draft status
            if response.status_code == 200:
                print_success(f"PUT /sales/{{id}}: Updated sale")
            else:
                print_info(f"PUT /sales/{{id}}: {response.status_code} (Expected if sale not draft)")
                
        else:
            print_error(f"POST /sales: {response.status_code} - {response.text}")
        
        # Clean up
        print("\nCleaning up sales test data...")
        # Delete product (mark inactive)
        client.delete(f"{BASE_URL}/products/{product['id']}")
        # Delete supplier
        client.delete(f"{BASE_URL}/suppliers/{supplier['id']}")
        # Delete category
        client.delete(f"{BASE_URL}/categories/{category['id']}")

def test_user_endpoints():
    """Test user management endpoints (admin only)"""
    print_header("8. USER ENDPOINTS (Admin Required)")
    
    headers = TEST_DATA.get('admin_headers')
    if not headers:
        print_warning("Skipping user endpoints (admin token not available)")
        return
    
    with httpx.Client(timeout=10.0, headers=headers) as client:
        # Test GET /users
        print("\nTesting GET /users (admin only)...")
        response = client.get(f"{BASE_URL}/users/")
        if response.status_code == 200:
            users = response.json()
            print_success(f"GET /users: {len(users)} users found")
        elif response.status_code == 403:
            print_warning("GET /users: 403 Forbidden (not admin)")
        else:
            print_error(f"GET /users: {response.status_code}")
        
        # Create a test user via admin
        print("\nTesting POST /users (admin only)...")
        timestamp = datetime.now().timestamp()
        user_data = {
            "email": f"admincreated{timestamp}@example.com",
            "username": f"admincreated{timestamp}",
            "full_name": "Admin Created User",
            "password": "Test@123"
        }
        response = client.post(f"{BASE_URL}/users/", json=user_data)
        if response.status_code == 201:
            created_user = response.json()
            print_success(f"POST /users: Created user ID {created_user['id']}")
            
            # Test GET /users/{id}
            print("\nTesting GET /users/{id}...")
            response = client.get(f"{BASE_URL}/users/{created_user['id']}")
            if response.status_code == 200:
                print_success(f"GET /users/{{id}}: Found user")
            else:
                print_error(f"GET /users/{{id}}: {response.status_code}")
            
            # Test PUT /users/{id}
            print("\nTesting PUT /users/{id}...")
            update_data = {"full_name": "Updated Admin Created User"}
            response = client.put(
                f"{BASE_URL}/users/{created_user['id']}",
                json=update_data
            )
            if response.status_code == 200:
                print_success(f"PUT /users/{{id}}: Updated user")
            else:
                print_error(f"PUT /users/{{id}}: {response.status_code}")
            
            # Test DELETE /users/{id}
            print("\nTesting DELETE /users/{id}...")
            response = client.delete(f"{BASE_URL}/users/{created_user['id']}")
            if response.status_code == 204:
                print_success(f"DELETE /users/{{id}}: Deleted user")
            else:
                print_error(f"DELETE /users/{{id}}: {response.status_code}")
        elif response.status_code == 403:
            print_warning("POST /users: 403 Forbidden (not admin)")
        else:
            print_error(f"POST /users: {response.status_code} - {response.text}")

def run_comprehensive_test():
    """Run comprehensive test of all endpoints"""
    print("="*80)
    print("🚀 COMPREHENSIVE INVENTORY MANAGEMENT SYSTEM ENDPOINT TEST")
    print("="*80)
    
    print("\n📋 Testing Plan:")
    print("1. ✅ Server Check")
    print("2. ✅ Public Endpoints")
    print("3. ✅ Authentication")
    print("4. ✅ Category Endpoints")
    print("5. ✅ Supplier Endpoints")
    print("6. ✅ Product Endpoints")
    print("7. ✅ Sales Endpoints")
    print("8. ✅ User Endpoints (Admin)")
    
    print("\n" + "="*80)
    
    # Track results
    results = {
        'server': False,
        'auth': False,
        'categories': False,
        'suppliers': False,
        'products': False,
        'sales': False,
        'users': False
    }
    
    try:
        # Step 1: Check server
        results['server'] = check_server()
        if not results['server']:
            print_error("Server check failed. Cannot continue.")
            return
        
        # Step 2: Test public endpoints
        test_public_endpoints()
        
        # Step 3: Authenticate
        results['auth'] = authenticate()
        if not results['auth']:
            print_error("Authentication failed. Cannot test protected endpoints.")
            return
        
        # Step 4: Test auth endpoints
        test_auth_endpoints()
        
        # Step 5: Test category endpoints
        test_category_endpoints()
        
        # Step 6: Test supplier endpoints
        test_supplier_endpoints()
        
        # Step 7: Test product endpoints
        test_product_endpoints()
        
        # Step 8: Test sales endpoints
        test_sales_endpoints()
        
        # Step 9: Test user endpoints
        test_user_endpoints()
        
        print_header("🎉 TEST SUMMARY")
        
        print("\n📊 Endpoint Test Results:")
        for module, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {module.upper():15} {status}")
        
        print("\n🔍 Quick Status Check:")
        print(f"  Server running:      {'✅' if results['server'] else '❌'}")
        print(f"  Authentication:      {'✅' if results['auth'] else '❌'}")
        print(f"  Categories API:      {'✅' if 'category' in TEST_DATA else '❌'}")
        print(f"  Suppliers API:       {'✅' if 'supplier' in TEST_DATA else '❌'}")
        print(f"  Products API:        {'✅' if 'product' in TEST_DATA else '❌'}")
        print(f"  Sales API:           {'✅' if 'sale' in TEST_DATA else '❌'}")
        
        print("\n📈 API Statistics:")
        print(f"  Total endpoints tested: ~50+")
        print(f"  Test duration:          {datetime.now().strftime('%H:%M:%S')}")
        
        print("\n💡 Next Steps:")
        print("  1. Check any ❌ failures above")
        print("  2. Review server logs for errors")
        print("  3. Test with frontend/dashboard")
        print("  4. Add more edge case tests")
        
        print("\n" + "="*80)
        print("🏁 ENDPOINT TESTING COMPLETE")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if httpx is installed
    try:
        import httpx
    except ImportError:
        print("❌ 'httpx' module not found. Please install it:")
        print("   pip install httpx")
        sys.exit(1)
    
    # Run the test
    run_comprehensive_test()