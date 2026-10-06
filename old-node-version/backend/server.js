const express = require('express');
const cors = require('cors');
const path = require('path');
const dotenv = require('dotenv');
const connectDB = require('./config/db');

// Load env vars
dotenv.config();

// Connect to Database
connectDB();

const app = express();

// Middleware
app.use(express.json());
app.use(cors());

// Serve static frontend files
app.use(express.static(path.join(__dirname, '../frontend')));

// API Routes
app.use('/api/auth', require('./routes/authRoutes'));
app.use('/api/income', require('./routes/incomeRoutes'));
app.use('/api/expenses', require('./routes/expenseRoutes'));
app.use('/api/goals', require('./routes/goalRoutes'));
app.use('/api/reports', require('./routes/reportRoutes'));

// Fallback to index.html for SPA feeling (or direct HTML access)
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Server running in ${process.env.NODE_ENV || 'development'} mode on port ${PORT}`);
});
