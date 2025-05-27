from PIL import Image, ImageDraw, ImageFont
import string

def convert_ttf_to_bitmap(font_path, size=8):
    font = ImageFont.truetype(font_path, size)
    characters = string.ascii_uppercase + string.ascii_lowercase + string.digits + string.punctuation + " " + "°"
    font_dict = {}
    
    for char in characters:
        img = Image.new("1", (size, size), 0)
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), char, font=font, fill=1)
        
        bitmap = []
        for y in range(size):
            row = 0
            for x in range(size):
                pixel = img.getpixel((x, y))
                row |= (pixel << (size - 1 - x))
            bitmap.append(row)
        
        font_dict[char] = bitmap
    
    return font_dict

def transpose_bitmap(bitmap, width=7, height=7):
    """ Transpone el bitmap intercambiando filas por columnas y corrige el espejo """
    transposed = [0] * width
    for col in range(width):
        for row in range(height):
            bit = (bitmap[row] >> col) & 1  # Extraer el bit en la posición actual
            transposed[width - 1 - col] |= bit << row  # Invertimos las columnas
    return transposed


# Uso
ttf_path = "/home/pi/sensors/fuentes/calibri.ttf"  # Reemplaza con la ruta real
dictionary = convert_ttf_to_bitmap(ttf_path, size=32)


#for char, bitmap in dictionary.items():
#   print(f'"{char}": [{", ".join(hex(val) for val in transpose_bitmap(bitmap))}],')

for char, bitmap in dictionary.items():
    print(f'"{char}": [{", ".join(hex(val) for val in transpose_bitmap(bitmap, width=32, height=32))}],')