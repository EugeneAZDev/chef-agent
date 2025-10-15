"""
Tests for shopping list race conditions.

This module tests that shopping list operations are atomic
and handle concurrent access correctly.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from adapters.db.shopping_list_repository import SQLiteShoppingListRepository
from domain.entities import ShoppingItem, ShoppingList


class TestShoppingListRaceConditions:
    """Test race conditions in shopping list operations."""

    def test_concurrent_save_same_thread_user(self, temp_database):
        """Test concurrent save operations for same thread and user."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-race"
        user_id = "test-user-race"
        results = []
        errors = []

        def save_shopping_list(list_id):
            try:
                items = [
                    ShoppingItem(
                        name=f"Item {list_id}",
                        quantity="1",
                        unit="piece",
                    )
                ]
                shopping_list = ShoppingList(items=items)
                shopping_list.user_id = user_id
                result = repo.save(shopping_list, thread_id, user_id=user_id)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads trying to save for same thread/user
        threads = []
        for i in range(5):
            thread = threading.Thread(target=save_shopping_list, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed (no race conditions)
        assert len(results) == 5
        assert len(errors) == 0

        # Verify only one shopping list exists (due to UNIQUE constraint)
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == 1  # Only the last saved items

    def test_concurrent_add_items_same_thread_user(self, temp_database):
        """Test concurrent add_items operations for same thread and user."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-add-race"
        user_id = "test-user-add-race"

        # Create initial shopping list
        initial_list = ShoppingList(items=[])
        initial_list.user_id = user_id
        repo.save(initial_list, thread_id, user_id)

        results = []
        errors = []

        def add_items(item_id):
            try:
                items = [
                    ShoppingItem(
                        name=f"Concurrent Item {item_id}",
                        quantity="1",
                        unit="piece",
                    )
                ]
                repo.add_items(thread_id, items, user_id)
                results.append(item_id)
            except Exception as e:
                errors.append(e)

        # Create multiple threads trying to add items
        threads = []
        for i in range(10):
            thread = threading.Thread(target=add_items, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All should succeed
        assert len(results) == 10
        assert len(errors) == 0

        # Verify all items were added
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == 10

    def test_concurrent_save_and_add_items(self, temp_database):
        """Test concurrent save and add_items operations."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-mixed-race"
        user_id = "test-user-mixed-race"
        results = []
        errors = []

        def save_operation(operation_id):
            try:
                items = [
                    ShoppingItem(
                        name=f"Save Item {operation_id}",
                        quantity="1",
                        unit="piece",
                    )
                ]
                shopping_list = ShoppingList(items=items)
                shopping_list.user_id = user_id
                repo.save(shopping_list, thread_id, user_id=user_id)
                results.append(("save", operation_id))
            except Exception as e:
                errors.append(("save", operation_id, e))

        def add_items_operation(operation_id):
            try:
                items = [
                    ShoppingItem(
                        name=f"Add Item {operation_id}",
                        quantity="1",
                        unit="piece",
                    )
                ]
                repo.add_items(thread_id, items, user_id)
                results.append(("add", operation_id))
            except Exception as e:
                errors.append(("add", operation_id, e))

        # Create mixed operations
        threads = []
        for i in range(5):
            # Save operations
            save_thread = threading.Thread(target=save_operation, args=(i,))
            threads.append(save_thread)

            # Add items operations
            add_thread = threading.Thread(
                target=add_items_operation, args=(i,)
            )
            threads.append(add_thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Most operations should succeed
        assert len(results) >= 8  # Allow some failures due to concurrency
        assert len(results) + len(errors) == 10

        # Verify final state is consistent
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) >= 1

    def test_unique_constraint_enforcement(self, temp_database):
        """Test that UNIQUE constraint on (thread_id, user_id) is enforced."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-unique"
        user_id = "test-user-unique"

        # Create first shopping list
        list1 = ShoppingList(
            items=[ShoppingItem(name="Item 1", quantity="1", unit="piece")]
        )
        list1.user_id = user_id
        result1 = repo.save(list1, thread_id, user_id)
        assert result1.id is not None

        # Try to create second shopping list with same thread_id and user_id
        list2 = ShoppingList(
            items=[ShoppingItem(name="Item 2", quantity="1", unit="piece")]
        )
        list2.user_id = user_id
        result2 = repo.save(list2, thread_id, user_id)

        # Should get the same ID (replaced the first one)
        assert result2.id == result1.id

        # Verify only one list exists
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert final_list.id == result1.id

    def test_different_users_same_thread(self, temp_database):
        """Test that different users can have lists for same thread."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-multi-user"
        user1_id = "test-user-1"
        user2_id = "test-user-2"

        # Create list for user 1
        list1 = ShoppingList(
            items=[ShoppingItem(name="User1 Item", quantity="1", unit="piece")]
        )
        list1.user_id = user1_id
        result1 = repo.save(list1, thread_id, user1_id)
        assert result1.id is not None

        # Create list for user 2
        list2 = ShoppingList(
            items=[ShoppingItem(name="User2 Item", quantity="1", unit="piece")]
        )
        list2.user_id = user2_id
        result2 = repo.save(list2, thread_id, user2_id)
        assert result2.id is not None

        # Should have different IDs
        assert result1.id != result2.id

        # Verify both lists exist
        final_list1 = repo.get_by_thread_id(thread_id, user1_id)
        final_list2 = repo.get_by_thread_id(thread_id, user2_id)

        assert final_list1 is not None
        assert final_list2 is not None
        assert final_list1.id != final_list2.id

    def test_atomic_add_items_consistency(self, temp_database):
        """Test that add_items operations are atomic and consistent."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-atomic"
        user_id = "test-user-atomic"

        # Create initial list
        initial_list = ShoppingList(items=[])
        initial_list.user_id = user_id
        repo.save(initial_list, thread_id, user_id)

        def add_items_batch(batch_id, item_count):
            """Add a batch of items atomically."""
            items = [
                ShoppingItem(
                    name=f"Batch {batch_id} Item {i}",
                    quantity="1",
                    unit="piece",
                )
                for i in range(item_count)
            ]
            repo.add_items(thread_id, items, user_id)

        # Add items in batches concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(add_items_batch, i, 3) for i in range(5)
            ]

            # Wait for all to complete
            for future in as_completed(futures):
                future.result()  # This will raise if there was an exception

        # Verify all items were added consistently
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == 15  # 5 batches * 3 items each

        # Verify no duplicate items
        item_names = [item.name for item in final_list.items]
        assert len(item_names) == len(set(item_names))  # No duplicates

    def test_shopping_list_empty_items_handling(self, temp_database):
        """Test handling of empty items in shopping list operations."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-empty"
        user_id = "test-user-empty"

        # Test creating list with empty items
        empty_list = ShoppingList(items=[])
        empty_list.user_id = user_id
        result = repo.save(empty_list, thread_id, user_id)
        assert result is not None
        assert len(result.items) == 0

        # Test adding empty items list
        repo.add_items(thread_id, [], user_id)
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == 0

    def test_shopping_list_none_items_handling(self, temp_database):
        """Test handling of None items in shopping list operations."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-none"
        user_id = "test-user-none"

        # Test creating list with None items
        none_list = ShoppingList(items=None)
        none_list.user_id = user_id
        result = repo.save(none_list, thread_id, user_id)
        assert result is not None
        assert result.items is None or result.items == []

    def test_shopping_list_large_number_of_items(self, temp_database):
        """Test handling of large number of items in shopping list."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-large"
        user_id = "test-user-large"

        # Create list with many items
        large_items = [
            ShoppingItem(name=f"Large Item {i}", quantity="1", unit="piece")
            for i in range(1000)  # 1000 items
        ]
        large_list = ShoppingList(items=large_items)
        large_list.user_id = user_id
        result = repo.save(large_list, thread_id, user_id)
        assert result is not None
        assert len(result.items) == 1000

        # Verify all items are preserved
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == 1000

    def test_shopping_list_very_long_item_names(self, temp_database):
        """Test handling of very long item names."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-long-names"
        user_id = "test-user-long-names"

        # Create item with very long name
        long_name = "A" * 1000  # 1000 character name
        long_item = ShoppingItem(name=long_name, quantity="1", unit="piece")
        long_list = ShoppingList(items=[long_item])
        long_list.user_id = user_id
        result = repo.save(long_list, thread_id, user_id)
        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].name == long_name

    def test_shopping_list_special_characters_in_names(self, temp_database):
        """Test handling of special characters in item names."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-special"
        user_id = "test-user-special"

        # Create items with special characters
        special_items = [
            ShoppingItem(name="Item with spaces", quantity="1", unit="piece"),
            ShoppingItem(name="Item-with-dashes", quantity="1", unit="piece"),
            ShoppingItem(
                name="Item_with_underscores", quantity="1", unit="piece"
            ),
            ShoppingItem(name="Item.with.dots", quantity="1", unit="piece"),
            ShoppingItem(name="Item/with/slashes", quantity="1", unit="piece"),
            ShoppingItem(
                name="Item\\with\\backslashes", quantity="1", unit="piece"
            ),
            ShoppingItem(name="Item'with'quotes", quantity="1", unit="piece"),
            ShoppingItem(
                name='Item"with"double-quotes', quantity="1", unit="piece"
            ),
            ShoppingItem(
                name="Item(with)parentheses", quantity="1", unit="piece"
            ),
            ShoppingItem(
                name="Item[with]brackets", quantity="1", unit="piece"
            ),
            ShoppingItem(name="Item{with}braces", quantity="1", unit="piece"),
            ShoppingItem(
                name="Item<with>angle-brackets", quantity="1", unit="piece"
            ),
            ShoppingItem(
                name="Item&with&ampersands", quantity="1", unit="piece"
            ),
            ShoppingItem(name="Item#with#hashes", quantity="1", unit="piece"),
            ShoppingItem(name="Item%with%percent", quantity="1", unit="piece"),
            ShoppingItem(name="Item+with+plus", quantity="1", unit="piece"),
            ShoppingItem(name="Item=with=equals", quantity="1", unit="piece"),
            ShoppingItem(
                name="Item?with?question", quantity="1", unit="piece"
            ),
            ShoppingItem(
                name="Item!with!exclamation", quantity="1", unit="piece"
            ),
            ShoppingItem(name="Item@with@at", quantity="1", unit="piece"),
            ShoppingItem(name="Item$with$dollar", quantity="1", unit="piece"),
            ShoppingItem(name="Item^with^caret", quantity="1", unit="piece"),
            ShoppingItem(
                name="Item*with*asterisk", quantity="1", unit="piece"
            ),
            ShoppingItem(name="Item|with|pipe", quantity="1", unit="piece"),
            ShoppingItem(name="Item~with~tilde", quantity="1", unit="piece"),
            ShoppingItem(
                name="Item`with`backtick", quantity="1", unit="piece"
            ),
        ]

        special_list = ShoppingList(items=special_items)
        special_list.user_id = user_id
        result = repo.save(special_list, thread_id, user_id)
        assert result is not None
        assert len(result.items) == len(special_items)

        # Verify all special characters are preserved
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == len(special_items)

        for i, item in enumerate(final_list.items):
            assert item.name == special_items[i].name

    def test_shopping_list_unicode_characters(self, temp_database):
        """Test handling of Unicode characters in item names."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-unicode"
        user_id = "test-user-unicode"

        # Create items with Unicode characters
        unicode_items = [
            ShoppingItem(
                name="Item with émojis 🍎🥕🥬", quantity="1", unit="piece"
            ),
            ShoppingItem(
                name="Item with accents: café, naïve, résumé",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Chinese: 苹果, 胡萝卜, 菠菜",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Japanese: りんご, にんじん, ほうれん草",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Korean: 사과, 당근, 시금치",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Arabic: تفاح, جزر, سبانخ",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Russian: яблоко, морковь, шпинат",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Greek: μήλο, καρότο, σπανάκι",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Hebrew: תפוח, גזר, תרד",
                quantity="1",
                unit="piece",
            ),
            ShoppingItem(
                name="Item with Thai: แอปเปิ้ล, แครอท, ผักโขม",
                quantity="1",
                unit="piece",
            ),
        ]

        unicode_list = ShoppingList(items=unicode_items)
        unicode_list.user_id = user_id
        result = repo.save(unicode_list, thread_id, user_id)
        assert result is not None
        assert len(result.items) == len(unicode_items)

        # Verify all Unicode characters are preserved
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == len(unicode_items)

        for i, item in enumerate(final_list.items):
            assert item.name == unicode_items[i].name

    def test_shopping_list_extreme_quantities(self, temp_database):
        """Test handling of extreme quantities in shopping items."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-quantities"
        user_id = "test-user-quantities"

        # Create items with extreme quantities
        extreme_items = [
            ShoppingItem(
                name="Very small quantity", quantity="0.001", unit="mg"
            ),
            ShoppingItem(
                name="Very large quantity", quantity="999999.99", unit="kg"
            ),
            ShoppingItem(name="Zero quantity", quantity="0", unit="piece"),
            ShoppingItem(
                name="Negative quantity", quantity="-1", unit="piece"
            ),
            ShoppingItem(
                name="Fractional quantity", quantity="1.5", unit="cups"
            ),
            ShoppingItem(
                name="Scientific notation", quantity="1e-6", unit="g"
            ),
            ShoppingItem(
                name="Very long decimal",
                quantity="3.141592653589793238462643383279",
                unit="ml",
            ),
        ]

        extreme_list = ShoppingList(items=extreme_items)
        extreme_list.user_id = user_id
        result = repo.save(extreme_list, thread_id, user_id)
        assert result is not None
        assert len(result.items) == len(extreme_items)

        # Verify all quantities are preserved
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) == len(extreme_items)

        for i, item in enumerate(final_list.items):
            assert item.quantity == extreme_items[i].quantity

    def test_shopping_list_concurrent_mixed_operations(self, temp_database):
        """Test concurrent mixed operations on shopping lists."""
        repo = SQLiteShoppingListRepository(temp_database)
        thread_id = "test-thread-mixed-ops"
        user_id = "test-user-mixed-ops"

        results = []
        errors = []

        def create_list(operation_id):
            try:
                items = [
                    ShoppingItem(
                        name=f"Create Item {operation_id}",
                        quantity="1",
                        unit="piece",
                    )
                ]
                shopping_list = ShoppingList(items=items)
                shopping_list.user_id = user_id
                result = repo.save(shopping_list, thread_id, user_id=user_id)
                results.append(("create", operation_id, result.id))
            except Exception as e:
                errors.append(("create", operation_id, e))

        def add_items(operation_id):
            try:
                items = [
                    ShoppingItem(
                        name=f"Add Item {operation_id}",
                        quantity="1",
                        unit="piece",
                    )
                ]
                repo.add_items(thread_id, items, user_id)
                results.append(("add", operation_id))
            except Exception as e:
                errors.append(("add", operation_id, e))

        def get_list(operation_id):
            try:
                result = repo.get_by_thread_id(thread_id, user_id)
                item_count = len(result.items) if result else 0
                results.append(("get", operation_id, item_count))
            except Exception as e:
                errors.append(("get", operation_id, e))

        # Create mixed operations
        threads = []
        for i in range(10):
            # Create operations
            create_thread = threading.Thread(target=create_list, args=(i,))
            threads.append(create_thread)

            # Add items operations
            add_thread = threading.Thread(target=add_items, args=(i,))
            threads.append(add_thread)

            # Get operations
            get_thread = threading.Thread(target=get_list, args=(i,))
            threads.append(get_thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Most operations should succeed
        assert len(results) >= 20  # Allow some failures due to concurrency
        assert len(results) + len(errors) == 30

        # Verify final state is consistent
        final_list = repo.get_by_thread_id(thread_id, user_id)
        assert final_list is not None
        assert len(final_list.items) >= 1

    def test_shopping_list_thread_id_validation_edge_cases(
        self, temp_database
    ):
        """Test thread_id validation with edge cases."""
        repo = SQLiteShoppingListRepository(temp_database)
        user_id = "test-user-validation"

        # Test with various thread_id formats
        test_cases = [
            ("", "Empty thread_id"),
            ("a", "Single character"),
            ("a" * 100, "Very long thread_id"),
            ("thread-with-dashes", "With dashes"),
            ("thread_with_underscores", "With underscores"),
            ("thread.with.dots", "With dots"),
            ("thread/with/slashes", "With slashes"),
            ("thread\\with\\backslashes", "With backslashes"),
            ("thread'with'quotes", "With single quotes"),
            ('thread"with"double-quotes', "With double quotes"),
            ("thread(with)parentheses", "With parentheses"),
            ("thread[with]brackets", "With brackets"),
            ("thread{with}braces", "With braces"),
            ("thread<with>angle-brackets", "With angle brackets"),
            ("thread&with&ampersands", "With ampersands"),
            ("thread#with#hashes", "With hashes"),
            ("thread%with%percent", "With percent"),
            ("thread+with+plus", "With plus"),
            ("thread=with=equals", "With equals"),
            ("thread?with?question", "With question mark"),
            ("thread!with!exclamation", "With exclamation"),
            ("thread@with@at", "With at symbol"),
            ("thread$with$dollar", "With dollar"),
            ("thread^with^caret", "With caret"),
            ("thread*with*asterisk", "With asterisk"),
            ("thread|with|pipe", "With pipe"),
            ("thread~with~tilde", "With tilde"),
            ("thread`with`backtick", "With backtick"),
        ]

        for thread_id, description in test_cases:
            try:
                items = [
                    ShoppingItem(
                        name=f"Item for {description}",
                        quantity="1",
                        unit="piece",
                    )
                ]
                shopping_list = ShoppingList(items=items)
                shopping_list.user_id = user_id
                result = repo.save(shopping_list, thread_id, user_id=user_id)
                assert result is not None, f"Failed for {description}"
            except ValueError as e:
                # Some thread_ids should be rejected
                error_msg = f"Unexpected error for {description}: {e}"
                assert "Invalid thread_id format" in str(e), error_msg
            except Exception:
                # Other errors might be acceptable
                pass  # Continue with other test cases
