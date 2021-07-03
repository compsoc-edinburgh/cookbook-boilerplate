import argparse
import os
from glob import glob
import html
import subprocess
import yaml

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
        front_matter.setdefault("title", get_name(recipe))
        difficulty = os.path.dirname(recipe)
        front_matter.setdefault("difficulties", os.path.basename(difficulty))
        cuisine = os.path.dirname(difficulty)
        front_matter.setdefault("cuisines", os.path.basename(cuisine))

        # get the latest edit date from the git commit log
        relative_path = os.path.join(os.path.basename(cuisine), os.path.basename(difficulty), os.path.basename(recipe))
        git_command = ["git", "log", "-1", "--pretty=format:%ci", relative_path]
        date = subprocess.check_output(git_command, cwd=args.input_dir).decode("utf-8")
        front_matter.setdefault("publishdate", date)

        # read the existing front matter (if any) and contents
        with open(recipe, "r") as f:
            contents = f.readlines()
        existing_front_matter, contents = split_contents(contents)

        join_front_matter(existing_front_matter, front_matter)

        # write everything to file
        with open(os.path.join(args.output_dir, os.path.basename(recipe)), "w+") as f:
            f.write("---\n")
            f.writelines(yaml.dump(front_matter))
            f.write("---\n\n")
            f.writelines(contents)

def get_name(filename: str) -> str:
    """
    Get the first h1 header within the file, and return it
    """
    with open(filename, "r") as f:
        for line in f:
            if line[:2] == "# ":
                return line[2:].strip()
    return "<unnamed>"

def split_contents(contents: list[str]) -> (list[str], list[str]):
    """
    Split a list of all lines in a file into front matter
    and just regular markdown content.
    """
    front_matter = []
    meaningful_stuff = []
    currently_parsing = False
    for line in contents:
        if line == "---\n":
            currently_parsing = not currently_parsing
            continue

        if currently_parsing:
            front_matter.append(line)
        else:
            meaningful_stuff.append(line)

    try:
        parsed = yaml.safe_load("\n".join(front_matter))
    except Exception as e:
        parsed = {}
        meaningful_stuff = contents

    return (parsed, meaningful_stuff)

def join_front_matter(existing: dict, front_matter: dict) -> None:
    """
    Merge the existing front matter and prioritise those.
    @front_matter@ is modified in place.
    """
    if existing is not None:
        for key, value in existing.items():
            if key in front_matter:
                front_matter[key] = value
            else:
                front_matter.setdefault(key, value)


if __name__ == "__main__":
    main()
