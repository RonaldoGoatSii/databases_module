// index.js: explain of find({"actors.actor_id": 1}) before and after an index on actors.actor_id
// Run: mongosh "$MONGO_URL" --file index.js

function firstStage(plan) {
  let stage = plan;
  while (stage.inputStage) stage = stage.inputStage;
  return stage.stage;
}

function summary(label) {
  const ex = db.films.find({ "actors.actor_id": 1 }).explain("executionStats");
  const s = ex.executionStats;
  const out = {
    stage: firstStage(ex.queryPlanner.winningPlan),
    totalDocsExamined: s.totalDocsExamined,
    nReturned: s.nReturned,
  };
  print(`${label}: ${JSON.stringify(out)}`);
  return out;
}

const before = summary("before index");
db.films.createIndex({ "actors.actor_id": 1 });
const after = summary("after index");
print(`plan changed from ${before.stage} to ${after.stage}; examined ${before.totalDocsExamined} -> ${after.totalDocsExamined}`);