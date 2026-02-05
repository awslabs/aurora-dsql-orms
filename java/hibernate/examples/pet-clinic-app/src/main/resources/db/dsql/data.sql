-- Insert specialties first
INSERT INTO specialties (name) SELECT 'radiology' WHERE NOT EXISTS (SELECT * FROM specialties WHERE name='radiology');
INSERT INTO specialties (name) SELECT 'surgery' WHERE NOT EXISTS (SELECT * FROM specialties WHERE name='surgery');
INSERT INTO specialties (name) SELECT 'dentistry' WHERE NOT EXISTS (SELECT * FROM specialties WHERE name='dentistry');

-- Insert vets
INSERT INTO vets (first_name, last_name) SELECT 'James', 'Carter' WHERE NOT EXISTS (SELECT * FROM vets WHERE first_name='James' AND last_name='Carter');
INSERT INTO vets (first_name, last_name) SELECT 'Helen', 'Leary' WHERE NOT EXISTS (SELECT * FROM vets WHERE first_name='Helen' AND last_name='Leary');
INSERT INTO vets (first_name, last_name) SELECT 'Linda', 'Douglas' WHERE NOT EXISTS (SELECT * FROM vets WHERE first_name='Linda' AND last_name='Douglas');
INSERT INTO vets (first_name, last_name) SELECT 'Rafael', 'Ortega' WHERE NOT EXISTS (SELECT * FROM vets WHERE first_name='Rafael' AND last_name='Ortega');
INSERT INTO vets (first_name, last_name) SELECT 'Henry', 'Stevens' WHERE NOT EXISTS (SELECT * FROM vets WHERE first_name='Henry' AND last_name='Stevens');
INSERT INTO vets (first_name, last_name) SELECT 'Sharon', 'Jenkins' WHERE NOT EXISTS (SELECT * FROM vets WHERE first_name='Sharon' AND last_name='Jenkins');

-- Link vets with specialties (using subqueries to get the UUIDs)
INSERT INTO vet_specialties (vet_id, specialty_id)
SELECT v.id, s.id FROM vets v, specialties s 
WHERE v.first_name='Helen' AND v.last_name='Leary' AND s.name='radiology'
AND NOT EXISTS (
    SELECT 1 FROM vet_specialties vs 
    JOIN vets v2 ON vs.vet_id = v2.id 
    JOIN specialties s2 ON vs.specialty_id = s2.id 
    WHERE v2.first_name='Helen' AND v2.last_name='Leary' AND s2.name='radiology'
);

INSERT INTO vet_specialties (vet_id, specialty_id)
SELECT v.id, s.id FROM vets v, specialties s 
WHERE v.first_name='Linda' AND v.last_name='Douglas' AND s.name='surgery'
AND NOT EXISTS (
    SELECT 1 FROM vet_specialties vs 
    JOIN vets v2 ON vs.vet_id = v2.id 
    JOIN specialties s2 ON vs.specialty_id = s2.id 
    WHERE v2.first_name='Linda' AND v2.last_name='Douglas' AND s2.name='surgery'
);

INSERT INTO vet_specialties (vet_id, specialty_id)
SELECT v.id, s.id FROM vets v, specialties s 
WHERE v.first_name='Linda' AND v.last_name='Douglas' AND s.name='dentistry'
AND NOT EXISTS (
    SELECT 1 FROM vet_specialties vs 
    JOIN vets v2 ON vs.vet_id = v2.id 
    JOIN specialties s2 ON vs.specialty_id = s2.id 
    WHERE v2.first_name='Linda' AND v2.last_name='Douglas' AND s2.name='dentistry'
);

INSERT INTO vet_specialties (vet_id, specialty_id)
SELECT v.id, s.id FROM vets v, specialties s 
WHERE v.first_name='Rafael' AND v.last_name='Ortega' AND s.name='surgery'
AND NOT EXISTS (
    SELECT 1 FROM vet_specialties vs 
    JOIN vets v2 ON vs.vet_id = v2.id 
    JOIN specialties s2 ON vs.specialty_id = s2.id 
    WHERE v2.first_name='Rafael' AND v2.last_name='Ortega' AND s2.name='surgery'
);

INSERT INTO vet_specialties (vet_id, specialty_id)
SELECT v.id, s.id FROM vets v, specialties s 
WHERE v.first_name='Henry' AND v.last_name='Stevens' AND s.name='radiology'
AND NOT EXISTS (
    SELECT 1 FROM vet_specialties vs 
    JOIN vets v2 ON vs.vet_id = v2.id 
    JOIN specialties s2 ON vs.specialty_id = s2.id 
    WHERE v2.first_name='Henry' AND v2.last_name='Stevens' AND s2.name='radiology'
);

-- Insert pet types
INSERT INTO types (name) SELECT 'cat' WHERE NOT EXISTS (SELECT * FROM types WHERE name='cat');
INSERT INTO types (name) SELECT 'dog' WHERE NOT EXISTS (SELECT * FROM types WHERE name='dog');
INSERT INTO types (name) SELECT 'lizard' WHERE NOT EXISTS (SELECT * FROM types WHERE name='lizard');
INSERT INTO types (name) SELECT 'snake' WHERE NOT EXISTS (SELECT * FROM types WHERE name='snake');
INSERT INTO types (name) SELECT 'bird' WHERE NOT EXISTS (SELECT * FROM types WHERE name='bird');
INSERT INTO types (name) SELECT 'hamster' WHERE NOT EXISTS (SELECT * FROM types WHERE name='hamster');

-- Insert owners
INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'George', 'Franklin', '110 W. Liberty St.', 'Madison', '6085551023' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='George' AND last_name='Franklin');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Betty', 'Davis', '638 Cardinal Ave.', 'Sun Prairie', '6085551749' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Betty' AND last_name='Davis');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Eduardo', 'Rodriquez', '2693 Commerce St.', 'McFarland', '6085558763' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Eduardo' AND last_name='Rodriquez');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Harold', 'Davis', '563 Friendly St.', 'Windsor', '6085553198' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Harold' AND last_name='Davis');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Peter', 'McTavish', '2387 S. Fair Way', 'Madison', '6085552765' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Peter' AND last_name='McTavish');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Jean', 'Coleman', '105 N. Lake St.', 'Monona', '6085552654' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Jean' AND last_name='Coleman');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Jeff', 'Black', '1450 Oak Blvd.', 'Monona', '6085555387' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Jeff' AND last_name='Black');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Maria', 'Escobito', '345 Maple St.', 'Madison', '6085557683' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Maria' AND last_name='Escobito');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'David', 'Schroeder', '2749 Blackhawk Trail', 'Madison', '6085559435' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='David' AND last_name='Schroeder');

INSERT INTO owners (first_name, last_name, address, city, telephone) 
SELECT 'Carlos', 'Estaban', '2335 Independence La.', 'Waunakee', '6085555487' 
WHERE NOT EXISTS (SELECT * FROM owners WHERE first_name='Carlos' AND last_name='Estaban');

-- Insert pets (using subqueries to get the UUIDs)
INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Leo', '2000-09-07', 
       (SELECT id FROM types WHERE name = 'cat'),
       (SELECT id FROM owners WHERE first_name = 'George' AND last_name = 'Franklin'),
       4.5
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Leo' AND o.first_name = 'George' AND o.last_name = 'Franklin'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Basil', '2002-08-06', 
       (SELECT id FROM types WHERE name = 'hamster'),
       (SELECT id FROM owners WHERE first_name = 'Betty' AND last_name = 'Davis'),
       0.5
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Basil' AND o.first_name = 'Betty' AND o.last_name = 'Davis'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Rosy', '2001-04-17', 
       (SELECT id FROM types WHERE name = 'dog'),
       (SELECT id FROM owners WHERE first_name = 'Eduardo' AND last_name = 'Rodriquez'),
       8.2
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Rosy' AND o.first_name = 'Eduardo' AND o.last_name = 'Rodriquez'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Jewel', '2000-03-07', 
       (SELECT id FROM types WHERE name = 'dog'),
       (SELECT id FROM owners WHERE first_name = 'Eduardo' AND last_name = 'Rodriquez'),
       6.1
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Jewel' AND o.first_name = 'Eduardo' AND o.last_name = 'Rodriquez'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Iggy', '2000-11-30', 
       (SELECT id FROM types WHERE name = 'lizard'),
       (SELECT id FROM owners WHERE first_name = 'Harold' AND last_name = 'Davis'),
       1.2
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Iggy' AND o.first_name = 'Harold' AND o.last_name = 'Davis'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'George', '2000-01-20', 
       (SELECT id FROM types WHERE name = 'snake'),
       (SELECT id FROM owners WHERE first_name = 'Peter' AND last_name = 'McTavish'),
       0.8
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'George' AND o.first_name = 'Peter' AND o.last_name = 'McTavish'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Samantha', '1995-09-04', 
       (SELECT id FROM types WHERE name = 'cat'),
       (SELECT id FROM owners WHERE first_name = 'Jean' AND last_name = 'Coleman'),
       3.8
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Samantha' AND o.first_name = 'Jean' AND o.last_name = 'Coleman'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Max', '1995-09-04', 
       (SELECT id FROM types WHERE name = 'cat'),
       (SELECT id FROM owners WHERE first_name = 'Jean' AND last_name = 'Coleman'),
       5.2
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Max' AND o.first_name = 'Jean' AND o.last_name = 'Coleman'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Lucky', '1999-08-06', 
       (SELECT id FROM types WHERE name = 'bird'),
       (SELECT id FROM owners WHERE first_name = 'Jeff' AND last_name = 'Black'),
       2.3
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Lucky' AND o.first_name = 'Jeff' AND o.last_name = 'Black'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Mulligan', '1997-02-24', 
       (SELECT id FROM types WHERE name = 'dog'),
       (SELECT id FROM owners WHERE first_name = 'Maria' AND last_name = 'Escobito'),
       12.5
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Mulligan' AND o.first_name = 'Maria' AND o.last_name = 'Escobito'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Freddy', '2000-03-09', 
       (SELECT id FROM types WHERE name = 'bird'),
       (SELECT id FROM owners WHERE first_name = 'David' AND last_name = 'Schroeder'),
       3.1
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Freddy' AND o.first_name = 'David' AND o.last_name = 'Schroeder'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Lucky', '2000-06-24', 
       (SELECT id FROM types WHERE name = 'dog'),
       (SELECT id FROM owners WHERE first_name = 'Carlos' AND last_name = 'Estaban'),
       9.7
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Lucky' AND o.first_name = 'Carlos' AND o.last_name = 'Estaban'
);

INSERT INTO pets (name, birth_date, type_id, owner_id, weight)
SELECT 'Sly', '2002-06-08', 
       (SELECT id FROM types WHERE name = 'cat'),
       (SELECT id FROM owners WHERE first_name = 'Carlos' AND last_name = 'Estaban'),
       4.0
WHERE NOT EXISTS (
    SELECT * FROM pets p 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Sly' AND o.first_name = 'Carlos' AND o.last_name = 'Estaban'
);

-- Insert visits (using subqueries to get the UUIDs)
INSERT INTO visits (pet_id, visit_date, description)
SELECT 
    (SELECT p.id FROM pets p JOIN owners o ON p.owner_id = o.id WHERE p.name = 'Samantha' AND o.first_name = 'Jean' AND o.last_name = 'Coleman'),
    '2010-03-04', 
    'rabies shot'
WHERE NOT EXISTS (
    SELECT * FROM visits v 
    JOIN pets p ON v.pet_id = p.id 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Samantha' AND o.first_name = 'Jean' AND o.last_name = 'Coleman' AND v.description = 'rabies shot' AND v.visit_date = '2010-03-04'
);

INSERT INTO visits (pet_id, visit_date, description)
SELECT 
    (SELECT p.id FROM pets p JOIN owners o ON p.owner_id = o.id WHERE p.name = 'Max' AND o.first_name = 'Jean' AND o.last_name = 'Coleman'),
    '2011-03-04', 
    'rabies shot'
WHERE NOT EXISTS (
    SELECT * FROM visits v 
    JOIN pets p ON v.pet_id = p.id 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Max' AND o.first_name = 'Jean' AND o.last_name = 'Coleman' AND v.description = 'rabies shot' AND v.visit_date = '2011-03-04'
);

INSERT INTO visits (pet_id, visit_date, description)
SELECT 
    (SELECT p.id FROM pets p JOIN owners o ON p.owner_id = o.id WHERE p.name = 'Max' AND o.first_name = 'Jean' AND o.last_name = 'Coleman'),
    '2009-06-04', 
    'neutered'
WHERE NOT EXISTS (
    SELECT * FROM visits v 
    JOIN pets p ON v.pet_id = p.id 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Max' AND o.first_name = 'Jean' AND o.last_name = 'Coleman' AND v.description = 'neutered' AND v.visit_date = '2009-06-04'
);

INSERT INTO visits (pet_id, visit_date, description)
SELECT 
    (SELECT p.id FROM pets p JOIN owners o ON p.owner_id = o.id WHERE p.name = 'Samantha' AND o.first_name = 'Jean' AND o.last_name = 'Coleman'),
    '2008-09-04', 
    'spayed'
WHERE NOT EXISTS (
    SELECT * FROM visits v 
    JOIN pets p ON v.pet_id = p.id 
    JOIN owners o ON p.owner_id = o.id 
    WHERE p.name = 'Samantha' AND o.first_name = 'Jean' AND o.last_name = 'Coleman' AND v.description = 'spayed' AND v.visit_date = '2008-09-04'
);
