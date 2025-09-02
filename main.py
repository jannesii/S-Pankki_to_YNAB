import logging
from src import main as start_program

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d %(funcName)s: %(message)s",
    datefmt="%d/%m %H:%M:%S",
    filename="run.log",
    filemode="a",
)

# Create console handler
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

# Use the same format as file
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s:%(lineno)d %(funcName)s: %(message)s",
    datefmt="%d/%m %H:%M:%S"
)
console.setFormatter(formatter)

# Add the console handler to the root logger
logging.getLogger().addHandler(console)


def main() -> None:
    start_program()


if __name__ == "__main__":
    main()
