"""Run directly, or use the packaged calculator.pyz artifact."""

import argparse

from calculator import add, divide, multiply, subtract


def main():
    parser = argparse.ArgumentParser(description="CI/CD lab calculator")
    parser.add_argument("operation", choices=["add", "subtract", "multiply", "divide"])
    parser.add_argument("a", type=float)
    parser.add_argument("b", type=float)
    args = parser.parse_args()
    operations = {"add": add, "subtract": subtract, "multiply": multiply, "divide": divide}
    try:
        result = operations[args.operation](args.a, args.b)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"{result:g}")


if __name__ == "__main__":
    main()
