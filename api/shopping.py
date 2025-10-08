"""
Shopping list management API endpoints.

This module provides REST API endpoints for shopping list operations,
including creation, management, and item manipulation.
"""

import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from adapters.db import Database, SQLiteShoppingListRepository
from domain.entities import ShoppingItem, ShoppingList

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/shopping", tags=["shopping"])


def serialize_shopping_list(shopping_list) -> dict:
    """Serialize ShoppingList object to dictionary."""
    return {
        "id": shopping_list.id,
        "thread_id": getattr(shopping_list, "thread_id", None),
        "items": (
            [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "category": getattr(item, "category", None),
                    "purchased": getattr(item, "purchased", False),
                }
                for item in shopping_list.items
            ]
            if shopping_list.items
            else []
        ),
        "created_at": getattr(shopping_list, "created_at", None),
        "updated_at": getattr(shopping_list, "updated_at", None),
    }


def validate_thread_id(thread_id: str) -> str:
    """Validate thread_id format."""
    if not re.match(r"^[a-zA-Z0-9_-]{3,64}$", thread_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid thread_id format. Must be 3-64 characters, "
            "alphanumeric, underscore, or dash only.",
        )
    return thread_id


def validate_shopping_list_size(items: list, max_items: int = 100) -> None:
    """Validate shopping list size."""
    if len(items) > max_items:
        raise HTTPException(
            status_code=400,
            detail=f"Shopping list cannot exceed {max_items} items. "
            f"Current: {len(items)}",
        )


# Global database instance
db = Database()
shopping_repo = SQLiteShoppingListRepository(db)


@router.get(
    "/lists",
    response_model=Dict[str, Any],
    summary="Get shopping lists",
    description="Get all shopping lists for a specific thread",
)
async def get_shopping_lists(
    thread_id: str = Depends(validate_thread_id),
) -> Dict[str, Any]:
    """
    Get all shopping lists for a specific thread.

    Returns a list of shopping lists associated with the given thread.
    """
    try:
        logger.info(f"Getting shopping lists for thread: {thread_id}")

        # Get lists for thread
        lists = shopping_repo.get_by_thread_id(thread_id)

        # Handle single list vs list of lists
        if isinstance(lists, list):
            lists_data = [
                serialize_shopping_list(shopping_list)
                for shopping_list in lists
            ]
        else:
            lists_data = [serialize_shopping_list(lists)] if lists else []

        return {
            "lists": lists_data,
            "total": len(lists_data),
            "thread_id": thread_id,
        }

    except Exception as e:
        logger.error(f"Error getting shopping lists: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get shopping lists: {str(e)}"
        )


@router.post(
    "/lists",
    response_model=Dict[str, Any],
    summary="Create shopping list",
    description="Create a new shopping list for a thread",
)
async def create_shopping_list(
    thread_id: str = Depends(validate_thread_id),
    name: Optional[str] = Query(
        None, description="Optional name for the list"
    ),
) -> Dict[str, Any]:
    """
    Create a new shopping list.

    Creates a new shopping list for the specified thread.
    """
    try:
        logger.info(f"Creating shopping list for thread: {thread_id}")

        # Create shopping list
        shopping_list = ShoppingList(items=[])
        if name:
            shopping_list.name = name

        # Save to database
        created_list = shopping_repo.create(shopping_list, thread_id)

        return {
            "list": serialize_shopping_list(created_list),
            "status": "created",
            "message": "Shopping list created successfully",
        }

    except Exception as e:
        logger.error(f"Error creating shopping list: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create shopping list: {str(e)}"
        )


@router.get(
    "/lists/{list_id}",
    response_model=Dict[str, Any],
    summary="Get shopping list by ID",
    description="Get a specific shopping list by its ID",
)
async def get_shopping_list(list_id: int) -> Dict[str, Any]:
    """
    Get a specific shopping list by ID.

    Returns the complete shopping list information including all items.
    """
    try:
        logger.info(f"Getting shopping list with ID: {list_id}")

        shopping_list = shopping_repo.get_by_id(list_id)
        if not shopping_list:
            raise HTTPException(
                status_code=404,
                detail=f"Shopping list with ID {list_id} not found",
            )

        return {
            "list": serialize_shopping_list(shopping_list),
            "status": "success",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shopping list {list_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get shopping list: {str(e)}"
        )


@router.post(
    "/lists/{list_id}/items",
    response_model=Dict[str, Any],
    summary="Add item to shopping list",
    description="Add a new item to an existing shopping list",
)
async def add_item_to_list(
    list_id: int, item_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Add an item to a shopping list.

    Adds a new item to the specified shopping list.
    """
    try:
        logger.info(f"Adding item to shopping list {list_id}")

        # Validate required fields
        if "name" not in item_data:
            raise HTTPException(
                status_code=400, detail="Missing required field: name"
            )

        # Get existing list
        shopping_list = shopping_repo.get_by_id(list_id)
        if not shopping_list:
            raise HTTPException(
                status_code=404,
                detail=f"Shopping list with ID {list_id} not found",
            )

        # Create new item
        item = ShoppingItem(
            name=item_data["name"],
            quantity=item_data.get("quantity", "1"),
            unit=item_data.get("unit", ""),
            category=item_data.get("category"),
            purchased=item_data.get("purchased", False),
        )

        # Validate list size before adding
        validate_shopping_list_size(shopping_list.items + [item])

        # Add item to list
        shopping_list.items.append(item)

        # Update in database
        updated_list = shopping_repo.update(
            shopping_list, shopping_list.thread_id
        )

        return {
            "list": serialize_shopping_list(updated_list),
            "status": "updated",
            "message": "Item added successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding item to list {list_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to add item: {str(e)}"
        )


@router.put(
    "/lists/{list_id}/items/{item_index}",
    response_model=Dict[str, Any],
    summary="Update shopping list item",
    description="Update an existing item in a shopping list",
)
async def update_list_item(
    list_id: int, item_index: int, item_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an item in a shopping list.

    Updates the specified item in the shopping list.
    """
    try:
        logger.info(f"Updating item {item_index} in shopping list {list_id}")

        # Get existing list
        shopping_list = shopping_repo.get_by_id(list_id)
        if not shopping_list:
            raise HTTPException(
                status_code=404,
                detail=f"Shopping list with ID {list_id} not found",
            )

        # Check item index
        if item_index >= len(shopping_list.items):
            raise HTTPException(
                status_code=404, detail=f"Item at index {item_index} not found"
            )

        # Update item
        item = shopping_list.items[item_index]
        if "name" in item_data:
            item.name = item_data["name"]
        if "amount" in item_data:
            item.amount = item_data["amount"]
        if "unit" in item_data:
            item.unit = item_data["unit"]
        if "notes" in item_data:
            item.notes = item_data["notes"]
        if "purchased" in item_data:
            item.purchased = item_data["purchased"]

        # Update in database
        updated_list = shopping_repo.update(
            shopping_list, shopping_list.thread_id
        )

        return {
            "list": serialize_shopping_list(updated_list),
            "status": "updated",
            "message": "Item updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating item in list {list_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update item: {str(e)}"
        )


@router.delete(
    "/lists/{list_id}/items/{item_index}",
    response_model=Dict[str, Any],
    summary="Remove item from shopping list",
    description="Remove an item from a shopping list",
)
async def remove_list_item(list_id: int, item_index: int) -> Dict[str, Any]:
    """
    Remove an item from a shopping list.

    Removes the specified item from the shopping list.
    """
    try:
        logger.info(f"Removing item {item_index} from shopping list {list_id}")

        # Get existing list
        shopping_list = shopping_repo.get_by_id(list_id)
        if not shopping_list:
            raise HTTPException(
                status_code=404,
                detail=f"Shopping list with ID {list_id} not found",
            )

        # Check item index
        if item_index >= len(shopping_list.items):
            raise HTTPException(
                status_code=404, detail=f"Item at index {item_index} not found"
            )

        # Remove item
        removed_item = shopping_list.items.pop(item_index)

        # Update in database
        updated_list = shopping_repo.update(
            shopping_list, shopping_list.thread_id
        )

        return {
            "list": serialize_shopping_list(updated_list),
            "removed_item": {
                "name": removed_item.name,
                "quantity": removed_item.quantity,
                "unit": removed_item.unit,
                "category": getattr(removed_item, "category", None),
                "purchased": getattr(removed_item, "purchased", False),
            },
            "status": "updated",
            "message": "Item removed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item from list {list_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to remove item: {str(e)}"
        )


@router.delete(
    "/lists/{list_id}",
    response_model=Dict[str, Any],
    summary="Delete shopping list",
    description="Delete a shopping list completely",
)
async def delete_shopping_list(list_id: int) -> Dict[str, Any]:
    """
    Delete a shopping list.

    Permanently deletes the specified shopping list.
    """
    try:
        logger.info(f"Deleting shopping list {list_id}")

        # Check if list exists
        shopping_list = shopping_repo.get_by_id(list_id)
        if not shopping_list:
            raise HTTPException(
                status_code=404,
                detail=f"Shopping list with ID {list_id} not found",
            )

        # Delete from database
        shopping_repo.delete(list_id)

        return {
            "status": "deleted",
            "message": f"Shopping list {list_id} deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting shopping list {list_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete shopping list: {str(e)}"
        )
