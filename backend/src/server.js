const express = require('express');
const app = express();
const port = 3000;

// A simple route to check if the server is working
app.get('/', (req, res) => {
  res.send('Hello from the ANUMATI backend!');
});

// This is the crucial part!
// It starts the server and keeps it running.
app.listen(port, () => {
  console.log(`Server is listening on http://localhost:${port}`);
});
