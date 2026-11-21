from PIL import Image, ImageDraw

def create_lol_overlay():
    width = 1920
    height = 1080

    # 1. Create transparent RGBA image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Color definitions
    gold_color = (255, 215, 0, 255)       # Gold / Yellow
    dark_gold = (218, 165, 32, 255)       # Darker Accent
    shadow_color = (0, 0, 0, 180)         # Drop shadow
    header_fill = (15, 20, 30, 210)       # Dark semi-transparent fill for header

    # Helper function to draw bordered box with shadow
    def draw_framed_box(box_coords, stroke_w=8):
        x1, y1, x2, y2 = box_coords
        
        # Outer black shadow
        draw.rectangle([x1 - 3, y1 - 3, x2 + 3, y2 + 3], outline=(0, 0, 0, 200), width=stroke_w + 4)
        # Gold main frame
        draw.rectangle([x1, y1, x2, y2], outline=gold_color, width=stroke_w)
        # Inner subtle accent line
        draw.rectangle([x1 + stroke_w, y1 + stroke_w, x2 - stroke_w, y2 - stroke_w], outline=(255, 255, 255, 60), width=2)

    # 1. Top Header / Category Box (X: 510..1410, Y: 50..130)
    header_coords = [510, 50, 1410, 130]
    draw.rectangle(header_coords, fill=header_fill, outline=gold_color, width=5)
    # Header corner accents
    draw.line([510, 50, 540, 50], fill=(255, 255, 255, 255), width=7)
    draw.line([1380, 50, 1410, 50], fill=(255, 255, 255, 255), width=7)

    # 2. Left Champion Box (X: 100..900, Y: 220..770) - 16:9 ratio frame
    left_box = [100, 220, 900, 770]
    draw_framed_box(left_box, stroke_w=8)

    # 3. Right Champion Box (X: 1020..1820, Y: 220..770) - 16:9 ratio frame
    right_box = [1020, 220, 1820, 770]
    draw_framed_box(right_box, stroke_w=8)

    # 4. Center Vertical Divider Line (X: 960, Y: 180..850)
    center_x = 960
    # Black shadow line
    draw.line([center_x + 2, 180, center_x + 2, 850], fill=(0, 0, 0, 180), width=8)
    # Gold main vertical line
    draw.line([center_x, 180, center_x, 850], fill=gold_color, width=6)
    # Top and bottom decorative diamonds/circles on divider line
    draw.ellipse([center_x - 8, 172, center_x + 8, 188], fill=gold_color, outline=(0, 0, 0, 255), width=2)
    draw.ellipse([center_x - 8, 842, center_x + 8, 858], fill=gold_color, outline=(0, 0, 0, 255), width=2)

    # Save PNG
    output_path = r"c:\Users\emrKvn\Desktop\Yazılım\projects\completed\lol-ses-veriler\lol_overlay_template.png"
    img.save(output_path, "PNG")
    print(f"SEFFAF PNG SABLONU OLUSTURULDU: {output_path}")

if __name__ == "__main__":
    create_lol_overlay()
