-- Vets with explicit UUIDs
INSERT INTO vets VALUES ('7b4e3e8a-8c0f-4087-b08f-a5e927d6a1fe', 'James', 'Carter');
INSERT INTO vets VALUES ('9b549c3d-e2d5-4306-9fa7-6b746bcf976f', 'Helen', 'Leary');
INSERT INTO vets VALUES ('1c48fc5a-7c1b-4b32-990e-f9fe8ba75b4d', 'Linda', 'Douglas');
INSERT INTO vets VALUES ('2a9e3a1f-3a3d-4e9c-b8a5-7c77e6eb6a8a', 'Rafael', 'Ortega');
INSERT INTO vets VALUES ('3d2c325a-6c5d-4c2a-b8f0-8e7d92a768e1', 'Henry', 'Stevens');
INSERT INTO vets VALUES ('4e5f6a7b-8c9d-0e1f-2a3b-4c5d6e7f8a9b', 'Sharon', 'Jenkins');

-- Specialties with explicit UUIDs
INSERT INTO specialties VALUES ('a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d', 'radiology');
INSERT INTO specialties VALUES ('b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e', 'surgery');
INSERT INTO specialties VALUES ('c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f', 'dentistry');

-- Vet specialties using the explicit UUIDs
INSERT INTO vet_specialties VALUES ('9b549c3d-e2d5-4306-9fa7-6b746bcf976f', 'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d');
INSERT INTO vet_specialties VALUES ('1c48fc5a-7c1b-4b32-990e-f9fe8ba75b4d', 'b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e');
INSERT INTO vet_specialties VALUES ('1c48fc5a-7c1b-4b32-990e-f9fe8ba75b4d', 'c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f');
INSERT INTO vet_specialties VALUES ('2a9e3a1f-3a3d-4e9c-b8a5-7c77e6eb6a8a', 'b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e');
INSERT INTO vet_specialties VALUES ('3d2c325a-6c5d-4c2a-b8f0-8e7d92a768e1', 'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d');

-- Pet types with explicit UUIDs
INSERT INTO types VALUES ('d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a', 'cat');
INSERT INTO types VALUES ('e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b', 'dog');
INSERT INTO types VALUES ('f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c', 'lizard');
INSERT INTO types VALUES ('a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2d', 'snake');
INSERT INTO types VALUES ('b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e', 'bird');
INSERT INTO types VALUES ('c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4f', 'hamster');

-- Owners with explicit UUIDs
INSERT INTO owners VALUES ('d0e1f2a3-b4c5-6d7e-8f9a-0b1c2d3e4f5a', 'George', 'Franklin', '110 W. Liberty St.', 'Madison', '6085551023');
INSERT INTO owners VALUES ('e1f2a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6b', 'Betty', 'Davis', '638 Cardinal Ave.', 'Sun Prairie', '6085551749');
INSERT INTO owners VALUES ('f2a3b4c5-d6e7-8f9a-0b1c-2d3e4f5a6b7c', 'Eduardo', 'Rodriquez', '2693 Commerce St.', 'McFarland', '6085558763');
INSERT INTO owners VALUES ('a3b4c5d6-e7f8-9a0b-1c2d-3e4f5a6b7c8d', 'Harold', 'Davis', '563 Friendly St.', 'Windsor', '6085553198');
INSERT INTO owners VALUES ('b4c5d6e7-f8a9-0b1c-2d3e-4f5a6b7c8d9e', 'Peter', 'McTavish', '2387 S. Fair Way', 'Madison', '6085552765');
INSERT INTO owners VALUES ('c5d6e7f8-a90b-1c2d-3e4f-5a6b7c8d9e0f', 'Jean', 'Coleman', '105 N. Lake St.', 'Monona', '6085552654');
INSERT INTO owners VALUES ('d6e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a', 'Jeff', 'Black', '1450 Oak Blvd.', 'Monona', '6085555387');
INSERT INTO owners VALUES ('e7f8a90b-1c2d-3e4f-5a6b-7c8d9e0f1a2b', 'Maria', 'Escobito', '345 Maple St.', 'Madison', '6085557683');
INSERT INTO owners VALUES ('f8a90b1c-2d3e-4f5a-6b7c-8d9e0f1a2b3c', 'David', 'Schroeder', '2749 Blackhawk Trail', 'Madison', '6085559435');
INSERT INTO owners VALUES ('a90b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d', 'Carlos', 'Estaban', '2335 Independence La.', 'Waunakee', '6085555487');

-- Pets with explicit UUIDs
INSERT INTO pets VALUES ('b01c2d3e-4f5a-6b7c-8d9e-0f1a2b3c4d5e', 'Leo', '2010-09-07', 'd4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a', 'd0e1f2a3-b4c5-6d7e-8f9a-0b1c2d3e4f5a');
INSERT INTO pets VALUES ('c12d3e4f-5a6b-7c8d-9e0f-1a2b3c4d5e6f', 'Basil', '2012-08-06', 'c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4f', 'e1f2a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6b');
INSERT INTO pets VALUES ('d23e4f5a-6b7c-8d9e-0f1a-2b3c4d5e6f7a', 'Rosy', '2011-04-17', 'e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b', 'f2a3b4c5-d6e7-8f9a-0b1c-2d3e4f5a6b7c');
INSERT INTO pets VALUES ('e34f5a6b-7c8d-9e0f-1a2b-3c4d5e6f7a8b', 'Jewel', '2010-03-07', 'e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b', 'f2a3b4c5-d6e7-8f9a-0b1c-2d3e4f5a6b7c');
INSERT INTO pets VALUES ('f45a6b7c-8d9e-0f1a-2b3c-4d5e6f7a8b9c', 'Iggy', '2010-11-30', 'f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c', 'a3b4c5d6-e7f8-9a0b-1c2d-3e4f5a6b7c8d');
INSERT INTO pets VALUES ('a56b7c8d-9e0f-1a2b-3c4d-5e6f7a8b9c0d', 'George', '2010-01-20', 'a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2d', 'b4c5d6e7-f8a9-0b1c-2d3e-4f5a6b7c8d9e');
INSERT INTO pets VALUES ('b67c8d9e-0f1a-2b3c-4d5e-6f7a8b9c0d1e', 'Samantha', '2012-09-04', 'd4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a', 'c5d6e7f8-a90b-1c2d-3e4f-5a6b7c8d9e0f');
INSERT INTO pets VALUES ('c78d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f', 'Max', '2012-09-04', 'd4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a', 'c5d6e7f8-a90b-1c2d-3e4f-5a6b7c8d9e0f');
INSERT INTO pets VALUES ('d89e0f1a-2b3c-4d5e-6f7a-8b9c0d1e2f3a', 'Lucky', '2011-08-06', 'b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e', 'd6e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a');
INSERT INTO pets VALUES ('e90f1a2b-3c4d-5e6f-7a8b-9c0d1e2f3a4b', 'Mulligan', '2007-02-24', 'e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b', 'e7f8a90b-1c2d-3e4f-5a6b-7c8d9e0f1a2b');
INSERT INTO pets VALUES ('fa1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d', 'Freddy', '2010-03-09', 'b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e', 'f8a90b1c-2d3e-4f5a-6b7c-8d9e0f1a2b3c');
INSERT INTO pets VALUES ('ab2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e', 'Lucky', '2010-06-24', 'e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b', 'a90b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d');
INSERT INTO pets VALUES ('bc3d4e5f-6a7b-8c9d-0e1f-2a3b4c5d6e7f', 'Sly', '2012-06-08', 'd4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a', 'a90b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d');

-- Visits with explicit UUIDs
INSERT INTO visits VALUES ('cd4e5f6a-7b8c-9d0e-1f2a-3b4c5d6e7f8a', 'b67c8d9e-0f1a-2b3c-4d5e-6f7a8b9c0d1e', '2013-01-01', 'rabies shot');
INSERT INTO visits VALUES ('de5f6a7b-8c9d-0e1f-2a3b-4c5d6e7f8a9b', 'c78d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f', '2013-01-02', 'rabies shot');
INSERT INTO visits VALUES ('ef6a7b8c-9d0e-1f2a-3b4c-5d6e7f8a9b0c', 'c78d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f', '2013-01-03', 'neutered');
INSERT INTO visits VALUES ('fa7b8c9d-0e1f-2a3b-4c5d-6e7f8a9b0c1d', 'b67c8d9e-0f1a-2b3c-4d5e-6f7a8b9c0d1e', '2013-01-04', 'spayed');
