const express = require('express');
const cookieParser = require('cookie-parser');
const path = require('path');

require('./src/db');

const authRouter = require('./src/routes/auth');
const wholesalersRouter = require('./src/routes/wholesalers');
const searchRouter = require('./src/routes/search');

const app = express();
app.use(express.json());
app.use(cookieParser());

app.use('/api/auth', authRouter);
app.use('/api/wholesalers', wholesalersRouter);
app.use('/api/search', searchRouter);

app.use(express.static(path.join(__dirname, 'public')));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Wholesaler pricing comparison running on http://localhost:${PORT}`);
});
