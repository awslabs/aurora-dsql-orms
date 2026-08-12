const { createDefaultPreset } = require("ts-jest");

const tsJestTransformCfg = createDefaultPreset().transform;

/** @type {import("jest").Config} **/
module.exports = {
  testEnvironment: "node",
  // Only the package's own (mocked) unit tests. The example app under
  // examples/ has its own live-cluster suite run from its own directory.
  roots: ["<rootDir>/tests"],
  transform: {
    ...tsJestTransformCfg,
  },
};
