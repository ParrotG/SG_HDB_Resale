"""Create a dark-background presentation variant of the town premium map."""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "figures" / "06_town_premium_maps.png"
OUTPUT = ROOT / "figures" / "06_town_premium_maps_dark.png"

DARK = np.array([23, 50, 56], dtype=np.float32)
LIGHT = np.array([244, 240, 232], dtype=np.float32)
ORIGINAL_TEXT = 38


def recolor_grayscale_text(
    original: np.ndarray,
    result: np.ndarray,
    box: tuple[int, int, int, int],
) -> None:
    """Reverse dark antialiased text to light text inside a known text region."""
    left, top, right, bottom = box
    region = original[top:bottom, left:right, :3]
    target = result[top:bottom, left:right, :3]
    grayscale = np.ptp(region.astype(int), axis=2) <= 3
    value = region.mean(axis=2)
    alpha = np.clip((255 - value) / (255 - ORIGINAL_TEXT), 0, 1)
    replacement = (1 - alpha[..., None]) * DARK + alpha[..., None] * LIGHT
    target[grayscale] = replacement[grayscale].astype(np.uint8)


def main() -> None:
    image = Image.open(SOURCE).convert("RGBA")
    original = np.asarray(image).copy()
    result = original.copy()
    height, width = original.shape[:2]

    white = np.all(original[:, :, :3] == 255, axis=2)
    border_seed = np.zeros_like(white)
    border_seed[[0, -1], :] = white[[0, -1], :]
    border_seed[:, [0, -1]] = white[:, [0, -1]]
    background = ndimage.binary_propagation(border_seed, mask=white)
    bar_top, bar_bottom = int(.018 * height), int(.983 * height)
    for left, right in [(.4285, .4457), (.9371, .9538)]:
        background[bar_top:bar_bottom, int(left * width):int(right * width)] = False
    result[background, :3] = DARK.astype(np.uint8)

    text_regions = [
        (int(.06 * width), int(.02 * height), int(.40 * width), int(.10 * height)),
        (int(.57 * width), int(.02 * height), int(.90 * width), int(.10 * height)),
        (int(.448 * width), 0, int(.50 * width), height),
        (int(.956 * width), 0, width, height),
    ]
    for region in text_regions:
        recolor_grayscale_text(original, result, region)

    Image.fromarray(result, mode="RGBA").save(OUTPUT)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
