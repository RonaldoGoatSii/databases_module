// validation.js: $jsonSchema validation on films (strict, error), then the two rejected inserts.
// Run after operations.js and load.py: mongosh "$MONGO_URL" --file validation.js

db.runCommand({
  collMod: "films",
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["title", "rating", "length", "rental_rate", "categories", "actors"],
      properties: {
        title: { bsonType: "string" },
        rating: { enum: ["G", "PG", "PG-13", "R", "NC-17"] },
        length: { bsonType: ["int", "long"], minimum: 1, maximum: 999 },
        rental_rate: { bsonType: "decimal" },
        categories: { bsonType: "array", items: { bsonType: "string" } },
        actors: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["actor_id", "name"],
            properties: {
              actor_id: { bsonType: ["int", "long"] },
              name: { bsonType: "string" },
            },
          },
        },
      },
    },
  },
  validationLevel: "strict",
  validationAction: "error",
});
print("validator installed on films");

// A valid base document, with one field broken at a time, so that each rejection has one cause.
const base = {
  _id: 9001,
  title: "VALIDATION CHECK",
  rating: "PG",
  length: 90,
  rental_rate: NumberDecimal("0.99"),
  categories: ["Drama"],
  actors: [{ actor_id: 1, name: "PENELOPE GUINESS" }],
};

try {
  db.films.insertOne({ ...base, _id: 9002, rating: "XXX" });
  print("UNEXPECTED: rating XXX was accepted");
} catch (e) {
  print(`rejected rating XXX: ${e.message}`);
}

try {
  db.films.insertOne({ ...base, _id: 9003, length: "long" });
  print("UNEXPECTED: length 'long' was accepted");
} catch (e) {
  print(`rejected length "long": ${e.message}`);
}

try {
  db.films.insertOne(base);
  print("valid document accepted");
} catch (e) {
  print(`UNEXPECTED: valid document rejected: ${e.message}`);
}
db.films.deleteOne({ _id: 9001 });