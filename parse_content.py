import argparse
import os
import shutil
from glob import glob
import subprocess
import yaml
import re

parser = argparse.ArgumentParser(
    description="Convert the cook-book directory structure to Hugo structure."
)
parser.add_argument(
    "-i",
    "--input-dir",
    type=str,
    required=True,
    help="top directory for the cook-book recipes",
)
parser.add_argument(
    "-o",
    "--output-dir",
    type=str,
    required=True,
    help="top directory for the output (should be empty)",
)


def main():
    args = parser.parse_args()

    # make the output dir if not exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    parsed_contents: list[tuple[dict, list[str]]] = parse_all_markdown_files(
        args.input_dir
    )
    page_bundle_names: list[str] = [
        write_to_page_bundle(args.output_dir, *parsed_content)
        for parsed_content in parsed_contents
    ]
    move_images(args.input_dir, page_bundle_names)
    print("Done.")


def get_all_markdown_files(input_dir: str) -> list[str]:
    """
    Get all markdown files within the input directory.
    """
    # get all files within the input dir
    all_markdown = [
        y for x in os.walk(input_dir) for y in glob(os.path.join(x[0], "*.md"))
    ]

    return [
        file_path
        for file_path in all_markdown
        if (
            os.path.isfile(file_path)
            and "LICENSE" not in file_path
            and "README" not in file_path
        )
    ]


def directory_structure_to_front_matter(file_path: str) -> dict[str, str]:
    """
    Converts the directory structure of a recipe into a front matter.
    """
    # Make sure the path is well-formed and normalised
    path_to_recipe = os.path.normpath(file_path)

    # Unpack the directory structure into variable names
    *_, meal, difficulty, recipe_filename = path_to_recipe.split(os.sep)

    # Set some front matter using the extracted data
    return {
        "layout": "recipe",
        "difficulties": difficulty,
        "meals": meal,
        "originalfilename": recipe_filename,
        "originalpath": os.path.join(meal, difficulty, recipe_filename),
    }


def git_date_to_front_matter(directory: str, rel_file_path: str) -> dict[str, str]:
    git_command = [
        "git",
        "log",
        "-1",
        "--pretty=format:%cI",
        "--follow",
        "--",
        rel_file_path,
    ]
    date = subprocess.check_output(git_command, cwd=directory).decode("utf-8")

    return {"publishdate": date}


def parse_all_markdown_files(input_dir: str) -> tuple[dict, list[str]]:
    """
    Parses all markdown files in the input directory and generates the output
    files. Returns the written output directories.
    """
    parsed_contents = []

    for file_path in get_all_markdown_files(input_dir):
        print("Parsing " + file_path + "... ", end="", flush=True)

        front_matter = {}
        front_matter |= directory_structure_to_front_matter(file_path)

        # Get the latest edit date from the git commit log, add that in the
        # front matter as the publishdate.
        relative_path = front_matter["originalpath"]
        front_matter |= git_date_to_front_matter(input_dir, relative_path)

        # Read the existing front matter (if any) and contents
        with open(file_path, "r", encoding="utf-8") as f:
            contents = f.readlines()

        content_front_matter, contents = parse_front_matter_and_content(contents)
        front_matter |= content_front_matter

        print(front_matter["title"])

        parsed_contents.append((front_matter, contents))

    return parsed_contents


def write_to_page_bundle(
    output_dir: str, front_matter: dict, content: list[str]
) -> str:
    """
    Write everything to a new file called index.md, within a folder
    titled with the recipe filename. This creates a Hugo page bundle, so
    we can put images within the same folder and reference them relatively.
    """
    basename = os.path.splitext(front_matter["originalfilename"])[0]
    page_bundle_name = os.path.join(output_dir, basename)
    if not os.path.exists(page_bundle_name):
        os.makedirs(page_bundle_name)
    with open(os.path.join(page_bundle_name, "index.md"), "w+", encoding="utf-8") as f:
        f.write("---\n")
        f.writelines(yaml.dump(front_matter))
        f.write("---\n\n")
        f.writelines(content)

    return page_bundle_name


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
        if file_path[-4:] not in [".png", ".jpg", ".gif"] and file_path[-5:] not in [
            ".jpeg",
            ".webp",
        ]:
            continue

        print("Copying " + file_path + "... ", end="")
        for page_bundle in page_bundles:
            shutil.copyfile(
                file_path, os.path.join(page_bundle, os.path.basename(file_path))
            )
        print("Copied")


def parse_front_matter_and_content(
    contents: list[str],
) -> tuple[dict[str, str], list[str]]:
    """
    Parse a list of all lines in a file into:
      front matter (merged result of existing ones and title + preview image)
      all markdown lines in the content apart from the recipe name
    """
    front_matter = {"title": "<unnamed>"}
    front_matter_lines = []
    markdown_content = []

    # Emulate a FSM to parse the front matter
    currently_fm = False
    for line in contents:
        if line == "---\n":
            currently_fm = not currently_fm
            continue

        if line[:2] == "# " and front_matter["title"] == "<unnamed>":
            front_matter["title"] = line[2:].strip()
            continue

        result = re.match("^!\[(.+)\]\((.+)\)", line)
        if result is not None and "previewimage" not in front_matter:
            # Take the second group
            image_url = result.group(2)
            # If there is a title ![](blah "title"), this removes it
            front_matter["previewimage"] = image_url.split(" ")[0]

        if currently_fm:
            front_matter_lines.append(line)
        else:
            markdown_content.append(line)

    try:
        # PyYAML will return None if the YAML is simply not there (zero lines)
        front_matter |= yaml.safe_load("\n".join(front_matter_lines)) or {}
    except Exception as e:
        # If there was an error parsing the YAML, there is a case the front
        # matter isn't really a front matter (like a table). In which case,
        # treat them as normal meaningful markdown content.
        meaningful_stuff = contents

    return (front_matter, markdown_content)


if __name__ == "__main__":
    main()
