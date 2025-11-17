import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Kid, Moment, Item

app = FastAPI(title="Little Years Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def healthcheck():
    return {"status": "ok"}

@app.get("/test")
def test_database():
    """Quick DB connectivity check"""
    response = {"backend": "✅ Running", "database": "❌ Not Available"}
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["collections"] = db.list_collection_names()
        else:
            response["database"] = "❌ Not Configured"
    except Exception as e:
        response["database"] = f"⚠️ {str(e)[:80]}"
    return response

# ---------------------------
# Helpers
# ---------------------------

def _to_public(doc):
    if not doc:
        return doc
    d = doc.copy()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d

# ---------------------------
# Seed endpoint
# ---------------------------

class SeedResponse(BaseModel):
    inserted: List[str]

@app.post("/api/seed", response_model=SeedResponse)
def seed_demo():
    """Seed demo data: parent, grandma, kid Ava, a public photo, private artwork, audio moment."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    inserted_ids: List[str] = []

    # Upsert-like behavior: clear existing demo docs for idempotency
    db["kid"].delete_many({"name": "Ava"})
    db["moment"].delete_many({"kid_name": "Ava"})  # legacy safety if existed

    # Create kid Ava
    kid = Kid(
        name="Ava",
        nickname="Aves",
        avatar_url="https://images.unsplash.com/photo-1503454537195-1dcabb73ffb9?w=640",
        parent_email="parent@littleyears.demo",
        allowed_grandparents=["grandma@family.demo"],
    )
    kid_id = create_document("kid", kid)
    inserted_ids.append(kid_id)

    # Public photo moment
    public_photo = Moment(
        kid_id=kid_id,
        type="photo",
        title="First bike ride!",
        description="Sunset cruise in the park",
        media_url="https://images.unsplash.com/photo-1492724441997-5dc865305da7?w=1200",
        thumbnail_url="https://images.unsplash.com/photo-1492724441997-5dc865305da7?w=400",
        visibility="public",
        tags=["milestone", "outdoors"],
    )
    mid1 = create_document("moment", public_photo)
    inserted_ids.append(mid1)

    # Private artwork moment
    private_art = Moment(
        kid_id=kid_id,
        type="art",
        title="Finger painting",
        description="Blue and yellow masterpiece",
        media_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=1200",
        thumbnail_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=400",
        visibility="private",
        tags=["art", "home"],
    )
    mid2 = create_document("moment", private_art)
    inserted_ids.append(mid2)

    # Audio voice moment (treat as audio with placeholder url)
    audio_moment = Moment(
        kid_id=kid_id,
        type="audio",
        title="Goodnight message",
        description="Ava says goodnight to Grandma",
        media_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        visibility="public",
        tags=["voice"],
    )
    mid3 = create_document("moment", audio_moment)
    inserted_ids.append(mid3)

    return {"inserted": inserted_ids}

# ---------------------------
# Public API
# ---------------------------

@app.get("/api/kids")
def list_kids(grandparent: Optional[str] = Query(None, description="Filter by allowed grandparent email")):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filt = {}
    if grandparent:
        filt = {"allowed_grandparents": {"$in": [grandparent]}}
    kids = get_documents("kid", filt)
    return [_to_public(k) for k in kids]

@app.get("/api/kids/{kid_id}/timeline")
def kid_timeline(kid_id: str, include_private: bool = False, grandparent: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    from bson import ObjectId
    try:
        kid_obj = db["kid"].find_one({"_id": ObjectId(kid_id)})
        if not kid_obj:
            raise HTTPException(status_code=404, detail="Kid not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid kid id")

    # Access rules: by default only public. If include_private is True, require grandparent in allowed list
    visibility_filter = {"kid_id": kid_id, "visibility": "public"}
    if include_private:
        if grandparent and grandparent in (kid_obj.get("allowed_grandparents") or []):
            visibility_filter = {"kid_id": kid_id}  # include all
        else:
            # not authorized to view private
            include_private = False

    moments = get_documents("moment", visibility_filter)
    # Sort newest first by created_at if present
    moments.sort(key=lambda m: m.get("created_at"), reverse=True)
    return {
        "kid": _to_public(kid_obj),
        "moments": [_to_public(m) for m in moments],
        "includes_private": include_private,
    }

# Simple hello retained
@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
