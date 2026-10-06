const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');

router.get('/summary', protect, (req, res) => res.json({ totalIncome: 0, totalExpenses: 0, totalSavings: 0 }));
router.get('/monthly', protect, (req, res) => res.json([]));

module.exports = router;
