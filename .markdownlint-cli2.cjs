// Use the official JSON formatter only when the baseline wrapper requests it.
module.exports = {
  ignores: ["node_modules/**", ".venv/**", "CLAUDE.md"],
  config: {
    MD013: false,
    MD024: { siblings_only: true },
    MD033: {
      allowed_elements: ["details", "summary", "br", "b", "strong", "code", "a",
        "sup", "sub", "img", "kbd", "svc"],
    },
    MD060: false,
  },
  ...(process.env.MARKDOWNLINT_RESULTS ? {
    outputFormatters: [["markdownlint-cli2-formatter-json", {
      name: process.env.MARKDOWNLINT_RESULTS,
    }]],
  } : {}),
};
