/**
 * Returns a function that when will call callback in ms milliseconds unless
 * the parent delay function is called again. This is high level trickery that
 * I haven't been able to fully understand yet, insights welcome.
 *
 * Courtesy of StackOverflow.com/questions/1909441
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
 * Courtesy of StackOverflow.com/questions/5251520
 *
 * @param {string} s Raw string to escape
 * @returns HTML-escaped string
 */
function escape(s) {
  return s.replace(/[^0-9A-Za-z ]/g, c => "&#" + c.charCodeAt(0) + ";");
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
 *
 * @returns Filter object (defined at top of function)
 */
function getFiltersFromDOM() {
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
 * - setFiltersToDOM(getFiltersFromDOM()) = identity
 *
 * @param {object} filters Filter object as defined in getFiltersFromDOM
 */
function setFiltersToDOM(filters) {
  document.getElementById("search-query").value = filters.q;

  // Uncheck all checkboxes first to bring it to a clean state.
  let checkboxes = document.getElementsByClassName("filter-checkbox");
  for (let i = 0; i < checkboxes.length; i++) {
    checkboxes[i].checked = false;
  }

  // Set the allergens
  for (let i = 0; i < filters.excludeAllergens.length; i++) {
    let keySelector = "[data-filter-key=allergens]";
    let valueSelector = "[data-filter-value=\"" + filters.excludeAllergens[i] +"\"]"
    let a = document.querySelectorAll(keySelector + valueSelector);
    for (let j = 0; j < a.length; j++) {
      a[j].checked = true;
    }
  }

  // All taxonomies.
  for (let key in filters.includeTaxonomies) {
    for (let i = 0; i < filters.includeTaxonomies[key].length; i++) {
      let keySelector = "[data-filter-key=" + key +"]";
      let valueSelector = "[data-filter-value=\"" + filters.includeTaxonomies[key][i] +"\"]";
      let a = document.querySelectorAll(keySelector + valueSelector);
      for (let j = 0; j < a.length; j++) {
        a[j].checked = true;
      }
    }
  }

}

/**
 * Parse the URL and return a filter object. Allows multiple values to be defined
 * by separating the values with a comma or defining multiple of the same key.
 *
 *  - ?allergens=milk&allergens=eggs     => excludeAllergens: ["milk", "eggs"]
 *  - ?allergens=milk,eggs               => excludeAllergens: ["milk", "eggs"]
 *  - ?allergens[]=milk&allergens[]=eggs => **unsupported**
 *
 * @param {string} url The full document.location or any equivalent URL
 * @returns Filter object as defined in getFiltersFromDOM
 */
 function decodeFiltersFromURL(url) {
  let filters = {
    // search query
    q: "",
    // list of allergens to exclude (all lowercase) in AND style
    excludeAllergens: [],
    // object of (taxonomy => [terms]) to include in OR style
    includeTaxonomies: {}
  };

  let filterEntries = (new URL(url)).searchParams;
  for (let [key, value] of filterEntries.entries()) {
    if (key == "q") {
      filters.q = value;
    } else if (key == "allergens") {
      filters.excludeAllergens.push(...value.split(","));
    } else {
      filters.includeTaxonomies[key] = filters.includeTaxonomies[key] || [];
      filters.includeTaxonomies[key].push(...value.split(","));
    }
  }

  return filters;
}

/**
 * Creates a URL query parameter fragment that encodes the filter object. This
 * function must satisfy the following law:
 * - decodeFiltersFromURL(encodeFiltersToURL(filters)) = filters
 *
 * To satisfy the above law, the query parameters are not appended to any
 * existing URL, but created newly.
 *
 * @param {object} filters Filter object as defined in getFiltersFromDOM
 */
function encodeFiltersToURL(filters) {

  // update the URL and provide a back-button functionality to search queries
  let params  = "";
  params = replaceQueryParam("q", filters.q, params);
  params = replaceQueryParam("allergens", filters.excludeAllergens.join(","), params);
  for (let key in filters.includeTaxonomies) {
    params = replaceQueryParam(key, filters.includeTaxonomies[key].join(","), params);
  }
  return params;
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

/**
 * negate is a Higher-Order-Function that takes operates on a function that
 * takes any number of arguments and returns a boolean, by negating the retur
 * value.
 *
 * @param {function} fn Predicate function that returns a boolean
 * @returns A function that takes the same arguments but negates the return value
 */
function negate(fn) {
  return function(...things) {
    return !fn(...things);
  }
}

/**
 * Search a query against a target and return a positive integer score. 0 is a
 * perfect char-for-char match, the lower the score the further away (maybe only
 * a word matches), and -Infinity means no match.
 *
 * Typos and any sort of fuzzy matching is not supported, as it seems overkill
 * to implement this (or even add a dependency) for compsoc cookbook.
 *
 * @param {string} query Query to search for, space separated
 * @param {string} target The target string
 */
function scoreMultiWordSearch(query, target) {
  // if exact match (base case)
  if (target.includes(query)) return 0;

  // otherwise, see if we can split into further words
  let nextSpace = query.indexOf(" ");
  if (nextSpace > -1) {
    while (nextSpace > -1) {
      // for all splits, e.g. "abc def ghi" => [["abc", "def ghi"],["abc def", "ghi"]]
      before = query.slice(0, nextSpace);
      after = query.slice(nextSpace + 1, query.length);
      // recursively get the score and reduce it by 100.
      // If not found (-Infinity), arithmetic on it is ignored so all good.
      score1 = scoreMultiWordSearch(before, target) - 100;
      score2 = scoreMultiWordSearch(after, target) - 100;
      if (score1 != -Infinity || score2 != -Infinity) {
        // one of the sliced word/phrases had an exact match, so return the
        // score. They are both negative but closer to zero is better.
        return Math.max(score1, score2);
      }

      nextSpace = query.indexOf(" ", nextSpace + 1);
    }
  }

  return -Infinity;
}

/**
 * Filters the list of recipes by the set filters, and returns the remaining
 * recipes.
 *
 * @param {array} recipes Array of recipes
 * @param {object} filters Filter object, as returned by getFiltersFromDOM
 */
function filterRecipes(recipes, filters) {
  let results = recipes;
  if (filters.q) {
    results = recipes
      .map((item) => {
        let titleScore = scoreMultiWordSearch(filters.q.toLowerCase(), item.title.toLowerCase());
        let bodyScore = scoreMultiWordSearch(filters.q.toLowerCase(), item.body.toLowerCase());

        // JavaScript's .map() creates a new array but its contents point to the
        // same reference object, so clone it with the dots before adding a new
        // field. Without this, searchScore will persist between different searches.
        let itemWithScore = {...item};

        // Some really bad heuristics, would love if anyone could come up with
        // an improved algorithm. But tbh it does seem to work pretty well?
        if (titleScore > -Infinity) {
          itemWithScore.searchScore = titleScore;
        } else if (bodyScore > -Infinity) {
          let arbitraryMagicNumber = 5;
          itemWithScore.searchScore = (bodyScore - 100) * arbitraryMagicNumber;
        }

        return itemWithScore;
      })
      .sort((a, b) => a.searchScore <= b.searchScore ? 1 : -1)
      .filter((item) => item.searchScore > -Infinity);
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
  // let params = (new URL(document.location)).searchParams;
  // document.getElementById("search-query").value = params.get("q");
  let filters = decodeFiltersFromURL(document.location);
  setFiltersToDOM(filters);

  // The fetch API is unsupported on IE but we use Bootstrap 5 which doesn't
  // support IE anyway. Plus what CS student uses IE?
  fetch("index.json").then(data => data.json()).then(data => {
    window.recipesData = data;
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
  let filters = getFiltersFromDOM();
  updateRecipeDOM(filterRecipes(window.recipesData || [], filters));

  // update the URL and provide a back-button functionality to search queries
  history.pushState(filters, document.title, encodeFiltersToURL(filters));
}, 400));

// When a user has checked or unchecked one of the filtering checkboxes, perform
// the filter and update the recipe DOM.
const checkboxes = document.getElementsByClassName("filter-checkbox");

for (let i = 0; i < checkboxes.length; i++) {
  checkboxes[i].addEventListener("change", () => {
    let filters = getFiltersFromDOM();
    updateRecipeDOM(filterRecipes(window.recipesData || [], filters));

    // update the state and provide a back-button functionality to filters
    history.pushState(filters, document.title, encodeFiltersToURL(filters));
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

  setFiltersToDOM(state);
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
