# CompSoc Cookbook Boilerplate

In order to reduce the effort of maintaining/contributing/editing the [cookbook repository](https://github.com/compsoc-edinburgh/cook-book), all the website related things are put in this repository.

This website is built with Hugo.

## Flow

All of the building happens inside a GitHub action workflow within the cookbook, not here. This is so that changes in recipes trigger the rebuild, not changes in the theme.

Currently, the workflow is not merged into the official cookbook yet, but it is running on a fork by yutotakano: https://yutotakano.github.io/cook-book.

1. New commit is pushed to the cookbook.
2. This repo is checked out in a GitHub action, and then the cookbook is checked out into `/content_raw`.
3. The directory structure is translated into front matter and copied into `/content/recipes` using `parse_content.py`
4. `hugo` is called to build the site, and the `/public` directory is uploaded as GitHub Pages.

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
          repository: compsoc-edinburgh/cookbook-template

      - uses: actions/checkout@v2
        with:
          path: content_raw

      - uses: actions/setup-python@v2
        with:
          python-version: 3.9.6

      - name: Parse recipes
        run: |
          python parse_content.py -i content_raw -o content/recipes

      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v2
        with:
          hugo-version: 'latest'
          extended: true

      - name: Build
        run: hugo --minify

      - name: Deploy
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./public
```
