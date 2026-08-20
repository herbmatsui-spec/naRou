from PIL import Image

img = Image.open("assets/tiles/tiny_rogue/tilemap_packed.png")
print("tilemap_packed.png size:", img.size)
img2 = Image.open("assets/tiles/tiny_rogue/tilemap.png")
print("tilemap.png size:", img2.size)
