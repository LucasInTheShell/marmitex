from fastapi import APIRouter

# Endpoints enter with the order vertical slice; keeping the router in the
# composition root now makes module ownership explicit without exposing stubs.
router = APIRouter(prefix="/orders", tags=["orders"])

