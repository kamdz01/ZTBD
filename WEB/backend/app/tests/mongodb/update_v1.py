import sys
import json
import time
from pymongo import MongoClient, UpdateOne
from pymongo.errors import DocumentTooLarge


def run_update_test(limit=None):
    client = MongoClient("mongodb://admin:admin@localhost:27017/")
    db = client["ecommerce"]

    print("MongoDB Update Test Started.")
    overall_start_time = time.time()

    total_updated_orders = 0
    total_updated_items = 0
    total_updated_products = 0

    try:
        # 1. Update orders with status 'pending' to 'delivered'
        step_1_start_time = time.time()
        print("Step 1: Updating orders status 'pending' to 'delivered'...")
        orders_result = db.orders.update_many(
            {"order_status": "pending"}, {"$set": {"order_status": "delivered"}}
        )
        total_updated_orders = orders_result.modified_count
        step_1_time = time.time() - step_1_start_time
        print(
            f"Step 1: Updated {total_updated_orders} orders. Time: {step_1_time:.2f}s"
        )

        # --- Process in batches to avoid DocumentTooLarge ---
        batch_size = 1000  # Adjust batch size as needed
        print(f"Using batch size: {batch_size}")

        # 2. Update order_items for orders that are now 'delivered'
        step_2_start_time = time.time()
        print("Step 2: Updating order_items for 'delivered' orders...")

        print("Step 2: Fetching 'delivered' order_ids...")
        delivered_orders_cursor = db.orders.find(
            {"order_status": "delivered"},
            {"order_id": 1, "_id": 0},  # Only fetch order_id
        ).batch_size(
            batch_size
        )  # Apply batch_size to cursor fetching

        all_delivered_order_ids = [doc["order_id"] for doc in delivered_orders_cursor]
        processed_order_ids_count = len(all_delivered_order_ids)
        print(
            f"Step 2: Fetched {processed_order_ids_count} delivered order_ids to process for items."
        )

        batch_num_items = 0
        for i in range(0, processed_order_ids_count, batch_size):
            batch_order_ids = all_delivered_order_ids[i : i + batch_size]
            if not batch_order_ids:
                continue
            batch_num_items += 1
            print(
                f"Step 2: Processing item batch {batch_num_items} (order_ids: {len(batch_order_ids)})..."
            )
            items_result = db.order_items.update_many(
                {"order_id": {"$in": batch_order_ids}},
                {"$set": {"shipping_limit_date": "2025-05-01 23:59:59"}},
            )
            total_updated_items += items_result.modified_count

        step_2_time = time.time() - step_2_start_time
        print(
            f"Step 2: Finished processing items. Updated {total_updated_items} order_items. Time: {step_2_time:.2f}s"
        )

        # 3. Update products linked to 'delivered' orders
        step_3_start_time = time.time()
        print("Step 3: Updating products linked to 'delivered' orders...")

        product_id_pipeline = [
            {
                "$lookup": {
                    "from": "orders",
                    "localField": "order_id",
                    "foreignField": "order_id",
                    "as": "order_info",
                }
            },
            {"$unwind": "$order_info"},
            {"$match": {"order_info.order_status": "delivered"}},
            {"$group": {"_id": "$product_id"}},  # product_id from order_items
            {"$project": {"product_id_from_item": "$_id", "_id": 0}},
        ]

        print(
            "Step 3: Aggregating distinct product_ids from order_items linked to delivered orders..."
        )
        distinct_product_ids_cursor = db.order_items.aggregate(
            product_id_pipeline, allowDiskUse=True
        )

        # These are the product identifiers obtained from order_items.product_id
        product_ids_to_match_in_products = []
        for doc in distinct_product_ids_cursor:
            if doc.get("product_id_from_item"):
                product_ids_to_match_in_products.append(doc["product_id_from_item"])

        processed_source_product_ids_count = len(product_ids_to_match_in_products)
        print(
            f"Step 3: Found {processed_source_product_ids_count} distinct product_id values from order_items."
        )

        batch_num_products = 0
        for i in range(0, processed_source_product_ids_count, batch_size):
            product_ids_batch = product_ids_to_match_in_products[i : i + batch_size]
            if not product_ids_batch:
                continue

            batch_num_products += 1
            print(
                f"Step 3: Processing product batch {batch_num_products} (IDs to match in products: {len(product_ids_batch)})..."
            )

            # ASSUMPTION: The 'product_id_from_item' values are intended to match the '_id' field
            # in the 'products' collection. If your 'products' collection has a different field
            # (e.g., a field named 'product_id') that serves as the unique product identifier and
            # should be matched, change {"_id": ...} to {"your_product_key_field_name": ...}.
            products_result = db.products.update_many(
                {
                    "_id": {"$in": product_ids_batch}
                },  # Matching on _id in products collection
                {"$set": {"product_category_name": "home_appliances"}},
            )
            total_updated_products += products_result.modified_count

        step_3_time = time.time() - step_3_start_time
        print(
            f"Step 3: Updated {total_updated_products} products. Time: {step_3_time:.2f}s"
        )

    except DocumentTooLarge as e:
        print(f"DocumentTooLarge error encountered: {e}. Try reducing batch_size.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        overall_end_time = time.time()
        elapsed_time = overall_end_time - overall_start_time
        client.close()
        print(f"MongoDB Update Test Finished. Total time: {elapsed_time:.2f}s")

    total_updated = total_updated_orders + total_updated_items + total_updated_products
    result = {
        "time": elapsed_time,
        "rows": total_updated,
        "updated_orders": total_updated_orders,
        "updated_order_items": total_updated_items,
        "updated_products": total_updated_products,
    }
    print("Final JSON result:")
    print(json.dumps(result))

    return elapsed_time, total_updated


if __name__ == "__main__":
    limit_arg = None
    if len(sys.argv) > 1:
        try:
            limit_arg = int(sys.argv[1])
        except ValueError:
            print("Invalid limit argument. It should be an integer.")
            sys.exit(1)

    run_update_test(limit_arg)
