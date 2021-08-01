# The Theme

Hi! This is the boilerplate/template/theme that powers how CompSoc Cookbook looks.
Feel free to contribute!

## Explanations

Find which part you want to update, and edit the file. Changes will not be
reflected on the website until the next time the Action runs (recipe edit/creation).

The assets folder here and the static folder in project root are similar, but are
for different uses:

- `static` folder in root: gets copied across as-is. Suited for images.
- `assets` folder here: can utilise Hugo pipeline to minify & postprocess SCSS. Suited for scripts and styles.

Here is the directory structure of this theme, explained:

```
assets/
├── bootstrap         <- Bootstrap source SASS/JS files, don't touch.
├── js                <- All custom JS
└── scss              <- All custom CSS

layouts/
├── 404.html          <- 404
├── index.html        <- Homepage
├── partials/
│   ├── preamble.html <- Universal meta tags, CSS imports, etc
│   ├── navbar.html   <- Universal navbar contained in a <header>
│   ├── listing.html  <- Paginator and recipe listing, requires dict as argument
│   ├── footer.html   <- <footer> element and copyright.
│   └── postamble.html <- Scripts before body closes
├── recipes/
│   ├── list.html     <- /recipes
│   ├── list.json     <- /recipes/index.json provides a JSON api for search
│   ├── no-js-list.html <- /recipes/view-all
│   └── single.html   <- /recipes/<name>
├── meals/ | allergens/ | difficulties/
│   ├── taxonomy.html <- /<grouping>
│   └── term.html     <- /<grouping>/<name>
└── _default/
    ├── taxonomy.html <- tags, and other taxonomies in the future
    ├── term.html     <- tags, and other taxonomies in the future
    └── _markup
        └── render-link.html <- custom link renderer to open external ones in new tabs
```
