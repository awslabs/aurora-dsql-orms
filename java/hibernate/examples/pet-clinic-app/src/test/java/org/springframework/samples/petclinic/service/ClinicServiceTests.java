/*
 * Copyright 2012-2019 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.samples.petclinic.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.LocalDate;
import java.util.Collection;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase.Replace;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.samples.petclinic.owner.Owner;
import org.springframework.samples.petclinic.owner.OwnerRepository;
import org.springframework.samples.petclinic.owner.Pet;
import org.springframework.samples.petclinic.owner.PetType;
import org.springframework.samples.petclinic.owner.Visit;
import org.springframework.samples.petclinic.vet.Vet;
import org.springframework.samples.petclinic.vet.VetRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Integration test of the Service and the Repository layer.
 * <p>
 * ClinicServiceSpringDataJpaTests subclasses benefit from the following services provided
 * by the Spring TestContext Framework:
 * </p>
 * <ul>
 * <li><strong>Spring IoC container caching</strong> which spares us unnecessary set up
 * time between test execution.</li>
 * <li><strong>Dependency Injection</strong> of test fixture instances, meaning that we
 * don't need to perform application context lookups. See the use of
 * {@link Autowired @Autowired} on the <code> </code> instance variable, which uses
 * autowiring <em>by type</em>.
 * <li><strong>Transaction management</strong>, meaning each test method is executed in
 * its own transaction, which is automatically rolled back by default. Thus, even if tests
 * insert or otherwise change database state, there is no need for a teardown or cleanup
 * script.
 * <li>An {@link org.springframework.context.ApplicationContext ApplicationContext} is
 * also inherited and can be used for explicit bean lookup if necessary.</li>
 * </ul>
 *
 * @author Ken Krebs
 * @author Rod Johnson
 * @author Juergen Hoeller
 * @author Sam Brannen
 * @author Michael Isvy
 * @author Dave Syer
 */
@DataJpaTest(includeFilters = @ComponentScan.Filter(Service.class))
// Ensure that if the mysql profile is active we connect to the real database:
// @AutoConfigureTestDatabase(replace = Replace.NONE)
// @TestPropertySource("/application-postgres.properties")
class ClinicServiceTests {

	@Autowired
	protected OwnerRepository owners;

	@Autowired
	protected VetRepository vets;

	Pageable pageable = Pageable.unpaged();

	@Test
	void shouldFindOwnersByLastName() {
		// Create and save a test owner
		Owner owner = new Owner();
		owner.setFirstName("George");
		owner.setLastName("Davis");
		owner.setAddress("123 Main St");
		owner.setCity("Wollongong");
		owner.setTelephone("1234567890");
		this.owners.save(owner);

		// Search for the owner
		Page<Owner> owners = this.owners.findByLastName("Davis", pageable);
		assertThat(owners).isNotEmpty();

		// Search for non-existent owner
		owners = this.owners.findByLastName("Daviss", pageable);
		assertThat(owners).isEmpty();
	}

	@Test
	void shouldFindSingleOwnerWithPet() {
		// Find all owners first
		Page<Owner> ownersPage = this.owners.findAll(pageable);
		assertThat(ownersPage).isNotEmpty();

		// Get the first owner
		Owner owner = ownersPage.getContent().get(0);
		assertThat(owner.getLastName()).isNotNull();
		assertThat(owner.getPets()).isNotEmpty();
		assertThat(owner.getPets().get(0).getType()).isNotNull();
	}

	@Test
	@Transactional
	void shouldInsertOwner() {
		Page<Owner> owners = this.owners.findByLastName("Schultz", pageable);
		int found = (int) owners.getTotalElements();

		Owner owner = new Owner();
		owner.setFirstName("Sam");
		owner.setLastName("Schultz");
		owner.setAddress("4, Evans Street");
		owner.setCity("Wollongong");
		owner.setTelephone("4444444444");
		this.owners.save(owner);
		assertThat(owner.getId()).isNotNull();

		owners = this.owners.findByLastName("Schultz", pageable);
		assertThat(owners.getTotalElements()).isEqualTo(found + 1);
	}

	@Test
	@Transactional
	void shouldUpdateOwner() {
		// Create a new owner
		Owner owner = new Owner();
		owner.setFirstName("Sam");
		owner.setLastName("Coleman");
		owner.setAddress("123 Main St");
		owner.setCity("Wollongong");
		owner.setTelephone("1234567890");
		this.owners.save(owner);

		// Update the owner's last name
		String oldLastName = owner.getLastName();
		String newLastName = oldLastName + "X";
		owner.setLastName(newLastName);
		this.owners.save(owner);

		// Retrieve the owner and verify the name was updated
		UUID ownerId = owner.getId();
		Owner updatedOwner = this.owners.findById(ownerId);
		assertThat(updatedOwner.getLastName()).isEqualTo(newLastName);
	}

	@Test
	void shouldFindAllPetTypes() {
		Collection<PetType> petTypes = this.owners.findPetTypes();
		assertThat(petTypes).isNotEmpty();

		// Verify we have at least one pet type
		boolean foundCat = false;
		for (PetType type : petTypes) {
			if ("cat".equals(type.getName())) {
				foundCat = true;
				break;
			}
		}
		assertThat(foundCat).isTrue();
	}

	@Test
	@Transactional
	void shouldInsertPetIntoDatabaseAndGenerateId() {
		// Create an owner
		Owner owner = new Owner();
		owner.setFirstName("Sam");
		owner.setLastName("Coleman");
		owner.setAddress("123 Main St");
		owner.setCity("Wollongong");
		owner.setTelephone("1234567890");
		this.owners.save(owner);

		// Add a pet to the owner
		Pet pet = new Pet();
		pet.setName("bowser");
		Collection<PetType> types = this.owners.findPetTypes();
		assertThat(types).isNotEmpty();
		pet.setType(types.iterator().next());
		pet.setBirthDate(LocalDate.now());
		owner.addPet(pet);

		// Save the owner with the new pet
		this.owners.save(owner);

		// Verify the pet was saved with an ID
		Owner savedOwner = this.owners.findById(owner.getId());
		assertThat(savedOwner.getPets()).hasSize(1);
		Pet savedPet = savedOwner.getPet("bowser");
		assertThat(savedPet).isNotNull();
		assertThat(savedPet.getId()).isNotNull();
	}

	@Test
	@Transactional
	void shouldUpdatePetName() {
		// First create an owner with a pet
		Owner owner = new Owner();
		owner.setFirstName("Sam");
		owner.setLastName("Coleman");
		owner.setAddress("123 Main St");
		owner.setCity("Wollongong");
		owner.setTelephone("1234567890");

		Pet pet = new Pet();
		pet.setName("Fluffy");
		Collection<PetType> types = this.owners.findPetTypes();
		assertThat(types).isNotEmpty();
		pet.setType(types.iterator().next());
		pet.setBirthDate(LocalDate.now());
		owner.addPet(pet);

		this.owners.save(owner);

		// Now update the pet's name
		String oldName = pet.getName();
		String newName = oldName + "X";
		pet.setName(newName);
		this.owners.save(owner);

		// Retrieve the owner again and verify the pet's name was updated
		UUID ownerId = owner.getId();
		assertThat(ownerId).isNotNull();

		Owner updatedOwner = this.owners.findById(ownerId);
		Pet updatedPet = updatedOwner.getPets().get(0);
		assertThat(updatedPet.getName()).isEqualTo(newName);
	}

	@Test
	void shouldFindVets() {
		Collection<Vet> vets = this.vets.findAll();
		assertThat(vets).isNotEmpty();

		// Check that at least one vet has specialties
		boolean foundVetWithSpecialties = false;
		for (Vet vet : vets) {
			if (vet.getNrOfSpecialties() > 0) {
				foundVetWithSpecialties = true;
				break;
			}
		}
		assertThat(foundVetWithSpecialties).isTrue();
	}

	@Test
	@Transactional
	void shouldAddNewVisitForPet() {
		// Create owner with pet
		Owner owner = new Owner();
		owner.setFirstName("Sam");
		owner.setLastName("Coleman");
		owner.setAddress("123 Main St");
		owner.setCity("Wollongong");
		owner.setTelephone("1234567890");

		Pet pet = new Pet();
		pet.setName("Fluffy");
		Collection<PetType> types = this.owners.findPetTypes();
		assertThat(types).isNotEmpty();
		pet.setType(types.iterator().next());
		pet.setBirthDate(LocalDate.now());
		owner.addPet(pet);

		this.owners.save(owner);

		// Now the pet should have an ID
		assertThat(pet.getId()).isNotNull();

		// Add a visit
		Visit visit = new Visit();
		visit.setDescription("test visit");
		visit.setDate(LocalDate.now());

		owner.addVisit(pet.getId(), visit);
		this.owners.save(owner);

		// Verify the visit was added
		Owner updatedOwner = this.owners.findById(owner.getId());
		Pet updatedPet = updatedOwner.getPets().get(0);
		assertThat(updatedPet.getVisits()).isNotEmpty();
		assertThat(updatedPet.getVisits().iterator().next().getId()).isNotNull();
	}

	@Test
	@Transactional
	void shouldFindVisitsByPetId() {
		// Create owner with pet and visit
		Owner owner = new Owner();
		owner.setFirstName("Sam");
		owner.setLastName("Coleman");
		owner.setAddress("123 Main St");
		owner.setCity("Wollongong");
		owner.setTelephone("1234567890");

		Pet pet = new Pet();
		pet.setName("Fluffy");
		Collection<PetType> types = this.owners.findPetTypes();
		assertThat(types).isNotEmpty();
		pet.setType(types.iterator().next());
		pet.setBirthDate(LocalDate.now());
		owner.addPet(pet);

		this.owners.save(owner);

		// Add two visits
		Visit visit1 = new Visit();
		visit1.setDescription("first visit");
		visit1.setDate(LocalDate.now());

		Visit visit2 = new Visit();
		visit2.setDescription("second visit");
		visit2.setDate(LocalDate.now().plusDays(1));

		owner.addVisit(pet.getId(), visit1);
		owner.addVisit(pet.getId(), visit2);
		this.owners.save(owner);

		// Verify we can find the visits
		Owner updatedOwner = this.owners.findById(owner.getId());
		Pet updatedPet = updatedOwner.getPets().get(0);
		Collection<Visit> visits = updatedPet.getVisits();

		assertThat(visits).hasSize(2);
		assertThat(visits.iterator().next().getDate()).isNotNull();
	}

}
