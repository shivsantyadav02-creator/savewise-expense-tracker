const mongoose = require('mongoose');

const savingGoalSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true },
  name: { type: String, required: true },
  targetAmount: { type: Number, required: true },
  savedAmount: { type: Number, default: 0 },
  deadline: { type: Date, required: true },
  description: { type: String }
}, { timestamps: true });

module.exports = mongoose.model('SavingGoal', savingGoalSchema);
