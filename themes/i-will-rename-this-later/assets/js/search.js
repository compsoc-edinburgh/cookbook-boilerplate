/**
 * Returns a function that when will call callback in ms milliseconds unless
 * the parent delay function is called again. This is high level trickery that
 * I haven't been able to fully understand yet, insights welcome.
 *
 * Taken from StackOverflow.com/questions/1909441
 *
 * @param {function} callback Function to be called after the delay
 * @param {number} ms Number of milliseconds to wait for further events before
 *   calling the callback function.
 */
function delay(callback, ms) {
  let timer = 0;
  return function() {
    let context = this, args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function () {
      callback.apply(context, args);
    }, ms || 0);
  };
}

/**
 * Escape a user-provided string into HTML codes to prevent XSS attacks.
 *
 * @param {string} s Raw string to escape
 * @returns HTML-escaped string
 */
function escape(s) {
  return s.replace(
      /[^0-9A-Za-z ]/g,
      c => "&#" + c.charCodeAt(0) + ";"
  );
}

/**
 * Parse all the currently set filters/search queries from the DOM, and returns
 * an organised object to be used in filterRecipes.
 * @returns Filter object (defined at top of function)
 */
function getCurrentlySetFilters() {
  let filters = {
    // search query
    q: "",
    // list of allergens to exclude (all lowercase) in AND style
    excludeAllergens: [],
    // object of (taxonomy => [terms]) to include in OR style
    includeTaxonomies: {}
  };

  filters.q = document.getElementById("search-query").value.trim();

  let checkboxes = document.getElementsByClassName("filter-checkbox");
  for (let i = 0; i < checkboxes.length; i++) {
    let filterTaxonomy = checkboxes[i].getAttribute("data-filter-key")
    let filterTerm = checkboxes[i].getAttribute("data-filter-value");

    if (checkboxes[i].checked) {
      if (filterTaxonomy === "allergens") {
        // Allergens get special treatment because they aren't a registered
        // taxonomy, and its behaviour is different -- ticking means exclusion.
        filters["excludeAllergens"].push(filterTerm);
        continue;
      }

      // All normal taxonomies are added to the filter
      filters.includeTaxonomies[filterTaxonomy] = filters.includeTaxonomies[filterTaxonomy] || [];
      filters.includeTaxonomies[filterTaxonomy].push(filterTerm);
    }
  }

  return filters;
}

/**
 * A partially filled higher-order function to be used with Array.some().
 *
 * @param {object} recipe A recipe to compare against
 * @param {string} paramKey The key within recipe.params to check against
 * @returns A function that takes an allergen and returns whether it is contained
 */
function existsInRecipe(recipe, paramKey) {
  return function(term) {
    // if not set, it definitely doesn't exist
    if (!recipe.params[paramKey]) return false;
    // if it's an array, check if it's included
    if (Array.isArray(recipe.params[paramKey]) &&
        recipe.params[paramKey].includes(term)) return true;
    // otherwise check for string equality
    if (recipe.params[paramKey] === term) return true;
    return false;
  }
}

function negate(fn) {
  return function(...things) {
    return !fn(...things);
  }
}

/**
 * Filters the list of recipes by the set filters, and returns the remaining
 * recipes.
 * @param {array} recipes Array of recipes
 * @param {object} filters Filter object, as returned by getCurrentlySetFilters
 */
function filterRecipes(recipes, filters) {
  let results = recipes;
  if (filters.q) {
    results = fuzzysort.go(filters.q, recipes, {
      keys: ["title"]
    }).map((elem) => elem.obj);
  }

  let filteredResults = [];
  for (let i = 0; i < results.length; i++) {
    let result = results[i];
    // remove this recipe if there is at least one excluded allergen that exists
    // in the recipe.
    if(filters.excludeAllergens.some(existsInRecipe(result, "allergens"))) {
      continue;
    }

    // Individual terms within a taxonomy are filtered with OR, but between each
    // taxonomies they are filtered with AND.
    //
    //   ¬ (mealTypeFilter.some(existsInRecipe) ∧ difficultyFilter.some(existsInRecipe) ∧ ...)
    // = (¬ mealTypeFilter.some(existsInRecipe)) ∨ (¬ difficultyFilter.some(existsInRecipe)) ∨ ...
    // = (mealTypeFilter.every(¬ existsInRecipe)) ∨ (difficultyFilter.every(¬ existsInRecipe)) ∨ ...
    if (Object.keys(filters.includeTaxonomies).some((filter) => filters.includeTaxonomies[filter].every(negate(existsInRecipe(result, filter))))) {
      continue;
    }

    filteredResults.push(result);
  }

  return filteredResults;
}

/**
 * Updates the innerHTML of the recipe-listing to the filtered recipes.
 *
 * @param {array} recipes Array of filtered recipe objects in the same format as the API response
 */
function updateRecipeDOM(recipes) {
  let output = ""
  for (const key in recipes) {
    let recipe = recipes[key];
    output +=
      "<li class=\"recipe-listing-item col\">" +
        "<a href=\"" + recipe.permalink + "\" role=\"article\">" +
          "<div class=\"card h-100\">" +
            // "<img src=\"https://source.unsplash.com/random?" + escape(recipe.title) + "\" class=\"card-image-top mx-1 mt-1\" alt=\"Placeholder courtesy of Unsplash. License: https://unsplash.com/license\" />" +
            "<div class=\"card-body\">" +
              "<span class=\"meta\">" + escape(recipe.params.meals) + "/" + escape(recipe.params.difficulties) + "</span>" +
              "<h4 class=\"display-5 mt-lg-3\">" + escape(recipe.title) + "</h2>" +
            "</div>" +
          "</div>" +
        "</a>" +
      "</li>";
  }
  document.getElementById("recipe-listing").innerHTML = output;
}

// On page load, download all recipes from the JSON endpoint and save it to a
// global variable. This speeds up all filtering/searching in the future, and
// saves bandwidth. It's also not common for new recipes to be added/changed
// during a search session.
document.addEventListener("DOMContentLoaded", () => {
  // The fetch API is unsupported on IE but we use Bootstrap 5 which doesn't
  // support IE anyway. Plus what CS student uses IE?
  fetch("index.json").then(data => data.json()).then(data => {
    window.recipesData = data;
    updateRecipeDOM(recipesData);
    document.getElementById("page-title").innerHTML = "Recipes";
  });
});

// When a user has typed something into the search in the sidebar, filter and
// update the recipe DOM.
document.getElementById("search-query").addEventListener("input", delay(() => {
  // The list of recipes is already stored on the page
  let filters = getCurrentlySetFilters();
  let recipes = filterRecipes(window.recipesData || [], filters);
  updateRecipeDOM(recipes);
}, 400));

// When a user has checked or unchecked one of the filtering checkboxes, perform
// the filter and update the recipe DOM.
const checkboxes = document.getElementsByClassName("filter-checkbox");

for (let i = 0; i < checkboxes.length; i++) {
  checkboxes[i].addEventListener("change", () => {
    let filters = getCurrentlySetFilters();
    let recipes = filterRecipes(window.recipesData || [], filters);
    updateRecipeDOM(recipes);
  });
}
