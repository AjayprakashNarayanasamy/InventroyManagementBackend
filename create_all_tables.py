from app.database.database import engine, Base
from app.models.category import Category
from app.models.supplier import Supplier
from app.models.product import Product
from app.models.user import User

print("Creating all database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created:")
print("   - categories")
print("   - suppliers")
print("   - products")
print("   - users")
