import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { loadApiReference } from "../../frontend/src/api-docs.ts";

class TestElement {
  readonly children: TestElement[] = [];
  className = "";
  dataset: Record<string, string> = {};
  hidden = false;
  textContent: string | null = "";

  constructor(public tagName = "div") {}

  append(...children: TestElement[]): void {
    this.children.push(...children);
  }
}

function createDocument(): { document: Document; elements: Map<string, TestElement> } {
  const elements = new Map<string, TestElement>(
    ["api-reference", "api-description", "operations", "schemas", "load-error"].map(
      (id): [string, TestElement] => [id, new TestElement()],
    ),
  );
  elements.get("api-reference")!.dataset.specUrl = "/openapi.json";

  const mockDocument = {
    title: "",
    getElementById: (id: string) => elements.get(id) ?? null,
    createElement: (tagName: string) => new TestElement(tagName),
  };
  return {
    elements,
    document: mockDocument as unknown as Document,
  };
}

function getElement(elements: Map<string, TestElement>, id: string): TestElement {
  const element = elements.get(id);
  assert.ok(element, `expected test element #${id}`);
  return element;
}

test("browser entry points load the generated TypeScript modules", () => {
  const apiTemplate = readFileSync("pi_camera_in_docker/templates/api_docs.html", "utf8");
  const viewerTemplate = readFileSync("pi_camera_in_docker/templates/index.html", "utf8");

  assert.match(apiTemplate, /<script type="module"[^>]+js\/api-docs\.js/);
  assert.match(viewerTemplate, /<script type="module"[^>]+js\/app\.js/);
  assert.match(viewerTemplate, /<script type="module"[^>]+js\/settings\.js/);
});

test("loadApiReference renders operations and schemas from the local OpenAPI document", async () => {
  const { document, elements } = createDocument();
  const response = {
    ok: true,
    status: 200,
    json: async () => ({
      info: { title: "Motion In Ocean", description: "Camera API" },
      paths: {
        "/api/cameras": {
          get: {
            summary: "List cameras",
            description: "Lists configured cameras.",
            responses: { 200: { description: "Success" } },
          },
        },
      },
      components: {
        schemas: { Camera: { type: "object", properties: { id: { type: "string" } } } },
      },
    }),
  };

  await loadApiReference(document, async (url, options) => {
    assert.equal(url, "/openapi.json");
    assert.deepEqual(options, { headers: { Accept: "application/json" } });
    return response;
  });

  assert.equal(document.title, "Motion In Ocean API");
  assert.equal(getElement(elements, "api-description").textContent, "Camera API");
  assert.equal(getElement(elements, "operations").children.length, 1);
  assert.equal(
    getElement(elements, "operations").children[0]!.children[0]!.children[1]!.textContent,
    "/api/cameras",
  );
  assert.equal(getElement(elements, "schemas").children.length, 1);
  assert.equal(
    getElement(elements, "schemas").children[0]!.children[1]!.textContent!.includes('"id"'),
    true,
  );
  assert.equal(getElement(elements, "load-error").hidden, true);
});

test("loadApiReference displays an error when the OpenAPI request fails", async () => {
  const { document, elements } = createDocument();

  await loadApiReference(document, async () => ({
    ok: false,
    status: 503,
    json: async () => ({}),
  }));

  assert.equal(getElement(elements, "load-error").hidden, false);
  assert.match(getElement(elements, "load-error").textContent || "", /HTTP 503/);
  assert.equal(
    getElement(elements, "api-description").textContent,
    "The local OpenAPI document could not be loaded.",
  );
});
