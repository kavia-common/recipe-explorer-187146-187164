from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime

# Application metadata and tags for OpenAPI/Swagger
openapi_tags = [
    {
        "name": "Health",
        "description": "Service status and diagnostics.",
    },
    {
        "name": "Recipes",
        "description": "CRUD operations for managing recipes.",
    },
]

app = FastAPI(
    title="Recipe Explorer Backend",
    description=(
        "RESTful API for browsing, viewing, and managing recipes.\n\n"
        "This backend provides endpoints to list, retrieve, create, update, and delete recipes. "
        "It uses in-memory storage for simplicity and demo purposes."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# Configure CORS to allow all origins for preview purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PUBLIC_INTERFACE
class RecipeBase(BaseModel):
    """Base schema for Recipe input fields shared across create and update."""
    title: str = Field(..., description="The title of the recipe", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="A brief description of the recipe", max_length=2000)
    ingredients: List[str] = Field(default_factory=list, description="List of ingredients required for the recipe")
    steps: List[str] = Field(default_factory=list, description="Ordered list of cooking steps/instructions")
    image_url: Optional[HttpUrl] = Field(None, description="Optional image illustrating the recipe")
    prep_time_minutes: Optional[int] = Field(None, description="Preparation time in minutes", ge=0)
    cook_time_minutes: Optional[int] = Field(None, description="Cooking time in minutes", ge=0)
    servings: Optional[int] = Field(None, description="Number of servings", ge=1)


# PUBLIC_INTERFACE
class RecipeCreate(RecipeBase):
    """Schema for creating a new recipe."""
    pass


# PUBLIC_INTERFACE
class RecipeUpdate(BaseModel):
    """Schema for updating an existing recipe (partial updates supported)."""
    title: Optional[str] = Field(None, description="The title of the recipe", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="A brief description of the recipe", max_length=2000)
    ingredients: Optional[List[str]] = Field(None, description="List of ingredients required for the recipe")
    steps: Optional[List[str]] = Field(None, description="Ordered list of cooking steps/instructions")
    image_url: Optional[HttpUrl] = Field(None, description="Optional image illustrating the recipe")
    prep_time_minutes: Optional[int] = Field(None, description="Preparation time in minutes", ge=0)
    cook_time_minutes: Optional[int] = Field(None, description="Cooking time in minutes", ge=0)
    servings: Optional[int] = Field(None, description="Number of servings", ge=1)


# PUBLIC_INTERFACE
class Recipe(RecipeBase):
    """Recipe schema returned by the API with server-managed fields."""
    id: int = Field(..., description="Unique identifier of the recipe")
    created_at: datetime = Field(..., description="Timestamp when the recipe was created")
    updated_at: datetime = Field(..., description="Timestamp when the recipe was last updated")


# In-memory "database"
_db: Dict[int, Recipe] = {}
_id_counter: int = 0


def _next_id() -> int:
    """Generate the next recipe ID."""
    global _id_counter
    _id_counter += 1
    return _id_counter


def _now() -> datetime:
    return datetime.utcnow()


# Seed with a sample recipe for initial preview/demo
def _ensure_seed() -> None:
    if _db:
        return
    sample = Recipe(
        id=_next_id(),
        title="Classic Pancakes",
        description="Fluffy pancakes perfect for breakfast.",
        ingredients=[
            "1 1/2 cups all-purpose flour",
            "3 1/2 tsp baking powder",
            "1 tsp salt",
            "1 tbsp white sugar",
            "1 1/4 cups milk",
            "1 egg",
            "3 tbsp butter, melted",
        ],
        steps=[
            "In a large bowl, sift together the flour, baking powder, salt and sugar.",
            "Make a well in the center and pour in the milk, egg and melted butter; mix until smooth.",
            "Heat a lightly oiled griddle over medium high heat.",
            "Pour or scoop the batter onto the griddle, using approximately 1/4 cup for each pancake.",
            "Brown on both sides and serve hot.",
        ],
        image_url=None,
        prep_time_minutes=10,
        cook_time_minutes=15,
        servings=4,
        created_at=_now(),
        updated_at=_now(),
    )
    _db[sample.id] = sample


# Health check
@app.get(
    "/",
    summary="Health Check",
    tags=["Health"],
    response_model=dict,
)
def health_check():
    """Return a simple health status to verify the service is up."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/recipes",
    summary="List recipes",
    description="Retrieve a list of all recipes currently available.",
    tags=["Recipes"],
    response_model=List[Recipe],
)
def list_recipes() -> List[Recipe]:
    """List all recipes in the in-memory store."""
    _ensure_seed()
    return list(_db.values())


# PUBLIC_INTERFACE
@app.get(
    "/recipes/{recipe_id}",
    summary="Get recipe by ID",
    description="Retrieve a single recipe by its unique identifier.",
    tags=["Recipes"],
    response_model=Recipe,
)
def get_recipe(
    recipe_id: int = Path(..., description="The ID of the recipe to retrieve", ge=1)
) -> Recipe:
    """Get a recipe by ID."""
    _ensure_seed()
    recipe = _db.get(recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


# PUBLIC_INTERFACE
@app.post(
    "/recipes",
    summary="Create a recipe",
    description="Create a new recipe with the provided details.",
    tags=["Recipes"],
    response_model=Recipe,
    status_code=201,
)
def create_recipe(payload: RecipeCreate = Body(..., description="Recipe data for creation")) -> Recipe:
    """Create and store a new recipe."""
    _ensure_seed()
    rid = _next_id()
    now = _now()
    recipe = Recipe(
        id=rid,
        created_at=now,
        updated_at=now,
        **payload.model_dump(),
    )
    _db[rid] = recipe
    return recipe


# PUBLIC_INTERFACE
@app.put(
    "/recipes/{recipe_id}",
    summary="Update a recipe",
    description="Update all fields of an existing recipe by ID.",
    tags=["Recipes"],
    response_model=Recipe,
)
def update_recipe(
    recipe_id: int = Path(..., description="The ID of the recipe to update", ge=1),
    payload: RecipeCreate = Body(..., description="New data to replace the existing recipe"),
) -> Recipe:
    """Replace an existing recipe with new values."""
    _ensure_seed()
    existing = _db.get(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")
    now = _now()
    updated = Recipe(
        id=recipe_id,
        created_at=existing.created_at,
        updated_at=now,
        **payload.model_dump(),
    )
    _db[recipe_id] = updated
    return updated


# PUBLIC_INTERFACE
@app.patch(
    "/recipes/{recipe_id}",
    summary="Partially update a recipe",
    description="Partially update fields of an existing recipe by ID.",
    tags=["Recipes"],
    response_model=Recipe,
)
def patch_recipe(
    recipe_id: int = Path(..., description="The ID of the recipe to patch", ge=1),
    payload: RecipeUpdate = Body(..., description="Fields to update on the recipe"),
) -> Recipe:
    """Apply a partial update to an existing recipe."""
    _ensure_seed()
    existing = _db.get(recipe_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Recipe not found")

    data = existing.model_dump()
    for key, value in payload.model_dump(exclude_unset=True).items():
        data[key] = value
    data["updated_at"] = _now()
    updated = Recipe(**data)
    _db[recipe_id] = updated
    return updated


# PUBLIC_INTERFACE
@app.delete(
    "/recipes/{recipe_id}",
    summary="Delete a recipe",
    description="Delete a recipe by its ID.",
    tags=["Recipes"],
    response_model=dict,
)
def delete_recipe(
    recipe_id: int = Path(..., description="The ID of the recipe to delete", ge=1)
) -> dict:
    """Delete a recipe from the store."""
    _ensure_seed()
    if recipe_id not in _db:
        raise HTTPException(status_code=404, detail="Recipe not found")
    del _db[recipe_id]
    return {"status": "deleted", "id": recipe_id}
