/** @type {import("jest").Config} **/
module.exports = {
  testEnvironment: "node",
  roots: ["<rootDir>/test"],
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
