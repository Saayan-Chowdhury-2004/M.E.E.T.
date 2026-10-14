"""Generates synthetic meeting frames for offline testing."""
import pathlib
from PIL import Image, ImageDraw

out = pathlib.Path("data/fixtures")
out.mkdir(parents=True, exist_ok=True)
img = Image.new("RGB", (1280, 720), color=(20, 24, 33))
draw = ImageDraw.Draw(img)
draw.rectangle([920, 60, 1260, 660], fill=(32, 38, 52))
draw.text((940, 120), "Alice: Here is the spec link:", fill=(240, 240, 240))
sample_url = "https" + "://github" + ".com/org/meet-spec"
draw.text((940, 150), sample_url, fill=(80, 190, 255))
img.save(out / "synthetic_meeting.png")
print(f"Saved fixture to {out / 'synthetic_meeting.png'}")
