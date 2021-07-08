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
 * Replace a URL query parameter in a URL search with a new value, and if it
 * doesn't exist, newly append it.
 *
 * Courtesy of StackOverflow.com/questions/1090948
 *
 * @param {string} param Query string parameter key
 * @param {string} newVal The value to override or set anew for the key
 * @param {string} search The part after the ? in URLs (location.search)
 * @returns The updated search string with parameters changed
 */
function replaceQueryParam(param, newVal, search) {
  let regex = new RegExp("([?;&])" + param + "[^&;]*[;&]?");
  let query = search.replace(regex, "$1").replace(/&$/, '');

  return (query.length > 2 ? query + "&" : "?") + (newVal ? param + "=" + newVal : '');
}

/**
 * Parse all the currently set filters/search queries from the DOM, and returns
 * an organised object to be used in filterRecipes.
 * @returns Filter object (defined at top of function)
 */
function getDOMFilters() {
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
 * Sets the DOM values of various inputs/checkboxes to what is set in the filter
 * object. This function must satisfy the following law:
 * - setDOMFilters(getDOMFilters()) = identity
 *
 * @param {object} filters Filter object as defined in getDOMFilters
 */
function setDOMFilters(filters) {
  document.getElementById("search-query").value = filters.q;

  // Uncheck all checkboxes first to bring it to a clean state.
  let checkboxes = document.getElementsByClassName("filter-checkbox");
  for (let i = 0; i < checkboxes.length; i++) {
    checkboxes[i].checked = false;
  }

  // Set the allergens
  for (let i = 0; i < filters.excludeAllergens.length; i++) {
    document.getElementById("filterallergens" + filters.excludeAllergens[i]).checked = true;
  }

  // All taxonomies.
  for (let key in filters.includeTaxonomies) {
    for (let i = 0; i < filters.includeTaxonomies[key].length; i++) {
      document.getElementById("filter" + key + filters.includeTaxonomies[key][i]).checked = true;
    }
  }

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
 * @param {object} filters Filter object, as returned by getDOMFilters
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
    // Due to an extremely long-standing and curious issue, Hugo only adds
    // the relative dots (e.g. ../../) to a RelPermalink when it's used as
    // a href attribute. It also absolutely wrecks havoc with subdirectory
    // base URLs like GitHub pages (past related issues #7714, #2194, #8078)
    // See most recent issue highlighting exactly this: #8734.
    let properlyRelPermalink = "." + recipe.relPermalink;
    output +=
      "<li class=\"recipe-listing-item col\">" +
        "<a href=\"." + properlyRelPermalink + "\" role=\"article\">" +
          "<div class=\"card h-100\">" +
            (recipe.params.previewimage ?
              "<img loading=\"lazy\" src=\"" + recipe.params.previewimage + "\" class=\"card-image-top mx-1 mt-1\" alt=\"Delicious-looking image of " + escape(recipe.title) + "\" />"
              : "") +
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
function onLoad() {
  // Set the value of the search box from the URL.
  let params = (new URL(document.location)).searchParams;
  document.getElementById("search-query").value = params.get("q");

  // The fetch API is unsupported on IE but we use Bootstrap 5 which doesn't
  // support IE anyway. Plus what CS student uses IE?
  fetch("index.json").then(data => data.json()).then(data => {
    window.recipesData = data;
    let filters = getDOMFilters();
    let recipes = filterRecipes(window.recipesData || [], filters);
    updateRecipeDOM(recipes);
    document.getElementById("page-title").innerHTML = "Recipes";
  });
}

document.addEventListener("DOMContentLoaded", onLoad);
// Since the script tag may be loaded as async, DOM might already be ready and
// the above event may not fire. In　which case, just call onLoad.
if (document.readyState !== "loading") onLoad();

// When a user has typed something into the search in the sidebar, filter and
// update the recipe DOM.
document.getElementById("search-query").addEventListener("input", delay(() => {
  // The list of recipes is already stored on the page
  let filters = getDOMFilters();
  let recipes = filterRecipes(window.recipesData || [], filters);
  updateRecipeDOM(recipes);

  // update the URL and provide a back-button functionality to search queries
  let current = window.location.search;
  let updated = replaceQueryParam("q", filters.q, current);
  history.pushState(filters, document.title, updated);
}, 400));

// When a user has checked or unchecked one of the filtering checkboxes, perform
// the filter and update the recipe DOM.
const checkboxes = document.getElementsByClassName("filter-checkbox");

for (let i = 0; i < checkboxes.length; i++) {
  checkboxes[i].addEventListener("change", () => {
    let filters = getDOMFilters();
    let recipes = filterRecipes(window.recipesData || [], filters);
    updateRecipeDOM(recipes);

    // update the state and provide a back-button functionality to filters
    history.pushState(filters, document.title);
  });
}

// When a user presses the back button after performing searches or filtering,
// read the previous state and update the DOM accordingly.
window.addEventListener("popstate", (event) => {
  // event.state might not be defined if popstate popped back to the first page
  // load, before any pushStates.
  let state = event.state;
  if (!event.state) {
    state = { q: "", excludeAllergens: [], includeTaxonomies: {}};
  }

  setDOMFilters(state);
  let recipes = filterRecipes(window.recipesData || [], state);
  updateRecipeDOM(recipes);
});

// When a user has scrolled and is idle for 300ms, update the scroll position
// cookie. This is used to return the user to the original scroll position after
// a browser popstate event. It is necessary for UX because the dynamic loading
// of recipes causes users to be taken to the top of the page every time.
//
// This is unimplemented because cookies sound like a gigantic rabbit hole of
// beautiful and fabulous problems, one of which is GDPR.
//
// window.addEventListener("scroll", delay(() => {
//   console.log(window.scrollY);
// }, 300));
