/** @type {import("jest").Config} **/
module.exports = {
  testEnvironment: "node",
  // Only the package's own (mocked) unit tests. The example app under
  // examples/ has its own live-cluster suite run from its own directory.
  roots: ["<rootDir>/tests"],
  transform: {
    "^.+\\.tsx?$": [
      "babel-jest",
      {
        presets: [
          ["@babel/preset-env", { targets: { node: "current" } }],
          "@babel/preset-typescript",
        ],
      },
    ],
  },
};
