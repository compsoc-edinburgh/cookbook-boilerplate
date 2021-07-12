import argparse
import os
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

    # get all files with .md extension within the input dir
    recipes = [y for x in os.walk(args.input_dir) for y in glob(os.path.join(x[0], "*.md"))]

    for recipe in recipes:
        # skip unrelated files
        if "LICENSE" in recipe or "README" in recipe:
            continue

        front_matter = {}
        front_matter.setdefault("layout", "recipe")
        difficulty = os.path.dirname(recipe)
        front_matter.setdefault("difficulties", os.path.basename(difficulty))
        meal = os.path.dirname(difficulty)
        front_matter.setdefault("meals", os.path.basename(meal))

        # get the latest edit date from the git commit log
        relative_path = os.path.join(os.path.basename(meal), os.path.basename(difficulty), os.path.basename(recipe))
        git_command = ["git", "log", "-1", "--pretty=format:%cI", "--follow", "--", relative_path]
        date = subprocess.check_output(git_command, cwd=args.input_dir).decode("utf-8")
        front_matter.setdefault("publishdate", date)

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

        # write everything to a Page Bundle (see Hugo docs)
        basename = os.path.splitext(os.path.basename(recipe))[0]
        if not os.path.exists(os.path.join(args.output_dir, basename)):
            os.makedirs(args.output_dir, basename)
        with open(os.path.join(args.output_dir, basename, "index.md"), "w+", encoding="utf-8") as f:
            f.write("---\n")
            f.writelines(yaml.dump(front_matter))
            f.write("---\n\n")
            f.writelines(contents)

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
            image_url = result.group(2)

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
