// operations.js: the 8 operations of the exercise, run on freshly loaded collections, in this order.
// Run: mongosh "$MONGO_URL" --file operations.js
// Operation 8 must run before validation.js: once the validator is on, the TEST FILM document
// (which has only _id and title) is rejected.

const show = (label, value) => print(`${label}: ${JSON.stringify(value)}`);

// 1. Films rated PG-13 and longer than 120 minutes (expected 118)
show("1 PG-13 > 120 min", db.films.countDocuments({ rating: "PG-13", length: { $gt: 120 } }));

// 2. Films in which actor 1 appears (expected 19)
show("2 actor 1", db.films.countDocuments({ "actors.actor_id": 1 }));

// 3. Horror films with a rental rate of 0.99 (expected 43)
show("3 Horror at 0.99", db.films.countDocuments({
  categories: "Horror",
  rental_rate: NumberDecimal("0.99"),
}));

// 4. Customers with at least one unreturned rental among recent_rentals (expected 56)
show("4 unreturned in recent", db.customers.countDocuments({
  recent_rentals: { $elemMatch: { return_date: null } },
}));

// 5. Customer 1 with names and recent rental titles only (expected 1 document with 10 titles)
const c1 = db.customers.find(
  { _id: 1 },
  { _id: 0, first_name: 1, last_name: 1, "recent_rentals.title": 1 }
).toArray();
show("5 customer 1 projection", { documents: c1.length, titles: c1[0].recent_rentals.length });

// 6. Raise by 0.50 the rate of NC-17 films shorter than 60 minutes (expected 21 modified)
const r6 = db.films.updateMany(
  { rating: "NC-17", length: { $lt: 60 } },
  { $inc: { rental_rate: NumberDecimal("0.50") } }
);
show("6 NC-17 < 60 min", { matched: r6.matchedCount, modified: r6.modifiedCount });

// 7. Add a rental to the front of customer 1's recent_rentals and keep 10 (expected 10 items, new one first)
const newRental = {
  rental_id: 99999,
  film_id: 1,
  title: "ACADEMY DINOSAUR",
  rental_date: new Date(),
  return_date: null,
};
db.customers.updateOne(
  { _id: 1 },
  { $push: { recent_rentals: { $each: [newRental], $position: 0, $slice: 10 } } }
);
const c7 = db.customers.findOne({ _id: 1 }, { recent_rentals: 1 });
show("7 recent_rentals size and first", {
  size: c7.recent_rentals.length,
  first: c7.recent_rentals[0].rental_id,
});

// 8. Upsert TEST FILM, run twice (expected: first run upserts 1, second matches 1 and modifies 0)
const up = { _id: 1001 };
const setOnInsert = { $setOnInsert: { title: "TEST FILM" } };
show("8 first run", db.films.updateOne(up, setOnInsert, { upsert: true }));
show("8 second run", db.films.updateOne(up, setOnInsert, { upsert: true }));