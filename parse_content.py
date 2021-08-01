import argparse
import os
import shutil
from glob import glob
import subprocess
import yaml
import re

parser = argparse.ArgumentParser(description="Convert the cook-book directory structure to Hugo structure.")
parser.add_argument("-i", "--input-dir", type=str, required=True,
                    help="top directory for the cook-book recipes")
parser.add_argument("-o", "--output-dir", type=str, required=True,
                    help="top directory for the output (should be empty)")

def main():
    args = parser.parse_args()

    # make the output dir if not exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    page_bundles = parse_generate_markdown(args.input_dir, args.output_dir)
    move_images(args.input_dir, page_bundles)
    print("Done.")

def parse_generate_markdown(input_dir: str, output_dir: str) -> list[str]:
    """
    Parses all markdown files in the input directory and generates the output
    files. Returns the written output directories.
    """
    # get all files within the input dir
    all_markdown = [y for x in os.walk(input_dir) for y in glob(os.path.join(x[0], "*.md"))]

    # list to put directories of generated page bundles (for use in image copying)
    page_bundles = []

    for file_path in all_markdown:
        if not os.path.isfile(file_path):
            continue

        # skip unrelated files
        if "LICENSE" in file_path or "README" in file_path:
            continue

        print("Parsing " + file_path + "... ", end="")
        recipe = file_path

        front_matter = {}
        recipe_filename = os.path.basename(recipe)
        up_to_difficulty = os.path.dirname(recipe)
        difficulty = os.path.basename(up_to_difficulty)
        up_to_meal = os.path.dirname(up_to_difficulty)
        meal = os.path.basename(up_to_meal)

        front_matter.setdefault("layout", "recipe")
        front_matter.setdefault("difficulties", difficulty)
        front_matter.setdefault("meals", meal)

        # get the latest edit date from the git commit log
        relative_path = os.path.join(meal, difficulty, recipe_filename)
        git_command = ["git", "log", "-1", "--pretty=format:%cI", "--follow", "--", relative_path]
        date = subprocess.check_output(git_command, cwd=input_dir).decode("utf-8")
        front_matter.setdefault("publishdate", date)
        front_matter.setdefault("originalpath", "/".join([meal, difficulty, recipe_filename]))

        # read the existing front matter (if any) and contents
        with open(recipe, "r", encoding="utf-8") as f:
            contents = f.readlines()
        existing_front_matter, name, preview_image, contents = split_contents(contents)

        front_matter.setdefault("title", name)
        if preview_image is not None:
            front_matter.setdefault("previewimage", preview_image)

        # merge the front matters (3.9+)
        if existing_front_matter:
            front_matter = front_matter | existing_front_matter

        print(front_matter["title"])

        # Write everything to a file
        basename = os.path.splitext(os.path.basename(recipe))[0]
        page_bundle = os.path.join(output_dir, basename)
        if not os.path.exists(page_bundle):
            os.makedirs(page_bundle)
        page_bundles.append(page_bundle)
        with open(os.path.join(page_bundle, "index.md"), "w+", encoding="utf-8") as f:
            f.write("---\n")
            f.writelines(yaml.dump(front_matter))
            f.write("---\n\n")
            f.writelines(contents)

    return page_bundles

def move_images(input_dir: str, page_bundles: list[str]) -> None:
    """
    Get all images and copy them into all page bundles. This is hugely
    inefficient but I've thought about it for a few days and there is no clean
    solution for image loading that is also contributor-friendly.

    1. Copy all images into each page (they can be referenced relatively, but duplication)
    2. Put all images in /static when parsing (relative URL won't work)
    3. Put all images in /static in the cookbook (very clunky, unintuitive as hell)

    Duplication is a problem with number 1, but since GitHub Page offers us
    1GB for free, I decided the trade-off was most beneficial with 1 than the
    other two.
    """
    all_files = [y for x in os.walk(input_dir) for y in glob(os.path.join(x[0], "**"))]

    for file_path in all_files:
        if not os.path.isfile(file_path):
            continue

        # filter only images
        if file_path[-4:] not in [".png", ".jpg", ".gif"] and file_path[-5:] not in [".jpeg", ".webp"]:
            continue

        print("Copying " + file_path + "... ", end="")
        for page_bundle in page_bundles:
            shutil.copyfile(file_path, os.path.join(page_bundle, os.path.basename(file_path)))
        print("Copied")

def split_contents(contents: list[str]) -> (dict, str, str, list[str]):
    """
    Split a list of all lines in a file into:
      front matter dictionary
      name of recipe or <unnamed>
      url for the first image (only supports ![]() style), None if not found
      all markdown lines in the content apart from the recipe name
    """
    front_matter = []
    recipe_name = "<unnamed>"
    image_url = None
    meaningful_stuff = []
    currently_fm = False
    for line in contents:
        if line == "---\n":
            currently_fm = not currently_fm
            continue

        if line[:2] == "# " and recipe_name == "<unnamed>":
            recipe_name = line[2:].strip()
            continue

        result = re.match("^!\[(.+)\]\((.+)\)", line)
        if result is not None:
            # Take the second group
            image_url = result.group(2)
            # If there is a title ![](blah "title"), this removes it
            image_url = image_url.split(" ")[0]

        if currently_fm:
            front_matter.append(line)
        else:
            meaningful_stuff.append(line)

    try:
        parsed = yaml.safe_load("\n".join(front_matter))
    except Exception as e:
        parsed = {}
        meaningful_stuff = contents

    return (parsed, recipe_name, image_url, meaningful_stuff)

if __name__ == "__main__":
    main()
