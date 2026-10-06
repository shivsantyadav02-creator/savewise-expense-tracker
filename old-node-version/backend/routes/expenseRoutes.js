const express = require('express');
const router = express.Router();
const { protect } = require('../middleware/authMiddleware');

router.get('/', protect, (req, res) => res.json([]));
router.post('/', protect, (req, res) => res.json({}));
router.put('/:id', protect, (req, res) => res.json({}));
router.delete('/:id', protect, (req, res) => res.json({ message: 'Deleted' }));

module.exports = router;
