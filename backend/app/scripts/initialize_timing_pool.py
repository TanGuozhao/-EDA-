from __future__ import annotations

from app.timing.challenge_repository import TIMING_CHAPTER_KEY, initialize_timing_challenge_pool


def main() -> None:
    initialize_timing_challenge_pool(TIMING_CHAPTER_KEY)
    print(f"Timing challenge pool initialized for {TIMING_CHAPTER_KEY}.")


if __name__ == "__main__":
    main()

