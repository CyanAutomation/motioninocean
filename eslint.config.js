import globals from "globals";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";

export default [
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
  pluginJs.configs.recommended,
  {
    ignores: [
      "node_modules/",
      "htmlcov/",
      "__pycache__/",
      ".venv/",
      "test_env/",
      "coverage/",
      "pi_camera_in_docker/static/js/app.js",
      "pi_camera_in_docker/static/js/**/*.js",
    ],
  },
  {
    files: ["frontend/src/**/*.ts"],
    languageOptions: {
      parser: tseslint.parser,
    },
    plugins: {
      "@typescript-eslint": tseslint.plugin,
    },
    rules: {
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  {
    rules: {
      "no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_", caughtErrors: "none" },
      ],
      // JSDoc validation (soft rules - warn level for incomplete docs)
      // Ensures all public functions have JSDoc headers with @param/@returns/@async/@throws
      // Private/internal functions can have minimal or no documentation
    },
  },
];
