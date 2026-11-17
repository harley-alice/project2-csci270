
from ml.food_safety.foodkeeper import load_foodkeeper, get_record_name

records = load_foodkeeper()

print(f"Total products loaded: {len(records)}")

# Show the actual fields available in a FoodKeeper record.
print("\nFOODKEEPER RECORD FIELDS")
for key in records[0].keys():
    print(key)

# Inspect beef, ground beef, and shrimp records.
search_terms = ["beef", "shrimp"]

for term in search_terms:
    print(f"\n{'=' * 50}")
    print(f"RECORDS MATCHING: {term.upper()}")
    print("=" * 50)

    for record in records:
        searchable = " ".join(
            str(record.get(field, ""))
            for field in ["Name", "Name_subtitle", "Keywords"]
        ).lower()

        if term in searchable:
            print(f"\nID: {record.get('ID')}")
            print(f"Name: {get_record_name(record)}")

            # Print every field that might contain storage guidance.
            for key, value in record.items():
                if any(
                    word in key.lower()
                    for word in ["pantry", "refriger", "freeze", "storage"]
                ):
                    print(f"{key}: {value}")
