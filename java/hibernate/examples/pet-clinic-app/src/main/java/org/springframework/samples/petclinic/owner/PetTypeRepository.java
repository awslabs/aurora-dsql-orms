package org.springframework.samples.petclinic.owner;

import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.CachePut;
import org.springframework.dao.DataAccessException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.repository.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collection;
import java.util.Optional;
import java.util.UUID;

public interface PetTypeRepository extends Repository<PetType, UUID> {

	@Transactional(readOnly = true)
	@Cacheable(value = "allPetTypes")
	Collection<PetType> findAll() throws DataAccessException;

	@Transactional(readOnly = true)
	Page<PetType> findAll(Pageable pageable);

	@Transactional(readOnly = true)
	@Cacheable(value = "petType", key = "#id.toString()")
	Optional<PetType> findById(UUID id);

	@CachePut(value = "petType", key = "#result.id.toString()")
	@CacheEvict(value = "allPetTypes", allEntries = true)
	PetType save(PetType petType);

	@CacheEvict(value = { "petType", "allPetTypes" }, key = "#petType.id.toString()")
	void delete(PetType petType);

}
