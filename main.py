import logging
from src import main as start_program


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d %(funcName)s: %(message)s",
    datefmt="%H:%M:%S",
)


def main() -> None:
    start_program()


if __name__ == "__main__":
    main()
