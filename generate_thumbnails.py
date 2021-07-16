import argparse
import os
from glob import glob
import yaml
import re
import requests
import datetime
import subprocess
from PIL import Image, ImageFont, ImageDraw

parser = argparse.ArgumentParser(description="Generate TwitterCard images from a directory full of Hugo posts. Will not create thumbnails for posts that haven't been edited since last generation (commit date unchanged)")
parser.add_argument("-i", "--input-dir", type=str, required=True,
                    help="top directory for the parsed and generated cook-book recipes")
parser.add_argument("-o", "--output-dir", type=str, required=True,
                    help="top directory for the output (in most cases this is the same as -i)")
parser.add_argument("-serif", "--serif-font", type=str, required=True,
                    help="filepath to the serif font")
parser.add_argument("-sansserif", "--sans-serif-font", type=str, required=True,
                    help="filepath to the sans serif font")

def main():
    args = parser.parse_args()

    # make the output dir if not exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # get all files with .md extension within the input dir
    recipes = [y for x in os.walk(args.input_dir) for y in glob(os.path.join(x[0], "*.md"))]

    serif = args.serif_font
    sansserif = args.sans_serif_font

    for recipe in recipes:
        if "view-all.md" in recipe:
            continue

        # read the existing front matter (if any) and contents
        with open(recipe, "r", encoding="utf-8") as f:
            contents = f.readlines()

        front_matter = get_front_matter(contents)

        if "title" in front_matter:
            page_bundle = os.path.dirname(recipe)
            image = create_thumbnail(front_matter, page_bundle, serif, sansserif)
            write_image(image, recipe, args.output_dir)

def write_image(im: Image.Image, recipe_filename: dict, out_dir: str) -> None:
    """
    Write the Pillow image to the output Page Bundle directory as a PNG with the
    name thumbnail.png.
    """
    basename = os.path.basename(os.path.dirname(recipe_filename))
    im.save(os.path.join(out_dir, basename, "thumbnail.png"), format="png")

def get_front_matter(contents: list[str]) -> dict:
    """
    Get the front matter from a Hugo recipe as a Python dictionary.
    It needs to be in YAML format to be parsable.
    """
    currently_fm = False
    front_matter = []
    for line in contents:
        if line == "---\n":
            currently_fm = not currently_fm
            continue

        if currently_fm:
            front_matter.append(line)

    try:
        parsed = yaml.safe_load("\n".join(front_matter))
    except Exception as e:
        parsed = {}

    return parsed

def create_thumbnail(front_matter: dict, page_bundle: str, serif: str, sansserif: str) -> Image.Image:
    """
    Create an thumbnail Pillow image, load the background image if any (from
    the page bundle directory), create the heading with background (each on
    separate layer, then flattened in order), similarly add metadata and logo.
    """
    im = Image.new("RGB", (1200, 600), (255, 255, 255))

    # load some fonts
    property_key_font = ImageFont.truetype(sansserif, 22)
    property_value_font = ImageFont.truetype(sansserif, 38)

    heading_opts = {
        "font": serif,
        "font_size": 86,
        "top_margin": 64,
        "line_height": 1,
        "left_margin": 40,
        "horizontal_padding": 30,
        "max_width": 1000,
        "max_lines": 3
    }

    draw_bg_in_place(im, front_matter, page_bundle)
    bottom = draw_heading_in_place(im, front_matter, heading_opts)

    metadata_opts = {
        "key_font": sansserif,
        "key_font_size": 22,
        "vertical_padding": 10,
        "value_font": sansserif,
        "value_font_size": 38,
        "top_margin": bottom + 20,
        "left_margin": 40,
        "horizontal_padding": 30,
        "space_between": 50,
        "max_width": 1000
    }

    draw_metadata_in_place(im, front_matter, metadata_opts)
    draw_logo_in_place(im, "static/img/cookbook-horizontal-whitebg.png")

    return im

def draw_bg_in_place(im: Image.Image, front_matter: dict, page_bundle: str) -> None:
    """
    Download, scale, and draw the background (preview) image in place if it exists.
    Done in place.
    """
    if "previewimage" in front_matter:
        try:
            if front_matter["previewimage"][:7] in ["https:/", "http://"]:
                bg = Image.open(requests.get(front_matter["previewimage"], stream=True).raw)
            else:
                # load file locally
                bg = Image.open(os.path.join(page_bundle, front_matter["previewimage"]))
            # Resize to fill.
            if bg.size[0] < 1200:
                bg = bg.resize((1200, int(1200/bg.size[0])*bg.size[1]), Image.ANTIALIAS)
            if bg.size[1] < 600:
                bg = bg.resize((int(600/bg.size[1])*bg.size[0], 600), Image.ANTIALIAS)

            im.paste(bg)
        except Exception as e:
            print(e)
            pass


def draw_heading_in_place(im: Image.Image, front_matter: dict, heading_opts: dict) -> int:
    """
    Draw the heading and return the y-coordinate of the bottom-most box boundary.
    """
    # Load the font
    heading_font = ImageFont.truetype(heading_opts["font"], heading_opts["font_size"])
    # Calculate the max vertical height of this font (some fonts are weird)
    heading_font_vert = heading_font.getsize("lgy1")[1]

    # Create the boxes and text layers, both fully transparent
    box_layer = Image.new("RGBA", (1200, 600), (255, 255, 255, 0))
    text_layer = Image.new("RGBA", (1200, 600), (255, 255, 255, 0))
    box_draw = ImageDraw.Draw(box_layer, "RGBA")
    text_draw = ImageDraw.Draw(text_layer, "RGBA")

    # Put newlines in the heading at appropriate places.
    heading_lines = get_wrapped_text(front_matter["title"], heading_font, heading_opts["max_width"], heading_opts["max_lines"])

    # Draw all the background boxes in its own layer, and all the text in its own
    # layer.
    prev_bottom = heading_opts["top_margin"]
    return_value = prev_bottom
    for i, heading_line in enumerate(heading_lines):
        # Get the estimated bounds of the text
        bounds = heading_font.getsize(heading_line)

        # Decide on where the boxes will be laid out. The following diagram
        # shows where each value corresponds to. Line height is not shown but
        # corresponds to the part below and above Text, within the box.
        #
        #                             top margin
        # <left margin> ---------------------------------------
        # <left margin> | <hor.padding>  Text   <hor.padding> |
        # <left margin> ---------------------------------------
        left_edge = heading_opts["left_margin"]
        right_edge = heading_opts["left_margin"] + heading_opts["horizontal_padding"]*2 + bounds[0]
        top_edge = prev_bottom
        bottom_edge = prev_bottom + heading_font_vert
        prev_bottom = prev_bottom + heading_font_vert * heading_opts["line_height"]
        # set the return value as the bottom of the background box (never will overlap text)
        return_value = bottom_edge

        corner_top_left = (left_edge, top_edge)
        corner_top_right = (right_edge, top_edge)
        corner_bottom_right = (right_edge, bottom_edge)
        corner_bottom_left = (left_edge, bottom_edge)
        # Draw the box as brown, and the text as default (white)
        box_draw.polygon([corner_top_left, corner_top_right, corner_bottom_right, corner_bottom_left], (74, 54, 47))
        text_draw.text((left_edge + heading_opts["horizontal_padding"], top_edge), heading_line, font=heading_font)

    # Lower the opacity of all solids in the box layer before merging. This is
    # done post-loop because otherwise overlapping transparent boxes introduce
    # some darker-than-other areas in the result -- undesirable.
    pixdata = box_layer.load()
    for y in range(600):
        for x in range(1200):
            if pixdata[x, y][3] == 255:
                # Tuple unpacking is clunky, smh.
                pixdata[x, y] = (pixdata[x, y][0], pixdata[x, y][1], pixdata[x, y][2], int(255*0.78))

    im.paste(box_layer, (0,0), box_layer)
    im.paste(text_layer, (0,0), text_layer)

    return return_value

def get_wrapped_text(text: str, font: ImageFont.ImageFont, line_length: int, max_lines: int) -> list[str]:
    """
    Courtesy of StackOverflow.com/questions/8257147
    """
    lines = [""]
    for word in text.split():
        # Hypothesise that the last line also contained this word
        line = f"{lines[-1]} {word}".strip()
        # If the hypothetical line is still short, replace the last line with it
        if font.getlength(line) <= line_length:
            lines[-1] = line
        # Otherwise, create a new line and put the hypothetical line there
        else:
            if len(lines) == max_lines:
                lines[-1] = lines[-1] + "..."
                break
            else:
                lines.append(word)
    return lines

def draw_metadata_in_place(im: Image.Image, front_matter: dict, metadata_opts: dict) -> None:
    """
    Draw the difficulty and meal type metadata, with dynamically calculated
    position. The methodology for calculation is to take the label and the
    content, and find the longest of them to calculate next item position or
    overflow.
    """
    difficulty = front_matter["difficulties"]
    meal = front_matter["meals"]

    # Load the fonts
    key_font = ImageFont.truetype(metadata_opts["key_font"], metadata_opts["key_font_size"])
    value_font = ImageFont.truetype(metadata_opts["value_font"], metadata_opts["value_font_size"])
    # Calculate the max vertical height of the fonts (some fonts are weird)
    key_font_vert = key_font.getsize("lgy1")[1]
    value_font_vert = value_font.getsize("lgy1")[1]

    # Create the boxes and text layers, both fully transparent
    box_layer = Image.new("RGBA", (1200, 600), (255, 255, 255, 0))
    text_layer = Image.new("RGBA", (1200, 600), (255, 255, 255, 0))
    box_draw = ImageDraw.Draw(box_layer, "RGBA")
    text_draw = ImageDraw.Draw(text_layer, "RGBA")

    # Get the estimated bounds of the text
    difficulty_key_bounds = key_font.getsize("DIFFICULTY")
    difficulty_value_bounds = value_font.getsize(difficulty)
    difficulty_max_width = max(difficulty_key_bounds[0], difficulty_value_bounds[0])
    meal_key_bounds = key_font.getsize("MEAL")
    meal_value_bounds = value_font.getsize(meal)
    meal_max_width = max(meal_key_bounds[0], meal_value_bounds[0])

    inner_box_width = difficulty_max_width + metadata_opts["space_between"] + meal_max_width

    left_edge = metadata_opts["left_margin"]
    top_edge = metadata_opts["top_margin"]
    right_edge = metadata_opts["left_margin"] + inner_box_width + metadata_opts["horizontal_padding"]*2
    bottom_edge = top_edge + key_font_vert + value_font_vert + metadata_opts["vertical_padding"]*2

    corner_top_left = (left_edge, top_edge)
    corner_top_right = (right_edge, top_edge)
    corner_bottom_right = (right_edge, bottom_edge)
    corner_bottom_left = (left_edge, bottom_edge)

    # Draw the box as brown
    box_draw.polygon([corner_top_left, corner_top_right, corner_bottom_right, corner_bottom_left], (74, 54, 47))

    # Lower the opacity of all solids in the box layer before merging.
    pixdata = box_layer.load()
    for y in range(600):
        for x in range(1200):
            if pixdata[x, y][3] == 255:
                # Tuple unpacking is clunky, smh.
                pixdata[x, y] = (pixdata[x, y][0], pixdata[x, y][1], pixdata[x, y][2], int(255*0.78))

    im.paste(box_layer, (0,0), box_layer)

    # Draw the labels
    text_draw.text((left_edge + metadata_opts["horizontal_padding"], top_edge + metadata_opts["vertical_padding"]), "DIFFICULTY", font=key_font)
    text_draw.text((left_edge + metadata_opts["horizontal_padding"] + difficulty_max_width + metadata_opts["space_between"], top_edge + metadata_opts["vertical_padding"]), "MEAL", font=key_font)

    # Draw the values
    text_draw.text((left_edge + metadata_opts["horizontal_padding"], top_edge +  + metadata_opts["vertical_padding"] + key_font_vert), difficulty, font=value_font)
    text_draw.text((left_edge + metadata_opts["horizontal_padding"] + difficulty_max_width + metadata_opts["space_between"], top_edge +  + metadata_opts["vertical_padding"] + key_font_vert), meal, font=value_font)

    im.paste(text_layer, (0,0), text_layer)

def draw_logo_in_place(im: Image.Image, logo_path: str) -> None:
    """
    Draw the Cookbook logo at the bottom right corner.
    """
    logo = Image.open(logo_path)
    logo = logo.resize((322, 51), Image.ANTIALIAS)
    im.paste(logo, (1200 - 322 - 50, 600 - 51 - 50), logo)

if __name__ == "__main__":
    main()
