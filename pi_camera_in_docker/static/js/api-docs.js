const methodOrder = ["get", "post", "put", "patch", "delete", "options", "head"];
function isRecord(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
function parseOpenApiDocument(value) {
    if (!isRecord(value)) {
        throw new Error("OpenAPI document must be a JSON object");
    }
    const info = isRecord(value.info) ? value.info : {};
    const paths = isRecord(value.paths) ? value.paths : {};
    const components = isRecord(value.components) ? value.components : {};
    const schemas = isRecord(components.schemas) ? components.schemas : {};
    return { info, paths, components: { schemas } };
}
function requiredElement(documentRef, id) {
    const element = documentRef.getElementById(id);
    if (!element) {
        throw new Error(`Required API reference element #${id} was not found`);
    }
    return element;
}
/**
 * Load the local OpenAPI document and render its summary.
 *
 * @param documentRef - Document containing the API reference page.
 * @param fetcher - Fetch implementation used to request the OpenAPI JSON.
 * @returns Resolves after the reference has rendered or an error is shown.
 */
export async function loadApiReference(documentRef, fetcher = globalThis.fetch) {
    const root = requiredElement(documentRef, "api-reference");
    const description = requiredElement(documentRef, "api-description");
    const operations = requiredElement(documentRef, "operations");
    const schemas = requiredElement(documentRef, "schemas");
    const error = requiredElement(documentRef, "load-error");
    const specUrl = root.dataset.specUrl;
    try {
        if (!specUrl) {
            throw new Error("OpenAPI document URL is missing from the API reference page");
        }
        const response = await fetcher(specUrl, { headers: { Accept: "application/json" } });
        if (!response.ok) {
            throw new Error(`OpenAPI document returned HTTP ${response.status}`);
        }
        const specification = parseOpenApiDocument(await response.json());
        const title = specification.info.title;
        const summary = specification.info.description;
        documentRef.title = `${typeof title === "string" && title ? title : "Motion In Ocean"} API`;
        description.textContent =
            typeof summary === "string" && summary ? summary : "API endpoints and schemas.";
        renderOperations(specification.paths, operations, documentRef);
        renderSchemas(specification.components.schemas, schemas, documentRef);
        error.hidden = true;
    }
    catch (exception) {
        const message = exception instanceof Error ? exception.message : String(exception);
        error.textContent = `Could not load the API reference: ${message}`;
        error.hidden = false;
        description.textContent = "The local OpenAPI document could not be loaded.";
    }
}
/**
 * Render each OpenAPI path and its HTTP operations.
 *
 * @param paths - OpenAPI path items keyed by URL path.
 * @param target - Element that receives operation details.
 * @param documentRef - Document used to create elements.
 */
function renderOperations(paths, target, documentRef) {
    for (const [path, pathItem] of Object.entries(paths)) {
        if (!isRecord(pathItem))
            continue;
        for (const method of methodOrder) {
            const value = pathItem[method];
            if (!isRecord(value))
                continue;
            const operation = value;
            const details = documentRef.createElement("details");
            details.className = "operation";
            const summary = documentRef.createElement("summary");
            appendText(summary, "span", method.toUpperCase(), "method", documentRef);
            appendText(summary, "code", path, "operation-path", documentRef);
            appendText(summary, "span", operation.summary || operation.operationId || "", "operation-summary", documentRef);
            details.append(summary);
            const content = documentRef.createElement("div");
            const operationDescription = documentRef.createElement("p");
            operationDescription.textContent = operation.description || "No additional description.";
            content.append(operationDescription);
            const contract = documentRef.createElement("pre");
            contract.textContent = JSON.stringify({
                tags: operation.tags,
                parameters: operation.parameters,
                requestBody: operation.requestBody,
                responses: operation.responses,
            }, null, 2);
            content.append(contract);
            details.append(content);
            target.append(details);
        }
    }
}
/**
 * Render component schemas as readable JSON.
 *
 * @param definitions - Named OpenAPI component schemas.
 * @param target - Element that receives schema details.
 * @param documentRef - Document used to create elements.
 */
function renderSchemas(definitions, target, documentRef) {
    for (const [name, schema] of Object.entries(definitions)) {
        const details = documentRef.createElement("details");
        details.className = "schema";
        const summary = documentRef.createElement("summary");
        appendText(summary, "code", name, "schema-name", documentRef);
        details.append(summary);
        const definition = documentRef.createElement("pre");
        definition.textContent = JSON.stringify(schema, null, 2);
        details.append(definition);
        target.append(details);
    }
}
/**
 * Append a text-only DOM element, avoiding HTML interpretation of spec values.
 *
 * @param parent - Parent to receive the new element.
 * @param tagName - HTML element name.
 * @param value - Text content to display.
 * @param className - CSS class to apply.
 * @param documentRef - Document used to create the element.
 */
function appendText(parent, tagName, value, className, documentRef) {
    const element = documentRef.createElement(tagName);
    element.className = className;
    element.textContent = value;
    parent.append(element);
}
if (typeof document !== "undefined") {
    void loadApiReference(document);
}
