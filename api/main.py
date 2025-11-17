from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from httpx import AsyncClient
from typing import Optional
import os
import mercadopago
from .models import CartItem, PickupSelection
from .database import get_session

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

ML_SEARCH_URL = "https://api.mercadolibre.com/sites/MLA/search"
sdk = mercadopago.SDK(os.getenv("MP_ACCESS_TOKEN"))

PICKUP_POINTS = [
    {"name": "Local Palermo", "address": "Guatemala 4770, Palermo, CABA"},
    {"name": "Local Belgrano", "address": "Av. Cabildo 2230, Belgrano, CABA"},
    {"name": "Local Recoleta", "address": "Av. Santa Fe 1850, Recoleta, CABA"},
    {"name": "Local Almagro", "address": "Av. Corrientes 4500, Almagro, CABA"},
    {"name": "Local Flores", "address": "Av. Rivadavia 6800, Flores, CABA"},
    {"name": "Local Quilmes", "address": "Av. Mitre 750, Quilmes, GBA"},
    {"name": "Local San Isidro", "address": "Av. Centenario 950, San Isidro, GBA"},
    {"name": "Local La Plata", "address": "Calle 7 esq. 50, La Plata"},
]

@app.get("/pickup-points")
def pickup_points(): return PICKUP_POINTS

@app.post("/pickup-select")
def select_pickup(point: dict, session: Session = Depends(get_session)):
    session.exec(select(PickupSelection)).delete()
    sel = PickupSelection(**point)
    session.add(sel); session.commit(); session.refresh(sel)
    return sel

@app.get("/pickup-selected")
def get_selected(session: Session = Depends(get_session)):
    sel = session.exec(select(PickupSelection)).first()
    return sel or {"pickup_name": "No seleccionado", "pickup_address": ""}

@app.get("/search")
async def search(q: str):
    async with AsyncClient() as client:
        r = await client.get(ML_SEARCH_URL, params={"q": q, "limit": 20})
        data = r.json()
        results = []
        for item in data["results"]:
            if not item.get("catalog_product_id"): continue
            inst = item.get("installments") or {}
            cuotas = f"{inst.get('quantity', 0)}x ${inst.get('amount', 0):,.0f} sin interés".replace(",", ".") if inst.get("rate", 1) == 0 else "Con interés"
            results.append({
                "id": item["id"], "title": item["title"], "price": item["price"],
                "image": item["thumbnail"], "shipping": item["shipping"]["free_shipping"],
                "installments": cuotas, "condition": item["condition"]
            })
        return results

@app.post("/cart")
async def add(item: CartItem, session: Session = Depends(get_session)):
    session.add(item); session.commit(); session.refresh(item)
    return item

@app.get("/cart")
def cart(session: Session = Depends(get_session)):
    return session.exec(select(CartItem)).all()

@app.delete("/cart/{id}")
def delete(id: int, session: Session = Depends(get_session)):
    item = session.get(CartItem, id)
    if item: session.delete(item); session.commit()
    return {"ok": True}

@app.post("/mp/create-preference")
async def mp_pref(session: Session = Depends(get_session)):
    items = session.exec(select(CartItem)).all()
    if not items: raise HTTPException(400, "Carrito vacío")
    sel = session.exec(select(PickupSelection)).first()
    note = f"RETIRO: {sel.pickup_name} - {sel.pickup_address}" if sel else "Retiro en local"
    pref = {
        "items": [{"title": i.title[:256], "quantity": i.quantity, "currency_id": "ARS", "unit_price": float(i.price), "picture_url": i.image} for i in items],
        "back_urls": {"success": "/", "failure": "/", "pending": "/"},
        "auto_return": "approved",
        "statement_descriptor": "Supermercado AR",
        "additional_info": note
    }
    return {"init_point": sdk.preference().create(pref)["response"]["init_point"]}
