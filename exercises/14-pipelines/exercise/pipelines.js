// pipelines.js: the 5 aggregation pipelines of session 14, run on pagila_docs (films and rentals).
// Run: mongosh "$MONGO_URL" --quiet --file pipelines.js

// 1. Revenue per category per month in 2025, by rental_date (expected 192 documents; Action 2025-01 = 333.87)
const revenuePerCategoryMonth = [
  { $match: { rental_date: { $gte: new Date("2025-01-01"), $lt: new Date("2026-01-01") } } },
  { $unwind: "$categories" },
  {
    $group: {
      _id: {
        category: "$categories",
        month: { $dateToString: { format: "%Y-%m", date: "$rental_date" } },
      },
      revenue: { $sum: "$amount" },
    },
  },
  {
    $project: {
      _id: 0,
      category: "$_id.category",
      month: "$_id.month",
      revenue: { $round: ["$revenue", 2] },
    },
  },
  { $sort: { category: 1, month: 1 } },
];

// 2. The actor with most films in each category, ties included (expected 16 documents, 30 actors in total)
const topActorPerCategory = [
  { $unwind: "$categories" },
  { $unwind: "$actors" },
  {
    $group: {
      _id: { category: "$categories", actor_id: "$actors.actor_id" },
      name: { $first: "$actors.name" },
      films: { $sum: 1 },
    },
  },
  {
    $group: {
      _id: "$_id.category",
      max: { $max: "$films" },
      actors: { $push: { actor_id: "$_id.actor_id", name: "$name", films: "$films" } },
    },
  },
  {
    $project: {
      _id: 0,
      category: "$_id",
      films: "$max",
      actors: {
        $filter: { input: "$actors", as: "a", cond: { $eq: ["$$a.films", "$max"] } },
      },
    },
  },
  { $sort: { category: 1 } },
];

// 3. Distribution of film lengths (expected 96, 224, 214, 216, 250)
const lengthDistribution = [
  {
    $bucket: {
      groupBy: "$length",
      boundaries: [0, 60, 90, 120, 150, 186],
      default: "other",
      output: { count: { $sum: 1 } },
    },
  },
];

// 4. Facet: totals, films per rating, and the 5 longest films (expected 1000 films, average rate 2.98;
//    G 178, PG 194, PG-13 223, R 195, NC-17 210; longest CHICAGO NORTH, CONTROL ANTHEM, DARN FORRESTER,
//    GANGS PRIDE, HOME PITY, all 185 minutes)
const filmSummary = [
  {
    $facet: {
      totals: [
        { $group: { _id: null, films: { $sum: 1 }, avg_rate: { $avg: "$rental_rate" } } },
        { $project: { _id: 0, films: 1, avg_rate: { $round: ["$avg_rate", 2] } } },
      ],
      by_rating: [
        { $group: { _id: "$rating", films: { $sum: 1 } } },
        { $addFields: { rank: { $indexOfArray: [["G", "PG", "PG-13", "R", "NC-17"], "$_id"] } } },
        { $sort: { rank: 1 } },
        { $project: { _id: 0, rating: "$_id", films: 1 } },
      ],
      longest: [
        { $sort: { length: -1, title: 1 } },
        { $limit: 5 },
        { $project: { _id: 0, title: 1, length: 1 } },
      ],
    },
  },
];

const run = (label, collection, pipeline) => {
  const docs = db[collection].aggregate(pipeline).toArray();
  print(`\n=== ${label}: ${docs.length} document(s) ===`);
  printjson(docs.slice(0, 5));
};

run("1 revenue per category per month, 2025", "rentals", revenuePerCategoryMonth);
run("2 top actor per category", "films", topActorPerCategory);
run("3 length distribution", "films", lengthDistribution);
run("4 facet summary", "films", filmSummary);