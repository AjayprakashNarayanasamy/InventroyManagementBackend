# app/crud/supplier.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


class CRUDSupplier:
    def get(self, db: Session, supplier_id: int) -> Optional[Supplier]:
        return db.query(Supplier).filter(Supplier.id == supplier_id).first()

    def get_by_name(self, db: Session, name: str) -> Optional[Supplier]:
        return db.query(Supplier).filter(Supplier.name == name).first()

    def get_by_email(self, db: Session, email: str) -> Optional[Supplier]:
        return db.query(Supplier).filter(Supplier.email == email).first()

    def get_all(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[Supplier]:
        return db.query(Supplier).offset(skip).limit(limit).all()

    def search(
        self, db: Session, search_term: str, skip: int = 0, limit: int = 100
    ) -> List[Supplier]:
        return db.query(Supplier).filter(
            or_(
                Supplier.name.ilike(f"%{search_term}%"),
                Supplier.contact_person.ilike(f"%{search_term}%"),
                Supplier.email.ilike(f"%{search_term}%"),
                Supplier.phone.ilike(f"%{search_term}%")
            )
        ).offset(skip).limit(limit).all()

    def get_active_suppliers(self, db: Session, skip: int = 0, limit: int = 100) -> List[Supplier]:
        return db.query(Supplier).filter(Supplier.is_active == True).offset(skip).limit(limit).all()

    def create(self, db: Session, supplier: SupplierCreate) -> Supplier:
        db_supplier = Supplier(
            name=supplier.name,
            contact_person=supplier.contact_person,
            email=supplier.email,
            phone=supplier.phone,
            address=supplier.address,
            city=supplier.city,
            state=supplier.state,
            country=supplier.country,
            postal_code=supplier.postal_code,
            tax_id=supplier.tax_id,
            website=supplier.website,
            is_active=supplier.is_active,
            payment_terms=supplier.payment_terms,
            rating=supplier.rating,
            notes=supplier.notes
        )
        db.add(db_supplier)
        db.commit()
        db.refresh(db_supplier)
        return db_supplier

    def update(
        self, db: Session, supplier_id: int, supplier: SupplierUpdate
    ) -> Optional[Supplier]:
        db_supplier = self.get(db, supplier_id)
        if not db_supplier:
            return None
        
        update_data = supplier.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_supplier, field, value)
        
        db.commit()
        db.refresh(db_supplier)
        return db_supplier

    def delete(self, db: Session, supplier_id: int) -> bool:
        db_supplier = self.get(db, supplier_id)
        if not db_supplier:
            return False
        
        db.delete(db_supplier)
        db.commit()
        return True


supplier = CRUDSupplier()