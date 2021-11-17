# CompSoc Cookbook Boilerplate

In order to separate the data and its view (and to reduce the bar of contribution), the CompSoc cookbook is separated into two parts:

- the [cookbook repository](https://github.com/compsoc-edinburgh/cook-book) with recipe data in Markdown
- this repo that controls website & thumbnail generation using Hugo.

The cook-book is placed in a Git submodule of this repo. Its tag (SHA1) is pinned to an older version, but this is not important since it gets updated in the workflow with `git submodule update --remote`, as shown in the example workflow below.

This website uses Hugo. Anyone is welcome to contribute, and if you want to change how the website looks/behaves, check out the `CONTRIBUTING` file.

## Local setup

The process of testing and developing locally is very similar to what the GitHub action workflow below does.

Specifically, what you need to for set up is recursively clone (`git clone --recurse-submodules`) the repo & update the recipe repo to latest (`git submodule update --remote`).

Then, running the converter script is simply running the python script. Building the website is with `hugo server`.

## Flow

All of the building happens inside a GitHub action workflow within the cookbook, not here. This is so that changes in recipes trigger the rebuild, not changes in the theme.

1. New commit is pushed to the cookbook.
2. This repo is checked out in a GitHub action, and then the cookbook submodule into `/content_raw`.
3. `parse_content.py` runs, translating the directory structure into front matter and copying recipes into `/content/recipes`
4. `generate_thumbnails.py` runs, creating thumbnails for all recipes and placing them next to them in `/content/recipes`
5. `hugo` is called to build the site, and the `/public` directory is uploaded as GitHub Pages.

`cook-book/.github/workflows/hugo.yml`
```
name: Hugo test
on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
        with:
          repository: compsoc-edinburgh/cookbook-boilerplate
          submodules: 'recursive'
          fetch-depth: 0

      - name: Update cook-book submodule to latest (because default is old)
        run: |
          git submodule update --remote

      - uses: actions/setup-python@v2
        with:
          python-version: 3.9.6

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyyaml

      - name: Parse recipes
        run: |
          python parse_content.py -i content_raw -o content/recipes

      - name: Generate thumbnails
        run: |
          python generate_thumbnails.py -i content/recipes -o content/recipes -serif fonts/PlayfairDisplay-Regular.ttf -sansserif fonts/Lato-Regular.ttf

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v2
        with:
          hugo-version: 'latest'
          extended: true

      - name: Build
        run: hugo --minify --baseURL https://<><><>.github.io/cook-book

      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
```
