import inspect
from pathlib import Path

from ml.food_safety import foodkeeper

functions = [
    "get_recommendations",
    "get_foodkeeper_selection",
    "get_confirmed_storage_guidance",
    "get_storage_guidance",
]

for name in functions:
    function = getattr(foodkeeper, name, None)

    print(f"\n{'=' * 60}")
    print(name)

    if function is None:
        print("Function not found.")
        continue

    print("Signature:")
    print(inspect.signature(function))

    print("\nSource:")
    print(inspect.getsource(function))

print("\nConfirmation test file exists:",
      Path("ml/food_safety/test_foodkeeper_confirmation.py").exists())