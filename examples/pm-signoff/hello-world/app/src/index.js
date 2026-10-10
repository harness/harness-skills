const http = require("http");

const PORT = Number(process.env.PORT) || 3000;
const MESSAGE = process.env.HELLO_MESSAGE || "Hello, World!";

const server = http.createServer((_request, response) => {
  if (_request.url === "/health") {
    response.writeHead(200, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ status: "ok" }));
    return;
  }

  response.writeHead(200, { "Content-Type": "text/plain" });
  response.end(`${MESSAGE}\n`);
});

server.listen(PORT, () => {
  console.log(`pm-signoff-hello-world listening on port ${PORT}`);
});
