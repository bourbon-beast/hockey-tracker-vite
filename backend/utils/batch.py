import logging
from firebase_admin import firestore
import os

logger = logging.getLogger(__name__)

def is_dry_run():
    """Check if we're in dry run mode."""
    return os.environ.get('DRY_RUN', '').lower() in ('true', '1', 't')

def batch_write_to_firestore(db, items, collection_name, transform_func=None, batch_size=400):
    """
    Write items to Firestore in batches to reduce costs and improve performance.

    Args:
        db: Firestore client
        items: List of items to write
        collection_name: Firestore collection to write to
        transform_func: Optional function to transform each item before writing
        batch_size: Maximum number of operations per batch (Firestore limit is 500)

    Returns:
        Tuple of (creates, updates) counts
    """
    if is_dry_run():
        logger.info(f"DRY RUN: Would write {len(items)} items to {collection_name}")
        return 0, 0

    batch = db.batch()
    count = 0
    creates = 0
    updates = 0

    for item in items:
        # Apply transformation if provided
        if transform_func:
            item = transform_func(item)

        # Get document ID
        doc_id = item.get('id')
        if not doc_id:
            logger.warning(f"Item missing ID, skipping: {item}")
            continue

        doc_ref = db.collection(collection_name).document(doc_id)

        # Check if document exists to count creates vs updates
        doc = doc_ref.get()
        if doc.exists:
            # Update - don't overwrite created_at
            if 'created_at' in doc.to_dict() and 'created_at' not in item:
                item['created_at'] = doc.to_dict()['created_at']

            batch.update(doc_ref, item)
            updates += 1
        else:
            # Create
            if 'created_at' not in item:
                item['created_at'] = firestore.SERVER_TIMESTAMP

            batch.set(doc_ref, item)
            creates += 1

        count += 1

        # Commit when batch size is reached
        if count >= batch_size:
            batch.commit()
            logger.info(f"Committed batch of {count} to {collection_name}")
            batch = db.batch()
            count = 0

    # Commit any remaining items
    if count > 0:
        batch.commit()
        logger.info(f"Committed final batch of {count} to {collection_name}")

    return creates, updates