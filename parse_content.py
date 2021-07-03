import argparse
import os
from glob import glob
import html
import subprocess
import yaml
from parsec import *

parser = argparse.ArgumentParser(description='Convert the cook-book directory structure to Hugo structure.')
parser.add_argument('-i', '--input-dir', type=str, required=True,
                    help='top directory for the cook-book recipes')
parser.add_argument('-o', '--output-dir', type=str, required=True,
                    help='top directory for the output (should be empty)')

def main():
    args = parser.parse_args()

    # make the output dir if not exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # get all files with .md extension within the input dir
    recipes = [y for x in os.walk(args.input_dir) for y in glob(os.path.join(x[0], '*.md'))]

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
        git_command = ["git", "log", "-1", "--pretty=format:%ci", "--follow", "--", relative_path]
        date = subprocess.check_output(git_command, cwd=args.input_dir).decode("utf-8")
        front_matter.setdefault("publishdate", date)

        # read the existing front matter (if any) and contents
        with open(recipe, "r") as f:
            contents = f.readlines()
        existing_front_matter, name, contents = split_contents(contents)

        front_matter.setdefault("title", name)

        # merge the front matters (3.9+)
        if existing_front_matter:
            front_matter = front_matter | existing_front_matter

        # write everything to file
        with open(os.path.join(args.output_dir, os.path.basename(recipe)), "w+") as f:
            f.write("---\n")
            f.writelines(yaml.dump(front_matter))
            f.write("---\n\n")
            f.writelines(contents)

def split_contents(contents: list[str]) -> (dict, str, list[str]):
    """
    Split a list of all lines in a file into front matter
    and just regular markdown content.
    """
    front_matter = []
    recipe_name = "<unnamed>"
    meaningful_stuff = []
    currently_fm = False
    for line in contents:
        if line == "---\n":
            currently_fm = not currently_fm
            continue

        if line[:2] == "# " and recipe_name == "<unnamed>":
            recipe_name = line[2:].strip()
            continue

        if currently_fm:
            front_matter.append(line)
        else:
            meaningful_stuff.append(line)

    try:
        parsed = yaml.safe_load("\n".join(front_matter))
    except Exception as e:
        parsed = {}
        meaningful_stuff = contents

    return (parsed, recipe_name, meaningful_stuff)

if __name__ == "__main__":
    main()
