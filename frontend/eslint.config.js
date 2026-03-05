import eslint from "@eslint/js";
import vue from "eslint-plugin-vue";
import vuea11y from "eslint-plugin-vuejs-accessibility";
import globals from "globals";
import tseslint from "typescript-eslint";

const IGNORES = [
  "logs",
  "*.log",
  "npm-debug.log*",
  "yarn-debug.log*",
  "yarn-error.log*",
  "pnpm-debug.log*",
  "lerna-debug.log*",
  "node_modules",
  ".DS_Store",
  "dist",
  "dist-ssr",
  "coverage",
  "*.local",
  "src/__generated__/**",
  "**/__generated__/**",
  "*.config.js",
  "src/plugins/*.d.ts",
];

export default tseslint.config(
  {
    ignores: IGNORES,
    linterOptions: {
      reportUnusedDisableDirectives: "off",
    },
  },
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  ...vue.configs["flat/recommended"],
  ...vuea11y.configs["flat/recommended"],
  {
    ignores: IGNORES,
    languageOptions: {
      parserOptions: {
        parser: "@typescript-eslint/parser",
        projectService: true,
        ecmaVersion: 2022,
        extraFileExtensions: [".vue"],
      },
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      "vue/multi-word-component-names": "off",
      "vue/max-attributes-per-line": "off",
      "vue/valid-v-slot": "off",
      "vue/no-use-v-if-with-v-for": "off",
      "vue/component-name-in-template-casing": [
        "error",
        "PascalCase",
        {
          registeredComponentsOnly: true,
        },
      ],
      "vue/prop-name-casing": ["error", "camelCase"],
      "vue/attribute-hyphenation": ["error", "always"],
      "vue/html-self-closing": "off",
      "vue/html-indent": "off",
      "vue/singleline-html-element-content-newline": "off",
      "vue/multiline-html-element-content-newline": "off",
      "vue/attributes-order": "off",
      "vue/html-closing-bracket-newline": "off",
      "vue/no-v-html": "off",
      "vue/require-default-prop": "off",
    },
  },
);
