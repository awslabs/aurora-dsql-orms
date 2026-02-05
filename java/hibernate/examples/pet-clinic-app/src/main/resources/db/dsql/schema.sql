CREATE TABLE IF NOT EXISTS vets (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  first_name TEXT,
  last_name  TEXT
);
CREATE INDEX ASYNC ON vets (last_name);

CREATE TABLE IF NOT EXISTS specialties (
  id   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT
);
CREATE INDEX ASYNC ON specialties (name);

CREATE TABLE IF NOT EXISTS vet_specialties (
  vet_id       UUID NOT NULL REFERENCES vets (id),
  specialty_id UUID NOT NULL REFERENCES specialties (id),
  UNIQUE (vet_id, specialty_id)
);

CREATE TABLE IF NOT EXISTS types (
  id   UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT
);
CREATE INDEX ASYNC ON types (name);

CREATE TABLE IF NOT EXISTS owners (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  first_name TEXT,
  last_name  TEXT,
  address    TEXT,
  city       TEXT,
  telephone  TEXT
);
CREATE INDEX ASYNC ON owners (last_name);

CREATE TABLE IF NOT EXISTS pets (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name       TEXT,
  birth_date DATE,
  type_id    UUID NOT NULL REFERENCES types (id),
  owner_id   UUID REFERENCES owners (id),
  weight     DOUBLE PRECISION
);
CREATE INDEX ASYNC ON pets (name);
CREATE INDEX ASYNC ON pets (owner_id);

CREATE TABLE IF NOT EXISTS visits (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  pet_id      UUID REFERENCES pets (id),
  visit_date  DATE,
  description TEXT
);
CREATE INDEX ASYNC ON visits (pet_id);
