from __future__ import annotations

from pathlib import Path
from urllib.request import urlretrieve


MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = Path(__file__).with_name("models") / "hand_landmarker.task"


def main() -> None:
    MODEL_PATH.parent.mkdir(exist_ok=True)
    print("Baixando modelo da mao...")
    urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"Modelo salvo em: {MODEL_PATH}")


if __name__ == "__main__":
    main()
