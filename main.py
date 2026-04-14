import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# 1. Initialize FastAPI
app = FastAPI(title="Subarna Apparel Automation")

# 2. Secure CORS Configuration
# This allows your live GitHub Pages site to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your GitHub Pages URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Supabase Credentials
# CRITICAL: Use the 'service_role' secret key here for stock deduction permissions
SUPABASE_URL = "https://unzhgcjequbqblogktmc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVuemhnY2plcXVicWJsb2drdG1jIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTkyMDQ0NywiZXhwIjoyMDkxNDk2NDQ3fQ.wtGgbMxIHjx3VlOAwwi5FDecEbJTHUaffjBU28L-gxE" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 4. Data Model for Payment Verification
class PaymentVerification(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    product_id: int

# 5. Routes
@app.get("/")
async def health_check():
    return {
        "status": "Online", 
        "project": "Subarna Apparel",
        "region": "West Bengal",
        "engine": "Python 3.12"
    }

@app.post("/payment/verify")
async def verify_payment(data: PaymentVerification):
    try:
        # Step A: Fetch current product details
        res = supabase.table("products").select("id, name, stock_count").eq("id", data.product_id).single().execute()
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Product not found")

        current_stock = res.data.get('stock_count', 0)
        product_name = res.data.get('name', 'Artisan Item')

        # Step B: Logic check for inventory
        if current_stock > 0:
            # Step C: Deduct 1 from Stock
            new_stock = current_stock - 1
            supabase.table("products").update({"stock_count": new_stock}).eq("id", data.product_id).execute()
            
            # Step D: Log the successful transaction in the 'orders' table
            order_entry = {
                "product_id": data.product_id,
                "payment_id": data.razorpay_payment_id,
                "status": "paid_and_verified"
            }
            supabase.table("orders").insert(order_entry).execute()

            print(f"✅ TRANSACTION SUCCESS: 1 x {product_name} sold. Remaining stock: {new_stock}")
            return {"status": "success", "message": f"Inventory updated for {product_name}"}
        
        else:
            print(f"⚠️ STOCK ALERT: {product_name} is out of stock.")
            return {"status": "error", "message": "Product recently sold out."}

    except Exception as e:
        print(f"❌ SYSTEM ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 6. Server Start Logic
@app.post("/products")
async def add_product(data: dict):
    try:
        # data will contain name, price, and image link
        response = supabase.table("products").insert(data).execute()
        return {"status": "success", "data": response.data}
    except Exception as e:
        print(f"Error adding product: {e}")
        raise HTTPException(status_code=500, detail="Failed to add product")
        # --- DELETE ORDER ROUTE ---
@app.delete("/orders/{order_id}")
async def delete_order(order_id: str):
    try:
        supabase.table("orders").delete().eq("id", order_id).execute()
        return {"status": "success", "message": "Order deleted"}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete order")

# --- DELETE PRODUCT ROUTE ---
@app.delete("/products/{product_id}")
async def delete_product(product_id: int):
    try:
        supabase.table("products").delete().eq("id", product_id).execute()
        return {"status": "success", "message": "Product deleted"}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete product")
if __name__ == "__main__":
    import uvicorn
    import os
    print("🚀 SUBARNA APPAREL BACKEND STARTING...")
    
    # Render will provide a port, or we use 8000 as a backup
    port = int(os.environ.get("PORT", 8000))
    
    # Use 0.0.0.0 to allow the cloud to see your app
    uvicorn.run(app, host="0.0.0.0", port=port)
