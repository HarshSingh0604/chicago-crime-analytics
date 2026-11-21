# pipeline.py
# Runs the complete Chicago Crime processing pipeline:
# Use Case 1 -> Use Case 2 -> Use Case 3 -> Use Case 4

from pathlib import Path
import subprocess
import sys


# Project root = folder containing this pipeline.py
BASE_DIR = Path(__file__).resolve().parent


USE_CASES = [
    ("Use Case 1", "1.py"),
    ("Use Case 2", "2.py"),
    ("Use Case 3", "3.py"),
    ("Use Case 4", "4.py"),
]


def run_pipeline():
    print("=" * 60)
    print("CHICAGO CRIME ANALYTICS - FULL PIPELINE")
    print("=" * 60)

    for name, filename in USE_CASES:

        script_path = BASE_DIR / filename

        if not script_path.exists():
            raise FileNotFoundError(
                f"{name} file not found: {script_path}"
            )

        print("\n" + "-" * 60)
        print(f"RUNNING {name}: {filename}")
        print("-" * 60)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"{name} failed with exit code "
                f"{result.returncode}."
            )

        print(f"\n{name} completed successfully.")

    print("\n" + "=" * 60)
    print("FULL PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print("\nPIPELINE FAILED")
        print(f"Error: {e}")
        raise