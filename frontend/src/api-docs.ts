interface OpenApiOperation {
  description?: string;
  operationId?: string;
  parameters?: unknown;
  requestBody?: unknown;
  responses?: unknown;
  summary?: string;
  tags?: unknown;
}

interface OpenApiDocument {
  components: {
    schemas: Record<string, unknown>;
  };
  info: Record<string, unknown>;
  paths: Record<string, unknown>;
}

type ApiResponse = Pick<Response, "json" | "ok" | "status">;
type ApiFetch = (input: string, init?: Parameters<typeof fetch>[1]) => Promise<ApiResponse>;

const methodOrder = ["get", "post", "put", "patch", "delete", "options", "head"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseOpenApiDocument(value: unknown): OpenApiDocument {
  if (!isRecord(value)) {
    throw new Error("OpenAPI document must be a JSON object");
  }

  const info = isRecord(value.info) ? value.info : {};
  const paths = isRecord(value.paths) ? value.paths : {};
  const components = isRecord(value.components) ? value.components : {};
  const schemas = isRecord(components.schemas) ? components.schemas : {};

  return { info, paths, components: { schemas } };
}

function requiredElement<T extends HTMLElement>(documentRef: Document, id: string): T {
  const element = documentRef.getElementById(id);
  if (!element) {
    throw new Error(`Required API reference element #${id} was not found`);
  }
  return element as T;
}

/**
 * Load the local OpenAPI document and render its summary.
 *
 * @param documentRef - Document containing the API reference page.
 * @param fetcher - Fetch implementation used to request the OpenAPI JSON.
 * @returns Resolves after the reference has rendered or an error is shown.
 */
export async function loadApiReference(
  documentRef: Document,
  fetcher: ApiFetch = globalThis.fetch,
): Promise<void> {
  const root = requiredElement<HTMLElement>(documentRef, "api-reference");
  const description = requiredElement<HTMLElement>(documentRef, "api-description");
  const operations = requiredElement<HTMLElement>(documentRef, "operations");
  const schemas = requiredElement<HTMLElement>(documentRef, "schemas");
  const error = requiredElement<HTMLElement>(documentRef, "load-error");
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
  } catch (exception: unknown) {
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
function renderOperations(
  paths: Record<string, unknown>,
  target: HTMLElement,
  documentRef: Document,
): void {
  for (const [path, pathItem] of Object.entries(paths)) {
    if (!isRecord(pathItem)) continue;
    for (const method of methodOrder) {
      const value = pathItem[method];
      if (!isRecord(value)) continue;
      const operation = value as OpenApiOperation;

      const details = documentRef.createElement("details");
      details.className = "operation";
      const summary = documentRef.createElement("summary");
      appendText(summary, "span", method.toUpperCase(), "method", documentRef);
      appendText(summary, "code", path, "operation-path", documentRef);
      appendText(
        summary,
        "span",
        operation.summary || operation.operationId || "",
        "operation-summary",
        documentRef,
      );
      details.append(summary);

      const content = documentRef.createElement("div");
      const operationDescription = documentRef.createElement("p");
      operationDescription.textContent = operation.description || "No additional description.";
      content.append(operationDescription);
      const contract = documentRef.createElement("pre");
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
 *
 * @param definitions - Named OpenAPI component schemas.
 * @param target - Element that receives schema details.
 * @param documentRef - Document used to create elements.
 */
function renderSchemas(
  definitions: Record<string, unknown>,
  target: HTMLElement,
  documentRef: Document,
): void {
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
function appendText(
  parent: HTMLElement,
  tagName: "code" | "span",
  value: string,
  className: string,
  documentRef: Document,
): void {
  const element = documentRef.createElement(tagName);
  element.className = className;
  element.textContent = value;
  parent.append(element);
}

if (typeof document !== "undefined") {
  void loadApiReference(document);
}
