import logging
from src import main as start_program

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    filename="run.log",
    filemode="a",
)

def main() -> None:
    start_program()

if __name__ == "__main__":
    main()