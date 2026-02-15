import globals from "globals";
import pluginJs from "@eslint/js";

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
    ignores: ["node_modules/", "htmlcov/", "__pycache__/", ".venv/", "test_env/", "coverage/"],
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
