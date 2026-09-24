/**
 * Load the local OpenAPI document and render its summary.
 * @returns {Promise<void>} Resolves after the reference has rendered or an error is shown.
 * @throws {Error} Fetch or response parsing failures are displayed in the page.
 * @async
 */
async function loadApiReference() {
  const root = document.getElementById("api-reference");
  const description = document.getElementById("api-description");
  const operations = document.getElementById("operations");
  const schemas = document.getElementById("schemas");
  const error = document.getElementById("load-error");

  try {
    const response = await fetch(root.dataset.specUrl, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`OpenAPI document returned HTTP ${response.status}`);
    }

    const specification = await response.json();
    document.title = `${specification.info.title} API`;
    description.textContent = specification.info.description || "API endpoints and schemas.";
    renderOperations(specification.paths || {}, operations);
    renderSchemas(specification.components?.schemas || {}, schemas);
  } catch (exception) {
    error.textContent = `Could not load the API reference: ${exception.message}`;
    error.hidden = false;
    description.textContent = "The local OpenAPI document could not be loaded.";
  }
}

/**
 * Render each OpenAPI path and its HTTP operations.
 * @param {Object<string, Object>} paths - OpenAPI path items keyed by URL path.
 * @param {HTMLElement} target - Element that receives operation details.
 * @returns {void}
 */
function renderOperations(paths, target) {
  const methodOrder = ["get", "post", "put", "patch", "delete", "options", "head"];
  for (const [path, pathItem] of Object.entries(paths)) {
    for (const method of methodOrder) {
      const operation = pathItem[method];
      if (!operation) continue;

      const details = document.createElement("details");
      details.className = "operation";
      const summary = document.createElement("summary");
      appendText(summary, "span", method.toUpperCase(), "method");
      appendText(summary, "code", path, "operation-path");
      appendText(
        summary,
        "span",
        operation.summary || operation.operationId || "",
        "operation-summary",
      );
      details.append(summary);

      const content = document.createElement("div");
      const description = document.createElement("p");
      description.textContent = operation.description || "No additional description.";
      content.append(description);
      const contract = document.createElement("pre");
      contract.textContent = JSON.stringify(
        {
          tags: operation.tags,
          parameters: operation.parameters,
          requestBody: operation.requestBody,
          responses: operation.responses,
        },
        null,
        2,
      );
      content.append(contract);
      details.append(content);
      target.append(details);
    }
  }
}

/**
 * Render component schemas as readable JSON.
 * @param {Object<string, Object>} definitions - Named OpenAPI component schemas.
 * @param {HTMLElement} target - Element that receives schema details.
 * @returns {void}
 */
function renderSchemas(definitions, target) {
  for (const [name, schema] of Object.entries(definitions)) {
    const details = document.createElement("details");
    details.className = "schema";
    const summary = document.createElement("summary");
    appendText(summary, "code", name, "schema-name");
    details.append(summary);

    const definition = document.createElement("pre");
    definition.textContent = JSON.stringify(schema, null, 2);
    details.append(definition);
    target.append(details);
  }
}

/**
 * Append a text-only DOM element, avoiding HTML interpretation of spec values.
 * @param {HTMLElement} parent - Parent to receive the new element.
 * @param {string} tagName - HTML element name.
 * @param {string} value - Text content to display.
 * @param {string} className - CSS class to apply.
 * @returns {void}
 */
function appendText(parent, tagName, value, className) {
  const element = document.createElement(tagName);
  element.className = className;
  element.textContent = value;
  parent.append(element);
}

loadApiReference();
