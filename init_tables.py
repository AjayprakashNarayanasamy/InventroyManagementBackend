# create_tables.py
from app.database.database import engine, Base
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")
print("\nTables created:")
print("- categories")
print("- suppliers")
print("- products")