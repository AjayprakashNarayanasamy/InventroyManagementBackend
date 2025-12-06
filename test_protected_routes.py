# test_protected_routes.py
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_protected_routes():
    print("=" * 70)
    print("PROTECTED ROUTES TEST")
    print("=" * 70)
    
    # First, login to get token
    print("\n1. 🔐 Logging in...")
    
    try:
        # Try admin login first
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": "admin", "password": "Admin@123"}
        )
        
        if response.status_code != 200:
            # Try with test user
            print("Admin login failed, trying test user...")
            # Register a test user first
            user_data = {
                "email": "test@protected.com",
                "username": "protected",
                "full_name": "Protected User",
                "password": "Test@123"
            }
            response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
            if response.status_code == 201:
                print("Created test user")
                response = requests.post(
                    f"{BASE_URL}/auth/login",
                    data={"username": "protected", "password": "Test@123"}
                )
        
        if response.status_code == 200:
            result = response.json()
            token = result["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login successful")
            user_info = result.get('user', {})
            print(f"   User: {user_info.get('username', 'N/A')}")
        else:
            print(f"❌ Login failed: {response.text}")
            return
        
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return
    
    # Test unprotected endpoints (should fail without token)
    print("\n2. 🚫 Testing endpoints WITHOUT token...")
    
    endpoints = [
        ("Categories", "/categories/"),
        ("Products", "/products/"),
        ("Suppliers", "/suppliers/"),
        ("Inventory Summary", "/products/inventory/summary")
    ]
    
    for name, endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}")
        print(f"   {name}: Status {response.status_code} (should be 401 or 403)")
    
    # Test protected endpoints WITH token
    print("\n3. ✅ Testing endpoints WITH token...")
    
    for name, endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"   {name}: {len(data)} items")
            elif isinstance(data, dict):
                print(f"   {name}: Success")
                if "total_products" in data:
                    print(f"      Products: {data.get('total_products', 0)}")
        else:
            print(f"   {name}: Failed (Status: {response.status_code})")
    
    # Test POST operations (create data)
    print("\n4. 📝 Testing POST operations...")
    
    # Create category
    category_data = {"name": "Protected Test", "description": "Test from protected route"}
    response = requests.post(f"{BASE_URL}/categories/", json=category_data, headers=headers)
    if response.status_code == 201:
        category = response.json()
        print(f"✅ Created category: {category['name']}")
        
        # Create supplier
        supplier_data = {
            "name": "Protected Supplier",
            "contact_person": "Test Contact",
            "email": "supplier@protected.com",
            "phone": "+91-9876543210"
        }
        response = requests.post(f"{BASE_URL}/suppliers/", json=supplier_data, headers=headers)
        if response.status_code == 201:
            supplier = response.json()
            print(f"✅ Created supplier: {supplier['name']}")
            
            # Create product
            product_data = {
                "sku": "PROTECTED-001",
                "name": "Protected Test Product",
                "description": "Created via protected route",
                "category_id": category['id'],
                "supplier_id": supplier['id'],
                "cost_price": 25.00,
                "selling_price": 49.99,
                "current_stock": 50
            }
            response = requests.post(f"{BASE_URL}/products/", json=product_data, headers=headers)
            if response.status_code == 201:
                product = response.json()
                print(f"✅ Created product: {product['name']}")
                print(f"   SKU: {product['sku']}")
                print(f"   Stock: {product['current_stock']}")
                
                # Cleanup - delete test data
                print("\n5. 🧹 Cleaning up test data...")
                
                # Delete product
                response = requests.delete(f"{BASE_URL}/products/{product['id']}", headers=headers)
                if response.status_code == 204:
                    print("   Deleted product")
                
                # Delete supplier
                response = requests.delete(f"{BASE_URL}/suppliers/{supplier['id']}", headers=headers)
                if response.status_code == 204:
                    print("   Deleted supplier")
                
                # Delete category
                response = requests.delete(f"{BASE_URL}/categories/{category['id']}", headers=headers)
                if response.status_code == 204:
                    print("   Deleted category")
            else:
                print(f"❌ Failed to create product: {response.text}")
        else:
            print(f"❌ Failed to create supplier: {response.text}")
    else:
        print(f"❌ Failed to create category: {response.text}")
    
    # Test invalid token
    print("\n6. 🚨 Testing invalid token...")
    invalid_headers = {"Authorization": "Bearer invalid_token_here"}
    response = requests.get(f"{BASE_URL}/categories/", headers=invalid_headers)
    print(f"   Invalid token response: Status {response.status_code} (should be 401)")
    
    # Test expired token scenario (would need actual expired token)
    print("   (Expired token test requires actual expired JWT)")
    
    print("\n" + "=" * 70)
    print("🎉 PROTECTED ROUTES TEST COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    test_protected_routes()