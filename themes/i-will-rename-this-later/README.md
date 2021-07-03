# The Theme

Hi! This is the boilerplate/template/theme that powers how CompSoc Cookbook looks.
Feel free to contribute!

## Explanations

Find which part you want to update, and edit the file. Changes will not be
reflected on the website until the next time the Action runs (recipe edit/creation).

```
assets/
├── bootstrap         <- Bootstrap source SASS/JS files, don't touch.
└── scss              <- All custom CSS

layouts/
├── 404.html          <- 404
├── index.html        <- Homepage
├── partials/
│   ├── preamble.html <- Universal meta tags, CSS imports, etc
│   ├── footer.html   <- <footer> element and copyright.
│   ├── postamble.html <- Universal scripts before body closes
│   └── comments.html <- Giscus comment snippet
├── shortcodes/
│   └── image.html
├── recipes/
│   ├── list.html     <- /recipes
│   └── single.html   <- /recipes/name
├── meals/ | allergens/ | difficulties/
│   ├── list.html     <- /<grouping>
│   └── single.html   <- /<grouping>/name
├── taxonomy/
│   ├── list.html     <- in case a new taxonomy is added in the future
│   └── single.html   <- in case a new taxonomy is added in the future
└── _default/
    └── _markup
        └── render-link.html <- custom link renderer to open external ones in new tabs
```
