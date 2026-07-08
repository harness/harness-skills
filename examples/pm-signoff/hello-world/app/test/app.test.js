const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const { spawn } = require("node:child_process");
const path = require("node:path");

const TEST_PORT = 39421;

test("GET / returns hello world", async (t) => {
  const child = spawn(process.execPath, [path.join(__dirname, "../src/index.js")], {
    env: {
      ...process.env,
      PORT: String(TEST_PORT),
      HELLO_MESSAGE: "Hello, World!",
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  t.after(() => {
    child.kill();
  });

  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("server did not start")), 5000);
    const check = () => {
      http
        .get(`http://127.0.0.1:${TEST_PORT}/health`, (response) => {
          if (response.statusCode === 200) {
            clearTimeout(timeout);
            resolve();
            return;
          }
          setTimeout(check, 100);
        })
        .on("error", () => setTimeout(check, 100));
    };
    check();
  });

  const body = await new Promise((resolve, reject) => {
    http
      .get(`http://127.0.0.1:${TEST_PORT}/`, (response) => {
        let data = "";
        response.on("data", (chunk) => {
          data += chunk;
        });
        response.on("end", () => resolve(data));
      })
      .on("error", reject);
  });

  assert.equal(body.trim(), "Hello, World!");
});
