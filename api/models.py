from sqlmodel import SQLModel, Field
from typing import Optional

class CartItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str
    title: str
    price: float
    quantity: int = 1
    image: str

class PickupSelection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pickup_name: str
    pickup_address: str
