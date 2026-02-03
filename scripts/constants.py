from pathlib import Path

artifacts_dir = Path(__file__).parent.parent / ".artifacts"


if __name__ == "__main__":
    print(artifacts_dir)
