const testModules = [
  {
    name: "formatters",
    path: "./src/features/map/formatters.test.js",
  },
  {
    name: "authStorage",
    path: "./src/services/authStorage.test.js",
  },
  {
    name: "mapApi",
    path: "./src/services/mapApi.test.js",
  },
  {
    name: "authApi",
    path: "./src/services/authApi.test.js",
  },
];

let failed = false;

for (const testModule of testModules) {
  try {
    const imported = await import(testModule.path);
    await imported.run();
    console.log(`PASS ${testModule.name}`);
  } catch (error) {
    failed = true;
    console.error(`FAIL ${testModule.name}`);
    console.error(error);
  }
}

if (failed) {
  process.exitCode = 1;
} else {
  console.log(`PASS ${testModules.length} frontend test modules`);
}
