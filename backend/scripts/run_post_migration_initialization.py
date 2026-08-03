from app.scripts.initialize_timing_pool import main as initialize_timing_pool
from app.scripts.seed_dev_data import main as seed_dev_data


def main() -> None:
    seed_dev_data()
    initialize_timing_pool()


if __name__ == "__main__":
    main()
