import os
import subprocess
import sys

def main():
    # build paths
    project_root = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(project_root, "src")
    tests_path = os.path.join(src_dir, "tests.py")

    # ensure tests.py exists
    if not os.path.exists(tests_path):
        print(f"Could not find tests.py at: {tests_path}")
        sys.exit(1)

    # command to run
    cmd = [
        sys.executable,
        tests_path,
        "aeric20.xml",
        "-m", "Adult Blue Dragon",
        "-n", "1000",
        "--visualize",
    ]

    print("Running:")
    print(" ".join(cmd))
    print()

    # run command
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
